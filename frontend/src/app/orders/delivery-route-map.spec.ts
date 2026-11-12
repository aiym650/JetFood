import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import * as L from 'leaflet/dist/leaflet-src.esm.js';
import { DeliveryRouteMap, getDeliveryRemainingSeconds, getPositionAlongRoute } from './delivery-route-map';

describe('DeliveryRouteMap', () => {
  it('counts down from the server ETA even when route duration is missing', () => {
    const startedAt = '2026-11-12T14:00:00.000Z';
    const eta = '2026-11-12T14:07:00.000Z';
    const now = Date.parse('2026-11-12T14:02:15.000Z');

    expect(getDeliveryRemainingSeconds(startedAt, eta, null, now)).toBe(285);
  });

  it('uses the saved route duration when the server ETA is unavailable', () => {
    const startedAt = '2026-11-12T14:00:00.000Z';
    const now = Date.parse('2026-11-12T14:02:15.000Z');

    expect(getDeliveryRemainingSeconds(startedAt, null, 420, now)).toBe(285);
  });

  it('does not report a timer when start time and ETA are invalid', () => {
    expect(getDeliveryRemainingSeconds('invalid', 'invalid', null, Date.now())).toBeNull();
  });

  it('emits selected A and B points as coordinate pairs', () => {
    TestBed.configureTestingModule({
      imports: [DeliveryRouteMap],
      providers: [provideHttpClient()],
    });
    const fixture = TestBed.createComponent(DeliveryRouteMap);
    const component = fixture.componentInstance;
    const points: unknown[] = [];
    component.pointsChange.subscribe(value => points.push(value));

    component.setRoutePoint('origin', 43.2389, 76.8897);
    component.setRoutePoint('destination', 43.2511, 76.9142);

    expect(points).toEqual([
      {
        origin_latitude: 43.2389,
        origin_longitude: 76.8897,
        destination_latitude: null,
        destination_longitude: null,
      },
      {
        origin_latitude: 43.2389,
        origin_longitude: 76.8897,
        destination_latitude: 43.2511,
        destination_longitude: 76.9142,
      },
    ]);
    fixture.destroy();
  });

  it('does not emit invalid map coordinates', () => {
    TestBed.configureTestingModule({
      imports: [DeliveryRouteMap],
      providers: [provideHttpClient()],
    });
    const fixture = TestBed.createComponent(DeliveryRouteMap);
    const component = fixture.componentInstance;
    const points: unknown[] = [];
    component.pointsChange.subscribe(value => points.push(value));

    component.setRoutePoint('origin', 91, 76);

    expect(points).toEqual([]);
    fixture.destroy();
  });

  it('interpolates courier positions along the road geometry by distance', () => {
    const route = [
      L.latLng(43.2, 76.8),
      L.latLng(43.2, 76.9),
      L.latLng(43.3, 76.9),
    ];
    const halfway = getPositionAlongRoute(route, 0.5);
    const firstSegmentDistance = route[0].distanceTo(route[1]);
    const secondSegmentDistance = route[1].distanceTo(route[2]);
    const secondSegmentProgress = (firstSegmentDistance + secondSegmentDistance) / 2;
    const expectedSegmentProgress = (secondSegmentProgress - firstSegmentDistance) / secondSegmentDistance;

    expect(halfway).not.toBeNull();
    expect(halfway!.lat).toBeCloseTo(43.2 + 0.1 * expectedSegmentProgress, 5);
    expect(halfway!.lng).toBeCloseTo(76.9, 5);
    expect(getPositionAlongRoute(route, 0)).toEqual(route[0]);
    expect(getPositionAlongRoute(route, 1)).toEqual(route[2]);
  });
});
