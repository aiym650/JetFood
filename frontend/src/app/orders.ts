import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { map, Observable } from 'rxjs';
import { ApiListResponse, getApiListResults } from './shared/api-list';

interface OrderItemInput {
  item_id: number;
  quantity: number;
}

interface OrderItem {
  id: number;
  menu_item_id: number | null;
  item_name: string;
  quantity: number;
  price_per_item: number;
  subtotal: number;
}

interface OrderInput {
  cashback_amount?: number;
  promo_code?: string;
  delivery_address: string;
  delivery_notes?: string;
  estimated_delivery_time?: string;
  payment_method: 'online' | 'cash';
  items: OrderItemInput[];
}

export interface OrderRecord {
  payment?: { id: number; method: 'cash' | 'online'; status: string } | null;
  cashback?: { earned: string; earned_minor: number; state: string } | null;
  id: number;
  order_number: string;
  customer: number;
  customer_name: string;
  delivery_person: number | null;
  delivery_person_name: string | null;
  status: string;
  priority: string;
  total_amount: number;
  delivery_address: string;
  delivery_notes: string;
  estimated_delivery_time: string | null;
  delivery_started_at: string | null;
  estimated_arrival_time: string | null;
  actual_delivery_time: string | null;
  delivery_confirmed_at: string | null;
  created_at: string;
  updated_at: string;
  items: OrderItem[];
}

export interface RefundRequestRecord {
  id: number;
  order: number;
  order_number: string;
  order_status: string;
  customer_name: string;
  requested_by: number;
  requested_by_name: string;
  request_type: 'cancel' | 'refund';
  reason_category: string;
  reason_text: string;
  status: 'pending' | 'approved' | 'rejected';
  decided_by: number | null;
  decided_by_name: string | null;
  decided_at: string | null;
  decision_note: string;
  refund_amount: string | null;
  amount_paid: string;
  created_at: string;
}

export interface CartQuote {
  online_payment_configured?: boolean; payment_test_mode?: boolean;
  cashback_amount?: string; cashback_max?: string; cashback_balance?: string; cashback_forecast?: string; cashback_spend_percent?: string;
  items_amount: string;
  discount_amount: string;
  delivery_fee: string;
  delivery_discount: string;
  total_amount: string;
  promo_code: string;
}

export interface DeliveryRoute {
  id: number;
  order: number;
  origin_address: string;
  destination_address: string;
  notes: string;
  origin_latitude: number | null;
  origin_longitude: number | null;
  destination_latitude: number | null;
  destination_longitude: number | null;
  route_distance_meters: number | null;
  estimated_duration_seconds: number | null;
  directions_url: string;
  updated_by: number | null;
  updated_by_name: string | null;
  updated_at: string;
}

export interface DeliveryCourier {
  id: number;
  username: string;
  role: string;
}

@Injectable({
  providedIn: 'root',
})
export class Orders {
  private apiUrl = 'http://localhost:8000/api/orders';

  constructor(private http: HttpClient) {}

  private getHeaders(): HttpHeaders {
    const token = localStorage.getItem('token');
    return new HttpHeaders({
      'Authorization': `Token ${token}`,
      'Content-Type': 'application/json'
    });
  }

  getOrders(): Observable<OrderRecord[]> {
    return this.http.get<ApiListResponse<OrderRecord>>(`${this.apiUrl}/`, { headers: this.getHeaders() })
      .pipe(map(getApiListResults));
  }

  getOrder(id: number): Observable<OrderRecord> {
    return this.http.get<OrderRecord>(`${this.apiUrl}/${id}/`, { headers: this.getHeaders() });
  }

  createOrder(order: OrderInput, key?: string): Observable<OrderRecord> {
    const headers = key ? this.getHeaders().set('Idempotency-Key', key) : this.getHeaders();
    return this.http.post<OrderRecord>(`${this.apiUrl}/`, order, { headers });
  }

  quote(items: OrderItemInput[], promo_code: string, cashback_amount = 0): Observable<CartQuote> {
    return this.http.post<CartQuote>(`${this.apiUrl}/quote/`, { items, promo_code, cashback_amount }, { headers: this.getHeaders() });
  }

  modifyOrder(orderId: number, changes: {
    delivery_address?: string;
    delivery_notes?: string;
    items?: OrderItemInput[];
  }): Observable<OrderRecord> {
    return this.http.patch<OrderRecord>(`${this.apiUrl}/${orderId}/modify/`, changes, {
      headers: this.getHeaders(),
    });
  }

  updateOrderStatus(orderId: number, status: string, notes?: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/${orderId}/status/`, 
      { status, notes }, 
      { headers: this.getHeaders() }
    );
  }

  cancelOrder(orderId: number, reason: string): Observable<OrderRecord> {
    return this.http.post<OrderRecord>(
      `${this.apiUrl}/${orderId}/cancel/`,
      { reason },
      { headers: this.getHeaders() },
    );
  }

  createRefundRequest(orderId: number, request: {
    request_type: 'cancel' | 'refund';
    reason_category?: string;
    reason_text: string;
  }): Observable<RefundRequestRecord> {
    return this.http.post<RefundRequestRecord>(
      `${this.apiUrl}/${orderId}/requests/`,
      request,
      { headers: this.getHeaders() },
    );
  }

  getRefundRequests(status?: 'pending' | 'approved' | 'rejected'): Observable<RefundRequestRecord[]> {
    const query = status ? `?status=${status}` : '';
    return this.http.get<RefundRequestRecord[]>(`${this.apiUrl}/requests/${query}`, {
      headers: this.getHeaders(),
    });
  }

  approveRefundRequest(requestId: number, refundAmount?: string): Observable<RefundRequestRecord> {
    const body = refundAmount === undefined ? {} : { refund_amount: refundAmount };
    return this.http.post<RefundRequestRecord>(
      `${this.apiUrl}/requests/${requestId}/approve/`,
      body,
      { headers: this.getHeaders() },
    );
  }

  rejectRefundRequest(requestId: number, decisionNote: string): Observable<RefundRequestRecord> {
    return this.http.post<RefundRequestRecord>(
      `${this.apiUrl}/requests/${requestId}/reject/`,
      { decision_note: decisionNote },
      { headers: this.getHeaders() },
    );
  }

  confirmDelivery(orderId: number): Observable<{ message: string; delivery_confirmed_at: string }> {
    return this.http.post<{ message: string; delivery_confirmed_at: string }>(
      `${this.apiUrl}/${orderId}/confirm-delivery/`,
      {},
      { headers: this.getHeaders() },
    );
  }

  getDeliveryRoute(orderId: number): Observable<DeliveryRoute> {
    return this.http.get<DeliveryRoute>(`${this.apiUrl}/${orderId}/route/`, {
      headers: this.getHeaders(),
    });
  }

  saveDeliveryRoute(orderId: number, route: {
    origin_address: string;
    notes: string;
    origin_latitude: number | null;
    origin_longitude: number | null;
    destination_latitude: number | null;
    destination_longitude: number | null;
    route_distance_meters: number;
    estimated_duration_seconds: number;
  }): Observable<DeliveryRoute> {
    return this.http.put<DeliveryRoute>(`${this.apiUrl}/${orderId}/route/`, route, {
      headers: this.getHeaders(),
    });
  }

  assignDeliveryPerson(orderId: number, deliveryPersonId: number): Observable<any> {
    return this.http.post(`${this.apiUrl}/${orderId}/assign/`, 
      { delivery_person_id: deliveryPersonId }, 
      { headers: this.getHeaders() }
    );
  }

  getDeliveryCouriers(): Observable<DeliveryCourier[]> {
    return this.http.get<ApiListResponse<DeliveryCourier>>(
      'http://localhost:8000/api/auth/users/',
      { headers: this.getHeaders() },
    ).pipe(
      map(response => getApiListResults(response).filter(user => user.role === 'delivery')),
    );
  }

  getOrderSummary(startDate?: string, endDate?: string): Observable<any> {
    let params: { [key: string]: string } = {};
    if (startDate) params['start_date'] = startDate;
    if (endDate) params['end_date'] = endDate;
    return this.http.get(`${this.apiUrl}/summary/`, {
      headers: this.getHeaders(),
      params
    });
  }
}
