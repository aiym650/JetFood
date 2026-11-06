import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { map, Observable } from 'rxjs';
import { ApiListResponse, getApiListResults } from './shared/api-list';

export interface Restaurant {
  id: number;
  name: string;
  description: string;
  address: string;
  phone: string;
  image_url: string;
  opening_time: string;
  closing_time: string;
  working_days: number[];
  is_active: boolean;
}

export type RestaurantInput = Omit<Restaurant, 'id'>;

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
