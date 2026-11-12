import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of } from 'rxjs';

import { Login } from './login';
import { Auth } from '../../auth';
import { I18nService } from '../../i18n/i18n.service';

describe('Login', () => {
  let component: Login;
  let fixture: ComponentFixture<Login>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Login],
      providers: [
        provideRouter([]),
        { provide: Auth, useValue: { login: () => of({}) } },
        { provide: I18nService, useValue: { currentLang$: of('en'), t: (key: string) => key } },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(Login);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should render working navigation links', () => {
    const links = fixture.nativeElement.querySelectorAll('a');

    expect(links[0].getAttribute('href')).toBe('/register');
    expect(links[1].getAttribute('href')).toBe('/landing');
  });
});
