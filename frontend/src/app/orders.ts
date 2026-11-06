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
  delivery_address: string;
  delivery_notes?: string;
  estimated_delivery_time?: string;
  payment_method: 'online' | 'cash';
  items: OrderItemInput[];
}

export interface OrderRecord {
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
  actual_delivery_time: string | null;
  delivery_confirmed_at: string | null;
  created_at: string;
  updated_at: string;
  items: OrderItem[];
}

export interface DeliveryRoute {
  id: number;
  order: number;
  origin_address: string;
  destination_address: string;
  notes: string;
  directions_url: string;
  updated_by: number | null;
  updated_by_name: string | null;
  updated_at: string;
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

  createOrder(order: OrderInput): Observable<OrderRecord> {
    return this.http.post<OrderRecord>(`${this.apiUrl}/`, order, { headers: this.getHeaders() });
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

  saveDeliveryRoute(orderId: number, route: { origin_address: string; notes: string }): Observable<DeliveryRoute> {
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
