import { AfterViewInit, Component, ElementRef, EventEmitter, Input, OnChanges, OnDestroy, Output, SimpleChanges, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import * as L from 'leaflet/dist/leaflet-src.esm.js';
import { Subscription } from 'rxjs';
import { I18nService } from '../i18n/i18n.service';

export interface RouteCoordinates {
  origin_latitude: number | null;
  origin_longitude: number | null;
  destination_latitude: number | null;
  destination_longitude: number | null;
}

export interface RouteMetrics {
  route_distance_meters: number;
  estimated_duration_seconds: number;
}

export function getDeliveryRemainingSeconds(
  deliveryStartedAt: string | null,
  estimatedArrivalTime: string | null,
  estimatedDurationSeconds: number | null,
  now: number,
): number | null {
  if (!deliveryStartedAt) return null;

  const startedAt = Date.parse(deliveryStartedAt);
  if (!Number.isFinite(startedAt)) return null;

  const eta = estimatedArrivalTime ? Date.parse(estimatedArrivalTime) : Number.NaN;
  const duration = estimatedDurationSeconds && estimatedDurationSeconds > 0
    ? estimatedDurationSeconds
    : Number.isFinite(eta) && eta > startedAt
      ? (eta - startedAt) / 1000
      : null;
  if (duration === null || duration <= 0) return null;

  const effectiveEta = Number.isFinite(eta) && eta > startedAt
    ? eta
    : startedAt + duration * 1000;
  return Math.ceil(Math.max(0, (effectiveEta - now) / 1000));
}

export function getPositionAlongRoute(points: L.LatLng[], progress: number): L.LatLng | null {
  if (!points.length) return null;
  if (points.length === 1 || progress <= 0) return points[0];
  if (progress >= 1) return points[points.length - 1];

  const segmentLengths = points.slice(1).map((point, index) => points[index].distanceTo(point));
  const totalDistance = segmentLengths.reduce((total, segment) => total + segment, 0);
  if (!totalDistance) return points[0];

  let remainingDistance = totalDistance * progress;
  for (let index = 0; index < segmentLengths.length; index += 1) {
    const segmentLength = segmentLengths[index];
    if (remainingDistance <= segmentLength) {
      const start = points[index];
      const end = points[index + 1];
      const segmentProgress = remainingDistance / segmentLength;
      return L.latLng(
        start.lat + (end.lat - start.lat) * segmentProgress,
        start.lng + (end.lng - start.lng) * segmentProgress,
      );
    }
    remainingDistance -= segmentLength;
  }
  return points[points.length - 1];
}

interface OsrmRouteResponse {
  code: string;
  routes: Array<{ geometry: { coordinates: [number, number][] }; distance: number; duration: number }>;
}

@Component({
  selector: 'app-delivery-route-map',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './delivery-route-map.html',
  styleUrl: './delivery-route-map.css',
})
export class DeliveryRouteMap implements AfterViewInit, OnChanges, OnDestroy {
  @Input() originLatitude: number | null = null;
  @Input() originLongitude: number | null = null;
  @Input() destinationLatitude: number | null = null;
  @Input() destinationLongitude: number | null = null;
  @Input() orderStatus = '';
  @Input() deliveryStartedAt: string | null = null;
  @Input() estimatedArrivalTime: string | null = null;
  @Input() estimatedDurationSeconds: number | null = null;
  @Output() pointsChange = new EventEmitter<RouteCoordinates>();
  @Output() routeMetricsChange = new EventEmitter<RouteMetrics | null>();
  @ViewChild('mapHost') mapHost!: ElementRef<HTMLDivElement>;

  activePoint: 'origin' | 'destination' = 'origin';
  routeDistanceKm: number | null = null;
  routeDurationMinutes: number | null = null;
  routeError = '';
  remainingSeconds = 0;
  hasDeliveryTimer = false;
  trackingTime = Date.now();

  private map?: L.Map;
  private originMarker?: L.Marker;
  private destinationMarker?: L.Marker;
  private courierMarker?: L.Marker;
  private routeLine?: L.Polyline;
  private routePoints: L.LatLng[] = [];
  private routeRequest?: Subscription;
  private trackingTimer?: ReturnType<typeof setInterval>;

  constructor(private http: HttpClient, public i18n: I18nService) {}

  ngAfterViewInit(): void {
    this.map = L.map(this.mapHost.nativeElement, { scrollWheelZoom: false })
      .setView([43.2389, 76.8897], 12);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors',
    }).addTo(this.map);
    this.map.on('click', (event: L.LeafletMouseEvent) => {
      this.setRoutePoint(this.activePoint, event.latlng.lat, event.latlng.lng);
    });
    this.updateMarkers();
    this.updateRoute();
    this.trackingTimer = setInterval(() => {
      this.trackingTime = Date.now();
      this.updateCourierPosition();
    }, 1000);
    setTimeout(() => this.map?.invalidateSize(), 0);
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (!this.map) return;
    const routeChanged = [
      'originLatitude', 'originLongitude',
      'destinationLatitude', 'destinationLongitude',
    ].some(field => !!changes[field]);
    if (routeChanged) {
      this.updateMarkers();
      this.updateRoute();
    } else {
      this.updateCourierPosition();
    }
  }

  ngOnDestroy(): void {
    if (this.trackingTimer) clearInterval(this.trackingTimer);
    this.routeRequest?.unsubscribe();
    this.map?.remove();
  }

  get remainingTimeLabel(): string {
    const seconds = Math.max(0, this.remainingSeconds);
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const remainder = seconds % 60;
    return [hours, minutes, remainder].map(value => String(value).padStart(2, '0')).join(':');
  }

  get deliveryIsLate(): boolean {
    return this.orderStatus === 'delivering' && this.hasDeliveryTimer && this.remainingSeconds === 0;
  }

  selectPoint(point: 'origin' | 'destination'): void {
    this.activePoint = point;
  }

  setRoutePoint(point: 'origin' | 'destination', latitude: number, longitude: number): void {
    if (
      !Number.isFinite(latitude)
      || !Number.isFinite(longitude)
      || latitude < -90
      || latitude > 90
      || longitude < -180
      || longitude > 180
    ) return;
    this.setPoint(point, L.latLng(latitude, longitude));
  }

  private setPoint(point: 'origin' | 'destination', location: L.LatLng): void {
    const latitude = Number(location.lat.toFixed(6));
    const longitude = Number(location.lng.toFixed(6));
    if (point === 'origin') {
      this.originLatitude = latitude;
      this.originLongitude = longitude;
    } else {
      this.destinationLatitude = latitude;
      this.destinationLongitude = longitude;
    }
    this.updateMarkers();
    this.pointsChange.emit({
      origin_latitude: this.originLatitude,
      origin_longitude: this.originLongitude,
      destination_latitude: this.destinationLatitude,
      destination_longitude: this.destinationLongitude,
    });
    this.updateRoute();
  }

  private updateMarkers(): void {
    if (!this.map) return;
    this.originMarker = this.updateMarker(
      this.originMarker,
      this.originLatitude,
      this.originLongitude,
      'A',
      '#21845b',
    );
    this.destinationMarker = this.updateMarker(
      this.destinationMarker,
      this.destinationLatitude,
      this.destinationLongitude,
      'B',
      '#d34c37',
    );
  }

  private updateMarker(
    marker: L.Marker | undefined,
    latitude: number | null,
    longitude: number | null,
    label: string,
    color: string,
  ): L.Marker | undefined {
    if (!this.map) return marker;
    if (latitude === null || longitude === null) {
      marker?.remove();
      return undefined;
    }
    const icon = L.divIcon({
      className: 'delivery-map-marker',
      html: `<span style="background:${color}">${label}</span>`,
      iconSize: [30, 30],
      iconAnchor: [15, 15],
    });
    const location: L.LatLngExpression = [latitude, longitude];
    if (!marker) {
      marker = L.marker(location, { icon, draggable: true }).addTo(this.map);
      marker.on('dragend', () => {
        const movedTo = marker?.getLatLng();
        if (movedTo) this.setPoint(label === 'A' ? 'origin' : 'destination', movedTo);
      });
    } else {
      marker.setLatLng(location);
      marker.setIcon(icon);
    }
    return marker;
  }

  private updateRoute(): void {
    if (!this.map) return;
    this.routeRequest?.unsubscribe();
    this.routeError = '';
    this.routeDistanceKm = null;
    this.routeDurationMinutes = null;
    this.routeLine?.remove();
    this.routePoints = [];
    this.courierMarker?.remove();
    this.courierMarker = undefined;
    this.routeMetricsChange.emit(null);
    if (
      this.originLatitude === null
      || this.originLongitude === null
      || this.destinationLatitude === null
      || this.destinationLongitude === null
    ) return;

    const url = `https://router.project-osrm.org/route/v1/driving/${this.originLongitude},${this.originLatitude};${this.destinationLongitude},${this.destinationLatitude}?overview=full&geometries=geojson`;
    this.routeRequest = this.http.get<OsrmRouteResponse>(url).subscribe({
      next: (result) => {
        const route = result.routes?.[0];
        if (result.code !== 'Ok' || !route) {
          this.routeError = this.i18n.t('mapRouteUnavailable');
          return;
        }
        this.routePoints = route.geometry.coordinates.map(
          ([longitude, latitude]) => L.latLng(latitude, longitude),
        );
        this.routeLine = L.polyline(
          this.routePoints,
          { color: '#24734f', weight: 5, opacity: 0.85 },
        ).addTo(this.map!);
        this.routeDistanceKm = route.distance / 1000;
        this.routeDurationMinutes = route.duration / 60;
        this.routeMetricsChange.emit({
          route_distance_meters: Math.round(route.distance),
          estimated_duration_seconds: Math.max(1, Math.round(route.duration)),
        });
        this.map!.fitBounds(this.routeLine.getBounds(), { padding: [28, 28] });
        this.updateCourierPosition();
      },
      error: () => {
        this.routeError = this.i18n.t('mapRouteUnavailable');
      },
    });
  }

  private updateCourierPosition(): void {
    if (!this.map || this.orderStatus !== 'delivering' || !this.deliveryStartedAt) {
      this.courierMarker?.remove();
      this.courierMarker = undefined;
      this.hasDeliveryTimer = false;
      this.remainingSeconds = 0;
      return;
    }

    const startedAt = Date.parse(this.deliveryStartedAt);
    const eta = this.estimatedArrivalTime ? Date.parse(this.estimatedArrivalTime) : Number.NaN;
    const duration = this.estimatedDurationSeconds && this.estimatedDurationSeconds > 0
      ? this.estimatedDurationSeconds
      : Number.isFinite(startedAt) && Number.isFinite(eta) && eta > startedAt
        ? (eta - startedAt) / 1000
        : null;
    const remainingSeconds = getDeliveryRemainingSeconds(
      this.deliveryStartedAt,
      this.estimatedArrivalTime,
      this.estimatedDurationSeconds,
      this.trackingTime,
    );
    if (remainingSeconds === null) {
      this.hasDeliveryTimer = false;
      this.courierMarker?.remove();
      this.courierMarker = undefined;
      return;
    }

    this.hasDeliveryTimer = true;
    this.remainingSeconds = remainingSeconds;
    if (!Number.isFinite(startedAt) || duration === null || duration <= 0) return;
    const elapsedSeconds = Math.max(0, (this.trackingTime - startedAt) / 1000);

    if (!this.routePoints.length) return;
    const position = getPositionAlongRoute(this.routePoints, elapsedSeconds / duration);
    if (!position) return;
    const icon = L.divIcon({
      className: 'delivery-map-courier',
      html: '<span>●</span>',
      iconSize: [30, 30],
      iconAnchor: [15, 15],
    });
    if (!this.courierMarker) {
      this.courierMarker = L.marker(position, { icon, zIndexOffset: 1000 }).addTo(this.map);
    } else {
      this.courierMarker.setLatLng(position);
    }
  }
}
