import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpClient } from '@angular/common/http';
import { provideRouter } from '@angular/router';
import { of } from 'rxjs';
import { vi } from 'vitest';

import { Addresses } from '../addresses';
import { Auth } from '../auth';
import { I18nService } from '../i18n/i18n.service';
import { ProfilePage } from './profile';

describe('ProfilePage', () => {
  let fixture: ComponentFixture<ProfilePage>;
  let component: ProfilePage;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ProfilePage],
      providers: [
        provideRouter([]),
        {
          provide: Auth,
          useValue: {
            getCurrentUser: () => ({ id: 7, username: 'customer', email: 'customer@example.com', role: 'customer' }),
            updateCurrentUser: vi.fn(),
            clearLocalSession: vi.fn(),
          },
        },
        { provide: Addresses, useValue: { getAddresses: () => of([]) } },
        {
          provide: HttpClient,
          useValue: {
            get: () => of({
              id: 7,
              username: 'customer',
              email: 'customer@example.com',
              role: 'customer',
              phone: '',
              address: '',
            }),
            patch: () => of({ id: 7, username: 'customer', email: 'customer@example.com', role: 'customer' }),
            post: () => of({}),
            delete: () => of({}),
          },
        },
      ],
    }).compileComponents();

    TestBed.inject(I18nService).setLanguage('en');
    fixture = TestBed.createComponent(ProfilePage);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('loads the profile and account settings', () => {
    expect(component.profile.username).toBe('customer');
    expect(fixture.nativeElement.textContent).toContain('Delivery addresses');
    expect(fixture.nativeElement.textContent).toContain('Change password');
  });

  it('rejects mismatched password confirmation before making a request', () => {
    component.passwordForm = {
      old_password: 'old-password',
      new_password: 'new-password',
      confirm_password: 'different-password',
    };

    component.changePassword();

    expect(component.passwordError).toBe('Passwords do not match');
    expect(component.passwordSaving).toBe(false);
  });
});
