import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { map, Observable } from 'rxjs';
import { ApiListResponse, getApiListResults } from './shared/api-list';

export interface FoodItem {
  id: number;
  name: string;
  description: string;
  price: number;
  image_url: string;
  category: string;
  rating: number;
  restaurant: number;
  restaurant_name?: string | null;
  is_active?: boolean;
}

export type FoodItemInput = Omit<FoodItem, 'id' | 'rating' | 'restaurant_name'>;

@Injectable({
  providedIn: 'root',
})
export class Menu {
  private readonly apiUrl = 'http://localhost:8000/api/orders/menu/';

  constructor(private http: HttpClient) {}

  getItems(restaurantId?: number): Observable<FoodItem[]> {
    let params = new HttpParams();
    if (restaurantId) params = params.set('restaurant', restaurantId);
    const token = localStorage.getItem('token');
    const headers = new HttpHeaders({ Authorization: `Token ${token}` });
    return this.http.get<ApiListResponse<FoodItem>>(this.apiUrl, { headers, params })
      .pipe(map(getApiListResults));
  }

  createItem(item: FoodItemInput): Observable<FoodItem> {
    return this.http.post<FoodItem>(this.apiUrl, item);
  }

  updateItem(id: number, item: FoodItemInput): Observable<FoodItem> {
    return this.http.put<FoodItem>(`${this.apiUrl}${id}/`, item);
  }

  deleteItem(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}${id}/`);
  }
}
