import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { map, Observable } from 'rxjs';
import { ApiListResponse, getApiListResults } from './shared/api-list';

export interface DeliveryAddress {
  id: number;
  label: string;
  recipient_name: string;
  phone: string;
  address_line: string;
  city: string;
  postal_code: string;
  instructions: string;
  is_default: boolean;
}

export type DeliveryAddressInput = Omit<DeliveryAddress, 'id'>;

@Injectable({ providedIn: 'root' })
export class Addresses {
  private readonly apiUrl = 'http://localhost:8000/api/auth/addresses/';

  constructor(private http: HttpClient) {}

  getAddresses(): Observable<DeliveryAddress[]> {
    return this.http.get<ApiListResponse<DeliveryAddress>>(this.apiUrl)
      .pipe(map(getApiListResults));
  }

  createAddress(address: DeliveryAddressInput): Observable<DeliveryAddress> {
    return this.http.post<DeliveryAddress>(this.apiUrl, address);
  }

  updateAddress(id: number, address: DeliveryAddressInput): Observable<DeliveryAddress> {
    return this.http.put<DeliveryAddress>(`${this.apiUrl}${id}/`, address);
  }

  deleteAddress(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}${id}/`);
  }
}
