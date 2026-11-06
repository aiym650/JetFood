import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { map, Observable } from 'rxjs';
import { ApiListResponse, getApiListResults } from './shared/api-list';

interface ExternalIntegration {
  name: string;
  integration_type: string;
  api_endpoint: string;
  api_key?: string;
  config?: any;
}

@Injectable({
  providedIn: 'root',
})
export class Integration {
  private apiUrl = 'http://localhost:8000/api/integration';

  constructor(private http: HttpClient) {}

  private getHeaders(): HttpHeaders {
    const token = localStorage.getItem('token');
    return new HttpHeaders({
      'Authorization': `Token ${token}`,
      'Content-Type': 'application/json'
    });
  }

  getIntegrations(): Observable<any[]> {
    return this.http.get<ApiListResponse<any>>(`${this.apiUrl}/`, { headers: this.getHeaders() })
      .pipe(map(getApiListResults));
  }

  createIntegration(integration: ExternalIntegration): Observable<any> {
    return this.http.post(`${this.apiUrl}/`, integration, { headers: this.getHeaders() });
  }

  getIntegration(id: number): Observable<any> {
    return this.http.get(`${this.apiUrl}/${id}/`, { headers: this.getHeaders() });
  }

  updateIntegration(id: number, integration: Partial<ExternalIntegration>): Observable<any> {
    return this.http.put(`${this.apiUrl}/${id}/`, integration, { headers: this.getHeaders() });
  }

  deleteIntegration(id: number): Observable<any> {
    return this.http.delete(`${this.apiUrl}/${id}/`, { headers: this.getHeaders() });
  }

  getLogs(): Observable<any[]> {
    return this.http.get<ApiListResponse<any>>(`${this.apiUrl}/logs/`, { headers: this.getHeaders() })
      .pipe(map(getApiListResults));
  }

  testIntegration(id: number): Observable<any> {
    return this.http.post(`${this.apiUrl}/${id}/test/`, {}, { headers: this.getHeaders() });
  }

  syncIntegration(id: number): Observable<any> {
    return this.http.post(`${this.apiUrl}/${id}/sync/`, {}, { headers: this.getHeaders() });
  }
}
