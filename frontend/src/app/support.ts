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

  openCase(orderNumber: string, issueDescription: string): Observable<SupportCase> {
    return this.http.post<SupportCase>(this.apiUrl, {
      order_number: orderNumber,
      issue_description: issueDescription,
    });
  }

  sendMessage(caseId: number, body: string): Observable<SupportCase> {
    return this.http.post<SupportCase>(
      `${this.apiUrl}${caseId}/messages/`,
      { body },
    );
  }
}
