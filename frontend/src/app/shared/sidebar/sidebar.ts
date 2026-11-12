import { ChangeDetectorRef, Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule } from '@angular/router';
import { Auth } from '../../auth';
import { I18nService } from '../../i18n/i18n.service';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

@Component({
  selector: 'app-sidebar',
  imports: [CommonModule, RouterModule],
  templateUrl: './sidebar.html',
  styleUrl: './sidebar.css',
})
export class SidebarComponent {
  @Input() currentUser: any;
  @Output() toggleSidebar = new EventEmitter<void>();

  isCollapsed = false;

  private readonly menuItems = [
    { icon: '⌂', label: 'dashboard', route: '/dashboard' },
    { icon: 'U', label: 'profile', route: '/profile' },
    { icon: 'P', label: 'payments', route: '/payments' },
    { icon: 'R', label: 'restaurants', route: '/restaurants' },
    { icon: '▤', label: 'orders', route: '/orders' },
    { icon: '▥', label: 'analytics', route: '/analytics', roles: ['admin', 'manager', 'analyst'] },
    { icon: '▧', label: 'reports', route: '/reports' },
    { icon: '↗', label: 'integration', route: '/integration', roles: ['admin', 'manager'] },
    { icon: '○', label: 'notifications', route: '/notifications' },
  ];

  constructor(
    private auth: Auth,
    private router: Router,
    private changeDetector: ChangeDetectorRef,
    public i18n: I18nService
  ) {
    this.i18n.currentLang$
      .pipe(takeUntilDestroyed())
      .subscribe(() => this.changeDetector.markForCheck());
  }

  get visibleMenuItems() {
    const role = this.currentUser?.role;
    return this.menuItems.filter(item => !item.roles || item.roles.includes(role ?? ''));
  }

  roleLabel(role: string): string {
    const key = `roles.${role}`;
    const label = this.i18n.t(key);
    return label === key ? role : label;
  }

  toggle(): void {
    this.isCollapsed = !this.isCollapsed;
    this.toggleSidebar.emit();
  }

  logout(): void {
    this.auth.logout().subscribe({
      next: () => this.router.navigate(['/landing']),
      error: (error) => {
        console.error('Server logout failed; local session was cleared.', error);
        this.router.navigate(['/landing']);
      },
    });
  }
}
