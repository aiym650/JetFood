import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of } from 'rxjs';
import { Auth } from '../../auth';
import { SidebarComponent } from './sidebar';
import { I18nService } from '../../i18n/i18n.service';

describe('Sidebar SVG navigation', () => {
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
