import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { map, Observable } from 'rxjs';
import { ApiListResponse, getApiListResults } from './shared/api-list';

interface Report {
  report_type: string;
  title: string;
  description?: string;
  format: string;
  parameters?: any;
}

interface ReportSchedule {
  report_type: string;
  frequency: string;
  parameters?: any;
  recipients: number[];
}

export interface ReportDownload {
  message: string;
  parameters: Record<string, unknown>;
}

@Injectable({
  providedIn: 'root',
})
export class Reports {
  private apiUrl = 'http://localhost:8000/api/reports';

  constructor(private http: HttpClient) {}

  private getHeaders(): HttpHeaders {
    const token = localStorage.getItem('token');
    return new HttpHeaders({
      'Authorization': `Token ${token}`,
      'Content-Type': 'application/json'
    });
  }

  getReports(): Observable<any[]> {
    return this.http.get<ApiListResponse<any>>(`${this.apiUrl}/`, { headers: this.getHeaders() })
      .pipe(map(getApiListResults));
  }

  createReport(report: Report): Observable<any> {
    return this.http.post(`${this.apiUrl}/`, report, { headers: this.getHeaders() });
  }

  getReport(id: number): Observable<any> {
    return this.http.get(`${this.apiUrl}/${id}/`, { headers: this.getHeaders() });
  }

  downloadReport(id: number): Observable<ReportDownload> {
    return this.http.get<ReportDownload>(`${this.apiUrl}/${id}/download/`, { headers: this.getHeaders() });
  }

  getSchedules(): Observable<any[]> {
    return this.http.get<ApiListResponse<any>>(`${this.apiUrl}/schedules/`, { headers: this.getHeaders() })
      .pipe(map(getApiListResults));
  }

  createSchedule(schedule: ReportSchedule): Observable<any> {
    return this.http.post(`${this.apiUrl}/schedules/`, schedule, { headers: this.getHeaders() });
  }

  updateSchedule(id: number, schedule: Partial<ReportSchedule>): Observable<any> {
    return this.http.put(`${this.apiUrl}/schedules/${id}/`, schedule, { headers: this.getHeaders() });
  }

  deleteSchedule(id: number): Observable<any> {
    return this.http.delete(`${this.apiUrl}/schedules/${id}/`, { headers: this.getHeaders() });
  }
}
