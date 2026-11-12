import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, provideRouter } from '@angular/router';
import { of } from 'rxjs';
import { I18nService } from '../i18n/i18n.service';
import { InfoPage } from './info-page';

describe('InfoPage', () => {
  let fixture: ComponentFixture<InfoPage>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [InfoPage],
      providers: [
        provideRouter([]),
        {
          provide: ActivatedRoute,
          useValue: {
            snapshot: {
              data: {
                titleKey: 'aboutUs',
                descriptionKey: 'aboutUsPageDescription',
              },
            },
          },
        },
        {
          provide: I18nService,
          useValue: {
            currentLang$: of('en'),
            t: (key: string) => ({
              aboutUs: 'О нас',
              aboutUsPageDescription: 'Информация о JetFood.',
              backToHome: 'Вернуться на главную',
            }[key] ?? key),
          },
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(InfoPage);
    fixture.detectChanges();
  });

  it('renders route-specific information and a working home link', () => {
    expect(fixture.nativeElement.querySelector('h1').textContent).toContain('О нас');
    expect(fixture.nativeElement.querySelector('.description').textContent).toContain('Информация о JetFood.');
    expect(fixture.nativeElement.querySelector('.back-link').getAttribute('href')).toBe('/landing');
  });
});
