import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { vi } from 'vitest';
import { HttpErrorResponse } from '@angular/common/http';
import { Observable, of, throwError } from 'rxjs';

import { Register } from './register';
import { Auth } from '../../auth';
import { I18nService } from '../../i18n/i18n.service';

describe('Register', () => {
  let component: Register;
  let fixture: ComponentFixture<Register>;
  let authMock: {
    register: () => Observable<object>;
    getRegistrationErrorKey: (error: HttpErrorResponse) => string;
  };

  beforeEach(async () => {
    authMock = {
      register: () => of({}),
      getRegistrationErrorKey: Auth.prototype.getRegistrationErrorKey,
    };
    await TestBed.configureTestingModule({
      imports: [Register],
      providers: [
        provideRouter([]),
        { provide: Auth, useValue: authMock },
        { provide: I18nService, useValue: { currentLang$: of('en'), t: (key: string) => key } },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(Register);
    component = fixture.componentInstance;
    vi.spyOn(TestBed.inject(Router), 'navigate').mockResolvedValue(true);
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('shows a specific message when the username is already registered', () => {
    component.username = 'test-user';
    component.password = 'testpass123';
    component.confirmPassword = component.password;
    authMock.register = () => throwError(() => new HttpErrorResponse({
      status: 400,
      error: { username: ['A user with that username already exists.'] },
    }));

    component.onSubmit();

    expect(component.errorMessage).toBe(TestBed.inject(I18nService).t('registrationFailedUsername'));
  });

  it('shows the generic registration message for a network error', () => {
    component.username = 'test-user';
    component.password = 'testpass123';
    component.confirmPassword = component.password;
    authMock.register = () => throwError(() => new HttpErrorResponse({ status: 0 }));

    component.onSubmit();

    expect(component.errorMessage).toBe(TestBed.inject(I18nService).t('registrationFailed'));
  });

  it('should render working navigation links', () => {
    const links = fixture.nativeElement.querySelectorAll('a');

    expect(links[0].getAttribute('href')).toBe('/login');
    expect(links[1].getAttribute('href')).toBe('/landing');
  });

  it('registers without contacts and preserves spaces in the password', () => {
    let submitted: any;
    authMock.register = ((value: any) => { submitted = value; return of({}); }) as any;
    component.username = '  new-user  ';
    component.password = component.confirmPassword = ' password123 ';
    component.onSubmit();
    expect(submitted).toEqual({ username: 'new-user', email: '', phone: '', password: ' password123 ' });
    expect(fixture.nativeElement.querySelector('form').hasAttribute('novalidate')).toBe(true);
    expect(fixture.nativeElement.querySelector('#email').required).toBe(false);
  });

  it('validates only nonempty trimmed email and phone', () => {
    component.username = 'new-user';
    component.password = component.confirmPassword = 'password123';
    component.email = ' test@ ';
    component.onSubmit();
    expect(component.errorMessage).toBe('registrationFailedEmail');
    component.email = '   ';
    component.phone = 'abc123';
    component.onSubmit();
    expect(component.errorMessage).toBe('registrationFailedPhone');
    component.phone = ' +77011234567 ';
    component.onSubmit();
    expect(component.errorMessage).toBe('');
    expect(component.phone).toBe('+77011234567');
  });
});
