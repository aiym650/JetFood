import {
  HttpRequest,
  HttpHandlerFn,
  HttpEvent,
  HttpErrorResponse
} from '@angular/common/http';
import { Observable, TimeoutError, catchError, throwError, timeout } from 'rxjs';
import { inject } from '@angular/core';
import { Router } from '@angular/router';

const BACKEND_API_PREFIX = 'http://localhost:8000/api/';

export function authInterceptor(
  request: HttpRequest<unknown>,
  next: HttpHandlerFn
): Observable<HttpEvent<unknown>> {
  const router = inject(Router);
  const token = localStorage.getItem('token');

  if (token && request.url.startsWith(BACKEND_API_PREFIX)) {
    request = request.clone({
      setHeaders: {
        Authorization: `Token ${token}`
      }
    });
  }

  return next(request).pipe(
    timeout({ first: 15000 }),
    catchError((error: unknown) => {
      const httpError = error instanceof TimeoutError
        ? new HttpErrorResponse({
          error,
          status: 0,
          statusText: 'Request timed out',
          url: request.url,
        })
        : error;

      if (httpError instanceof HttpErrorResponse && httpError.status === 401) {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        router.navigate(['/login']);
      }
      return throwError(() => httpError);
    })
  );
}
