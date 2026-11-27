import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { map, Observable } from 'rxjs';
import { ApiListResponse, getApiListResults } from './shared/api-list';

export interface RestaurantBranch {
  id: number;
  catalog_key?: string | null;
  address: string;
  phone: string;
  opening_time: string | null;
  closing_time: string | null;
  working_days: number[];
  is_active: boolean;
  delivery_available: boolean | null;
  delivery_info: string;
  source_url: string;
}

export interface Restaurant {
  cuisine?: string;
  catalog_key?: string | null;
  demo_key?: string | null;
  id: number;
  name: string;
  description: string;
  address: string;
  phone: string;
  image_url: string;
  source_url?: string;
  menu_source_url?: string;
  branches?: RestaurantBranch[];
  opening_time: string | null;
  closing_time: string | null;
  working_days: number[];
  is_active: boolean;
  owner?: number | null;
  avg_rating?: number | string;
  reviews_count?: number;
}

export type RestaurantInput = Omit<Restaurant, 'id'>;
export type RestaurantSort = 'name' | 'rating';

@Injectable({ providedIn: 'root' })
export class Restaurants {
  private readonly apiUrl = 'http://localhost:8000/api/restaurants/';

  constructor(private http: HttpClient) {}

  getRestaurants(): Observable<Restaurant[]> {
    return this.http.get<ApiListResponse<Restaurant>>(this.apiUrl)
      .pipe(map(getApiListResults));
  }

  createRestaurant(restaurant: RestaurantInput): Observable<Restaurant> {
    return this.http.post<Restaurant>(this.apiUrl, restaurant);
  }

  updateRestaurant(id: number, restaurant: RestaurantInput): Observable<Restaurant> {
    return this.http.put<Restaurant>(`${this.apiUrl}${id}/`, restaurant);
  }

  deleteRestaurant(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}${id}/`);
  }
}
