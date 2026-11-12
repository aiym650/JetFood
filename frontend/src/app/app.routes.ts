import { Routes } from '@angular/router';
import { Login } from './auth/login/login';
import { Register } from './auth/register/register';
import { Dashboard } from './dashboard/dashboard';
import { InfoPage } from './info-page/info-page';
import { LandingComponent } from './landing/landing';
import { AppShell } from './layout/app-shell';
import { authGuard, roleGuard } from './auth.guard';

export const routes: Routes = [
  { path: 'landing', component: LandingComponent },
  { path: 'login', component: Login },
  { path: 'register', component: Register },
  { path: 'about', component: InfoPage, data: { titleKey: 'aboutUs', descriptionKey: 'aboutUsPageDescription' } },
  { path: 'careers', component: InfoPage, data: { titleKey: 'careers', descriptionKey: 'careersPageDescription' } },
  { path: 'blog', component: InfoPage, data: { titleKey: 'blog', descriptionKey: 'blogPageDescription' } },
  { path: 'faq', component: InfoPage, data: { titleKey: 'faq', descriptionKey: 'faqPageDescription' } },
  { path: 'contacts', component: InfoPage, data: { titleKey: 'contacts', descriptionKey: 'contactsPageDescription' } },
  { path: 'support', component: InfoPage, data: { titleKey: 'support', descriptionKey: 'supportPageDescription' } },
  { path: '', redirectTo: '/landing', pathMatch: 'full' },
  {
    path: '',
    component: AppShell,
    canActivate: [authGuard],
    children: [
      { path: 'dashboard', component: Dashboard },
      {
        path: 'orders',
        loadComponent: () => import('./orders/orders').then(module => module.OrdersPage),
      },
      {
        path: 'profile',
        loadComponent: () => import('./profile/profile').then(module => module.ProfilePage),
      },
      {
        path: 'payments',
        loadComponent: () => import('./payment-history/payment-history').then(module => module.PaymentHistoryPage),
      },
      {
        path: 'restaurants/:id',
        loadComponent: () => import('./restaurants/restaurants').then(module => module.RestaurantsPage),
      },
      {
        path: 'restaurants',
        loadComponent: () => import('./restaurants/restaurants').then(module => module.RestaurantsPage),
      },
      {
        path: 'analytics',
        loadComponent: () => import('./analytics/analytics').then(module => module.AnalyticsComponent),
        canActivate: [roleGuard],
        data: { roles: ['admin', 'manager', 'analyst'] },
      },
      {
        path: 'reports',
        loadComponent: () => import('./reports/reports').then(module => module.ReportsComponent),
      },
      {
        path: 'integration',
        loadComponent: () => import('./integration/integration').then(module => module.IntegrationComponent),
        canActivate: [roleGuard],
        data: { roles: ['admin', 'manager'] },
      },
      {
        path: 'admin',
        loadComponent: () => import('./admin/admin').then(module => module.AdminComponent),
        canActivate: [roleGuard],
        data: { roles: ['admin'] },
      },
      {
        path: 'notifications',
        loadComponent: () => import('./notifications/notifications').then(module => module.NotificationsComponent),
      },
    ],
  },
  { path: '**', redirectTo: '/landing' }
];
