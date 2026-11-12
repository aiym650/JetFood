import { TestBed } from '@angular/core/testing';
import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { authInterceptor } from './auth.interceptor';

describe('authInterceptor', () => {
  let http: HttpClient;
  let httpTesting: HttpTestingController;

  beforeEach(() => {
    localStorage.setItem('token', 'private-api-token');
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        provideHttpClient(withInterceptors([authInterceptor])),
        provideHttpClientTesting(),
      ],
    });
    http = TestBed.inject(HttpClient);
    httpTesting = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpTesting.verify();
    localStorage.removeItem('token');
  });

  it('attaches the session token to JetFood backend requests', () => {
    http.get('http://localhost:8000/api/orders/').subscribe();
    const request = httpTesting.expectOne('http://localhost:8000/api/orders/');

    expect(request.request.headers.get('Authorization')).toBe('Token private-api-token');
    request.flush([]);
  });

  it('never sends the session token to the external route provider', () => {
    http.get('https://router.project-osrm.org/route/v1/driving/76.8,43.2;76.9,43.3').subscribe();
    const request = httpTesting.expectOne('https://router.project-osrm.org/route/v1/driving/76.8,43.2;76.9,43.3');

    expect(request.request.headers.has('Authorization')).toBe(false);
    request.flush({ code: 'Ok', routes: [] });
  });
});
