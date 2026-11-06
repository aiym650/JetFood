import { ActivatedRouteSnapshot, Router, RouterStateSnapshot, UrlTree, provideRouter } from '@angular/router';
import { TestBed } from '@angular/core/testing';
import { Auth } from './auth';
import { roleGuard } from './auth.guard';

describe('roleGuard', () => {
  let currentUser: { role: string } | null;
  let router: Router;

  beforeEach(() => {
    currentUser = { role: 'manager' };
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        { provide: Auth, useValue: { getCurrentUser: () => currentUser } },
      ],
    });
    router = TestBed.inject(Router);
  });

  function activate(roles?: string[]) {
    const route = { data: roles ? { roles } : {} } as ActivatedRouteSnapshot;
    const state = { url: '/restricted' } as RouterStateSnapshot;
    return TestBed.runInInjectionContext(() => roleGuard(route, state));
  }

  it('allows users whose role is listed for the route', () => {
    expect(activate(['admin', 'manager'])).toBe(true);
  });

  it('redirects users without an allowed role to the dashboard', () => {
    currentUser = { role: 'customer' };
    const result = activate(['admin', 'manager']);

    expect(result).toBeInstanceOf(UrlTree);
    if (result instanceof UrlTree) {
      expect(router.serializeUrl(result)).toBe('/dashboard');
    }
  });

  it('allows routes without role restrictions', () => {
    currentUser = null;
    expect(activate()).toBe(true);
  });
});
