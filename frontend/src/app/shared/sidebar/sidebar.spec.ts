import { TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { of, throwError } from 'rxjs';
import { Auth } from '../../auth';
import { SidebarComponent } from './sidebar';
import { I18nService } from '../../i18n/i18n.service';

describe('Sidebar SVG navigation', () => {
  afterEach(() => localStorage.removeItem('lang'));

  for (const collapsed of [false, true]) {
    for (const serverFails of [false, true]) {
      it(`logs out from the accessible button (collapsed=${collapsed}, serverFails=${serverFails})`, async () => {
        const logout = vi.fn(() => serverFails ? throwError(() => new Error('offline')) : of(undefined));
        await TestBed.configureTestingModule({ imports: [SidebarComponent], providers: [
          provideRouter([]), { provide: Auth, useValue: { logout } },
        ] }).compileComponents();
        const navigate = vi.spyOn(TestBed.inject(Router), 'navigate').mockResolvedValue(true);
        const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
        const fixture = TestBed.createComponent(SidebarComponent);
        fixture.componentInstance.currentUser = { username: 'customer', role: 'customer' };
        fixture.componentInstance.isCollapsed = collapsed;
        TestBed.inject(I18nService).setLanguage('kk');
        fixture.detectChanges();
        const buttons = fixture.nativeElement.querySelectorAll('.logout-btn');
        expect(buttons).toHaveLength(1);
        const button = buttons[0] as HTMLButtonElement;
        expect(button.type).toBe('button');
        expect(button.getAttribute('aria-label')).toBe('Шығу');
        expect(button.title).toBe('Шығу');
        expect(button.disabled).toBe(false);
        button.click();
        expect(logout).toHaveBeenCalledTimes(1);
        expect(navigate).toHaveBeenCalledWith(['/landing']);
        consoleError.mockRestore();
      });
    }
  }

  it('keeps accessible links and role restrictions when collapsed', async () => {
    await TestBed.configureTestingModule({ imports: [SidebarComponent], providers: [
      provideRouter([]), { provide: Auth, useValue: { logout: () => of(undefined) } },
    ] }).compileComponents();
    const fixture = TestBed.createComponent(SidebarComponent);
    fixture.componentInstance.currentUser = { username: 'customer', role: 'customer' };
    TestBed.inject(I18nService).setLanguage('en');
    fixture.detectChanges();
    const root: HTMLElement = fixture.nativeElement;
    expect(root.querySelector('a[href="/dashboard"] svg path')).not.toBeNull();
    expect(root.querySelector('a[href="/admin"]')).toBeNull();
    expect(root.querySelector('a[href="/analytics"]')).toBeNull();
    expect(root.querySelector('a[href="/reports"]')).toBeNull();
    expect(root.querySelector('.nav-label')).not.toBeNull();
    (root.querySelector('.toggle-btn') as HTMLButtonElement).click();
    fixture.detectChanges();
    expect(root.querySelector('.nav-label')).toBeNull();
    const dashboard = root.querySelector('a[href="/dashboard"]')!;
    expect(dashboard.getAttribute('aria-label')).toBe('Dashboard');
    expect(dashboard.getAttribute('title')).toBe('Dashboard');
    expect(root.querySelector('.logout-btn svg')).not.toBeNull();
  });
});
