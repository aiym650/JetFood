import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { map, Observable } from 'rxjs';
import { ApiListResponse, getApiListResults } from './shared/api-list';

export type SupportCaseStatus = 'open' | 'in_progress' | 'waiting_for_customer' | 'resolved';
export type SupportMessageSender = 'customer' | 'assistant' | 'staff';

export interface SupportMessage {
  id: number;
  sender: SupportMessageSender;
  body: string;
  created_at: string;
}

export interface SupportCase {
  language?: 'ru' | 'kk' | 'en';
  operator_requested?: boolean;
  id: number;
  customer: number;
  customer_name: string;
  order: number | null;
  order_number: string;
  issue_description: string;
  status: SupportCaseStatus;
  resolution: string;
  messages: SupportMessage[];
  created_at: string;
  updated_at: string;
}

@Injectable({ providedIn: 'root' })
export class Support {
  private readonly apiUrl = 'http://localhost:8000/api/support/cases/';

  constructor(private http: HttpClient) {}

  getCases(): Observable<SupportCase[]> {
    return this.http.get<ApiListResponse<SupportCase>>(this.apiUrl)
      .pipe(map(getApiListResults));
  }

  getCase(caseId: number): Observable<SupportCase> {
    return this.http.get<SupportCase>(`${this.apiUrl}${caseId}/`);
  }

  openCase(orderNumber: string, issueDescription: string, language: 'ru' | 'kk' | 'en' = 'en', operator_requested = false): Observable<SupportCase> {
    return this.http.post<SupportCase>(this.apiUrl, {
      order_number: orderNumber,
      issue_description: issueDescription,
      language, operator_requested,
    });
  }

  sendMessage(caseId: number, body: string, requestId: string = crypto.randomUUID()): Observable<SupportCase> {
    return this.http.post<SupportCase>(
      `${this.apiUrl}${caseId}/messages/`,
      { body, request_id: requestId },
    );
  }

  updateCase(caseId: number, changes: object): Observable<SupportCase> {
    return this.http.patch<SupportCase>(`${this.apiUrl}${caseId}/`, changes);
  }

  retry(caseId: number): Observable<SupportCase> {
    return this.http.post<SupportCase>(`${this.apiUrl}${caseId}/retry/`, {});
  }

  faq(language: string): Observable<{ question: string; answer: string }[]> {
    return this.http.get<{ question: string; answer: string }[]>(`http://localhost:8000/api/support/faq/`, { params: { language } });
  }
}
