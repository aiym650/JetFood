import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { Auth } from './auth';

export const authGuard: CanActivateFn = () => {
  const auth = inject(Auth);
  const router = inject(Router);
  return auth.isLoggedIn() ? true : router.createUrlTree(['/login']);
};

export const roleGuard: CanActivateFn = (route) => {
  const auth = inject(Auth);
  const router = inject(Router);
  const allowedRoles = route.data['roles'] as string[] | undefined;
  const user = auth.getCurrentUser();

  if (!allowedRoles || (user && allowedRoles.includes(user.role))) {
    return true;
  }

  return router.createUrlTree(['/dashboard']);
};
