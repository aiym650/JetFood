import { TestBed } from '@angular/core/testing';
import { HttpErrorResponse, provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';

import { Auth } from './auth';

describe('Auth', () => {
  let service: Auth;
  let httpTesting: HttpTestingController;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    httpTesting = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpTesting.verify();
    localStorage.clear();
  });

  it('should be created', () => {
    service = TestBed.inject(Auth);
    expect(service).toBeTruthy();
  });

  it('clears the local session even when the logout request fails', () => {
    localStorage.setItem('token', 'test-token');
    localStorage.setItem('user', JSON.stringify({
      id: 1,
      username: 'test',
      email: 'test@example.com',
      role: 'customer',
    }));
    service = TestBed.inject(Auth);
    let receivedError: unknown;

    service.logout().subscribe({ error: error => receivedError = error });

    httpTesting.expectOne('http://localhost:8000/api/auth/logout/').flush(
      { detail: 'Unavailable' },
      { status: 503, statusText: 'Service Unavailable' },
    );

    expect(receivedError).toBeInstanceOf(HttpErrorResponse);
    expect(localStorage.getItem('token')).toBeNull();
    expect(localStorage.getItem('user')).toBeNull();
    expect(service.isLoggedIn()).toBe(false);
  });

  it('synchronizes the cached user with the backend profile', () => {
    localStorage.setItem('token', 'manager-token');
    localStorage.setItem('user', JSON.stringify({
      id: 1,
      username: 'stale-manager',
      email: 'manager@example.com',
      role: 'manager',
    }));
    service = TestBed.inject(Auth);
    let currentUser = service.getCurrentUser();

    service.refreshCurrentUser().subscribe(user => currentUser = user);
    const request = httpTesting.expectOne('http://localhost:8000/api/auth/profile/');
    request.flush({
      id: 2,
      username: 'actual-customer',
      email: 'customer@example.com',
      role: 'customer',
      phone: '',
      address: '',
    });

    expect(currentUser?.username).toBe('actual-customer');
    expect(JSON.parse(localStorage.getItem('user') ?? '{}').role).toBe('customer');
  });

  it('synchronizes account changes made in another browser tab', () => {
    localStorage.setItem('token', 'manager-token');
    localStorage.setItem('user', JSON.stringify({
      id: 1,
      username: 'demo_manager',
      email: 'manager@example.com',
      role: 'manager',
    }));
    service = TestBed.inject(Auth);
    localStorage.setItem('token', 'customer-token');
    localStorage.setItem('user', JSON.stringify({
      id: 2,
      username: 'customer',
      email: 'customer@example.com',
      role: 'customer',
    }));

    window.dispatchEvent(new StorageEvent('storage', {
      key: 'token',
      newValue: 'customer-token',
      storageArea: localStorage,
    }));

    expect(service.getToken()).toBe('customer-token');
    expect(service.getCurrentUser()?.username).toBe('customer');
  });
});
