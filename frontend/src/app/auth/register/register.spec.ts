import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of } from 'rxjs';

import { Register } from './register';
import { Auth } from '../../auth';
import { I18nService } from '../../i18n/i18n.service';

describe('Register', () => {
  let component: Register;
  let fixture: ComponentFixture<Register>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Register],
      providers: [
        provideRouter([]),
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

  it('should render working navigation links', () => {
    const links = fixture.nativeElement.querySelectorAll('a');

    expect(links[0].getAttribute('href')).toBe('/login');
    expect(links[1].getAttribute('href')).toBe('/landing');
  });
});
