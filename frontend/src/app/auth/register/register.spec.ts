import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
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
        { provide: Auth, useValue: { register: () => of({}) } },
        { provide: I18nService, useValue: { currentLang$: of('en'), t: (key: string) => key } },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(Register);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('shows a specific message when the username is already registered', () => {
    component.password = 'testpass123';
    component.confirmPassword = component.password;
    authMock.register = () => throwError(() => new HttpErrorResponse({
      status: 400,
      error: { username: ['A user with that username already exists.'] },
    }));

    component.onSubmit();

    expect(component.errorMessage).toBe(TestBed.inject(I18nService).t('usernameAlreadyTaken'));
  });

  it('shows a backend connection message when registration cannot reach the server', () => {
    component.password = 'testpass123';
    component.confirmPassword = component.password;
    authMock.register = () => throwError(() => new HttpErrorResponse({ status: 0 }));

    component.onSubmit();

    expect(component.errorMessage).toBe(TestBed.inject(I18nService).t('backendUnavailable'));
  it('should render working navigation links', () => {
    const links = fixture.nativeElement.querySelectorAll('a');

    expect(links[0].getAttribute('href')).toBe('/login');
    expect(links[1].getAttribute('href')).toBe('/landing');
  });
});
