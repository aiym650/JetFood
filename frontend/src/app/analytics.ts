import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { map, Observable } from 'rxjs';
import { ApiListResponse, getApiListResults } from './shared/api-list';

interface AnalyticsEvent {
  event_type: string;
  metadata?: any;
}

interface SystemMetric {
  name: string;
  value: number;
  unit?: string;
  description?: string;
}

@Injectable({
  providedIn: 'root',
})
export class Analytics {
  private apiUrl = 'http://localhost:8000/api/analytics';

  constructor(private http: HttpClient) {}

  private getHeaders(): HttpHeaders {
    const token = localStorage.getItem('token');
    return new HttpHeaders({
      'Authorization': `Token ${token}`,
      'Content-Type': 'application/json'
    });
  }

  logEvent(event: AnalyticsEvent): Observable<any> {
    return this.http.post(`${this.apiUrl}/events/`, event, { headers: this.getHeaders() });
  }

  getEvents(): Observable<any[]> {
    return this.http.get<ApiListResponse<any>>(`${this.apiUrl}/events/`, { headers: this.getHeaders() })
      .pipe(map(getApiListResults));
  }

  getSystemMetrics(): Observable<SystemMetric[]> {
    return this.http.get<ApiListResponse<SystemMetric>>(`${this.apiUrl}/metrics/`, { headers: this.getHeaders() })
      .pipe(map(getApiListResults));
  }

  createSystemMetric(metric: SystemMetric): Observable<SystemMetric> {
    return this.http.post<SystemMetric>(`${this.apiUrl}/metrics/`, metric, { headers: this.getHeaders() });
  }

  getPerformanceReports(): Observable<any[]> {
    return this.http.get<ApiListResponse<any>>(`${this.apiUrl}/reports/`, { headers: this.getHeaders() })
      .pipe(map(getApiListResults));
  }

  getSystemAnalysis(): Observable<any> {
    return this.http.get(`${this.apiUrl}/analysis/`, { headers: this.getHeaders() });
  }

  applyRoleUpdates(updates: any[]): Observable<any> {
    return this.http.post(`${this.apiUrl}/apply-role-updates/`, 
      { updates }, 
      { headers: this.getHeaders() }
    );
  }
}
