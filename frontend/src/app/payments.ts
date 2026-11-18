import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { map, Observable } from 'rxjs';
import { ApiListResponse, getApiListResults } from './shared/api-list';

export interface PaymentRecord {
  id: number;
  order: number;
  order_number: string;
  order_status?: string;
  customer_name: string;
  method: 'online' | 'cash';
  status: 'pending' | 'failed' | 'paid' | 'refund_requested' | 'refunded' | 'cancelled';
  amount: string;
  transaction_id: string;
  card_brand: string | null;
  card_last4: string | null;
  failure_reason: string | null;
  refund_reason: string;
  created_at: string;
  paid_at: string | null;
  refunded_at: string | null;
}

export interface CardPaymentInput {
  card_number: string;
  expiry: string;
  cvv: string;
  cardholder_name: string;
}

export interface CardPaymentResult extends PaymentRecord {
  message: string;
}

@Injectable({ providedIn: 'root' })
export class Payments {
  private readonly apiUrl = 'http://localhost:8000/api/payments/';

  constructor(private http: HttpClient) {}

  getPayments(): Observable<PaymentRecord[]> {
    return this.http.get<ApiListResponse<PaymentRecord>>(this.apiUrl)
      .pipe(map(getApiListResults));
  }

  payOrder(orderId: number, card: CardPaymentInput): Observable<CardPaymentResult> {
    return this.http.post<CardPaymentResult>(`${this.apiUrl}${orderId}/pay/`, card);
  }

  getReceipt(paymentId: number): Observable<PaymentRecord> {
    return this.http.get<PaymentRecord>(`${this.apiUrl}${paymentId}/receipt/`);
  }

  confirmCashPayment(id: number): Observable<PaymentRecord> {
    return this.http.post<PaymentRecord>(`${this.apiUrl}${id}/confirm-cash/`, {});
  }

  refundPayment(id: number, reason: string): Observable<PaymentRecord> {
    return this.http.post<PaymentRecord>(`${this.apiUrl}${id}/refund/`, { reason });
  }
}
