import { Injectable } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Observable, BehaviorSubject, finalize } from 'rxjs';
import { map } from 'rxjs/operators';

export interface AuthUser {
  id: number;
  username: string;
  email: string;
  role: string;
  first_name?: string;
  last_name?: string;
  phone?: string;
  address?: string;
}

interface LoginResponse {
  token: string;
  user: AuthUser;
}

@Injectable({
  providedIn: 'root',
})
export class Auth {
  private apiUrl = 'http://localhost:8000/api/auth';
  private currentUserSubject = new BehaviorSubject<AuthUser | null>(null);
  public currentUser$ = this.currentUserSubject.asObservable();
  private tokenSubject = new BehaviorSubject<string | null>(null);
  public token$ = this.tokenSubject.asObservable();

  constructor(private http: HttpClient) {
    this.syncSessionFromStorage();
    window.addEventListener('storage', this.handleStorageChange);
  }

  private readonly handleStorageChange = (event: StorageEvent): void => {
    if (event.storageArea === localStorage && (event.key === null || event.key === 'token' || event.key === 'user')) {
      this.syncSessionFromStorage();
    }
  };

  private syncSessionFromStorage(): void {
    const storedToken = localStorage.getItem('token');
    const storedUser = localStorage.getItem('user');
    if (!storedToken || !storedUser) {
      this.tokenSubject.next(null);
      this.currentUserSubject.next(null);
      return;
    }

    try {
      const user = JSON.parse(storedUser) as AuthUser;
      if (!user || typeof user.id !== 'number' || typeof user.username !== 'string' || typeof user.role !== 'string') {
        throw new Error('Stored user data is invalid.');
      }
      this.tokenSubject.next(storedToken);
      this.currentUserSubject.next(user);
    } catch (error) {
      console.error('Could not restore the stored user session.', error);
      this.clearLocalSession();
    }
  }

  refreshCurrentUser(): Observable<AuthUser> {
    return this.http.get<AuthUser>(`${this.apiUrl}/profile/`).pipe(
      map(user => {
        this.updateCurrentUser(user);
        return user;
      })
    );
  }

  login(username: string, password: string): Observable<LoginResponse> {
    return this.http.post<LoginResponse>(`${this.apiUrl}/login/`, { username, password })
      .pipe(
        map(response => {
          localStorage.setItem('token', response.token);
          localStorage.setItem('user', JSON.stringify(response.user));
          this.tokenSubject.next(response.token);
          this.currentUserSubject.next(response.user);
          return response;
        })
      );
  }

  register(userData: {
    username: string;
    email: string;
    password: string;
    phone: string;
  }): Observable<object> {
    return this.http.post(`${this.apiUrl}/register/`, userData);
  }

  logout(): Observable<void> {
    return this.http.post(`${this.apiUrl}/logout/`, {}).pipe(
      map(() => undefined),
      finalize(() => this.clearLocalSession())
    );
  }

  getRegistrationErrorKey(error: HttpErrorResponse): string {
    if (error.status === 0) {
      return 'backendUnavailable';
    }

    const errors = error.error;
    if (errors && typeof errors === 'object') {
      for (const field of ['username', 'email']) {
        const messages = errors[field];
        if (Array.isArray(messages) && messages.some(
          message => typeof message === 'string' && /already exists|already taken|unique/i.test(message)
        )) {
          return field === 'username' ? 'usernameAlreadyTaken' : 'emailAlreadyTaken';
        }
      }
    }

    return error.status >= 400 && error.status < 500
      ? 'registrationValidationFailed'
      : 'authRequestFailed';
  }

  getLoginErrorKey(error: HttpErrorResponse): string {
    if (error.status === 0) {
      return 'backendUnavailable';
    }
    return error.status === 400 || error.status === 401
      ? 'invalidCredentials'
      : 'authRequestFailed';
  }

  clearLocalSession(): void {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    this.tokenSubject.next(null);
    this.currentUserSubject.next(null);
  }

  updateCurrentUser(user: AuthUser): void {
    localStorage.setItem('user', JSON.stringify(user));
    this.currentUserSubject.next(user);
  }

  isLoggedIn(): boolean {
    return !!localStorage.getItem('token');
  }

  getCurrentUser(): AuthUser | null {
    this.syncSessionFromStorage();
    return this.currentUserSubject.value;
  }

  getToken(): string | null {
    this.syncSessionFromStorage();
    return this.tokenSubject.value;
  }

  hasRole(role: string): boolean {
    const user = this.getCurrentUser();
    return user ? user.role === role : false;
  }
}
