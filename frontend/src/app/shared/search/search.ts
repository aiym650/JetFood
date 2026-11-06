import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { map, Observable } from 'rxjs';
import { ApiListResponse, getApiListResults } from '../api-list';

@Injectable({
  providedIn: 'root'
})
export class SearchService {
  private apiUrl = 'http://localhost:8000/api';

  constructor(private http: HttpClient) {}

  searchOrders(query: string): Observable<any[]> {
    return this.http.get<ApiListResponse<any>>(`${this.apiUrl}/orders/`, { params: { search: query } })
      .pipe(map(getApiListResults));
  }

  searchUsers(query: string): Observable<any[]> {
    return this.http.get<ApiListResponse<any>>(`${this.apiUrl}/auth/users/`, { params: { search: query } })
      .pipe(map(getApiListResults));
  }

  searchAll(query: string): Observable<{ orders: any[], users: any[], menu_items: any[] }> {
    const params = new HttpParams().set('q', query.trim());
    return this.http.get<{ orders: any[], users: any[], menu_items: any[] }>(`${this.apiUrl}/search/`, { params });
  }
}
