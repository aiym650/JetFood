import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { map, Observable } from 'rxjs';
import { ApiListResponse, getApiListResults } from './shared/api-list';

export interface PaymentRecord {
  id: number;
  order: number;
  order_number: string;
  customer_name: string;
  method: 'online' | 'cash';
  status: 'pending' | 'paid' | 'refund_requested' | 'refunded' | 'cancelled';
  amount: string;
  transaction_id: string;
  refund_reason: string;
  created_at: string;
  paid_at: string | null;
  refunded_at: string | null;
}

@Injectable({ providedIn: 'root' })
export class Payments {
  private readonly apiUrl = 'http://localhost:8000/api/payments/';

  constructor(private http: HttpClient) {}

  getPayments(): Observable<PaymentRecord[]> {
    return this.http.get<ApiListResponse<PaymentRecord>>(this.apiUrl)
      .pipe(map(getApiListResults));
  }

  confirmCashPayment(id: number): Observable<PaymentRecord> {
    return this.http.post<PaymentRecord>(`${this.apiUrl}${id}/confirm-cash/`, {});
  }

  refundPayment(id: number, reason: string): Observable<PaymentRecord> {
    return this.http.post<PaymentRecord>(`${this.apiUrl}${id}/refund/`, { reason });
  }
}
