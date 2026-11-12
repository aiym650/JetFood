import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { map, Observable } from 'rxjs';
import { ApiListResponse, getApiListResults } from './shared/api-list';

export type IntegrationType =
  | 'payment_gateway'
  | 'mapping_service'
  | 'notification_service'
  | 'analytics_service'
  | 'inventory_system';
export type IntegrationStatus = 'active' | 'inactive' | 'error';

export interface ExternalIntegrationInput {
  name: string;
  integration_type: IntegrationType;
  api_endpoint: string;
  api_key?: string;
  status?: IntegrationStatus;
  config?: Record<string, unknown>;
}

export interface ExternalIntegrationRecord {
  id: number;
  name: string;
  integration_type: IntegrationType;
  status: IntegrationStatus;
  api_endpoint: string;
  api_key_present: boolean;
  config: Record<string, unknown>;
  last_sync: string | null;
  created_at: string;
  updated_at: string;
}

export interface IntegrationLogRecord {
  id: number;
  integration: number;
  integration_name: string;
  level: 'info' | 'warning' | 'error' | 'debug';
  message: string;
  request_data: Record<string, unknown>;
  response_data: Record<string, unknown>;
  status_code: number | null;
  timestamp: string;
}

export interface IntegrationActionResponse {
  message: string;
  log_id?: number;
  last_sync?: string;
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

  getIntegrations(): Observable<ExternalIntegrationRecord[]> {
    return this.http.get<ApiListResponse<ExternalIntegrationRecord>>(`${this.apiUrl}/`, { headers: this.getHeaders() })
      .pipe(map(getApiListResults));
  }

  createIntegration(integration: ExternalIntegrationInput): Observable<ExternalIntegrationRecord> {
    return this.http.post<ExternalIntegrationRecord>(`${this.apiUrl}/`, integration, { headers: this.getHeaders() });
  }

  getIntegration(id: number): Observable<ExternalIntegrationRecord> {
    return this.http.get<ExternalIntegrationRecord>(`${this.apiUrl}/${id}/`, { headers: this.getHeaders() });
  }

  updateIntegration(id: number, integration: Partial<ExternalIntegrationInput>): Observable<ExternalIntegrationRecord> {
    return this.http.put<ExternalIntegrationRecord>(`${this.apiUrl}/${id}/`, integration, { headers: this.getHeaders() });
  }

  deleteIntegration(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${id}/`, { headers: this.getHeaders() });
  }

  getLogs(): Observable<IntegrationLogRecord[]> {
    return this.http.get<ApiListResponse<IntegrationLogRecord>>(`${this.apiUrl}/logs/`, { headers: this.getHeaders() })
      .pipe(map(getApiListResults));
  }

  testIntegration(id: number): Observable<IntegrationActionResponse> {
    return this.http.post<IntegrationActionResponse>(`${this.apiUrl}/${id}/test/`, {}, { headers: this.getHeaders() });
  }

  syncIntegration(id: number): Observable<IntegrationActionResponse> {
    return this.http.post<IntegrationActionResponse>(`${this.apiUrl}/${id}/sync/`, {}, { headers: this.getHeaders() });
  }
}
