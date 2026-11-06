import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';

import { SearchService } from './search';

describe('SearchService', () => {
  let service: SearchService;
  let httpTesting: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(SearchService);
    httpTesting = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpTesting.verify());

  it('searches all supported entity types using safely encoded query parameters', () => {
    let response: unknown;
    service.searchAll('pizza & pasta').subscribe((value) => response = value);

    const request = httpTesting.expectOne((req) => req.url === 'http://localhost:8000/api/search/');
    expect(request.request.params.get('q')).toBe('pizza & pasta');
    request.flush({ orders: [], users: [], menu_items: [] });

    expect(response).toEqual({ orders: [], users: [], menu_items: [] });
  });
});
