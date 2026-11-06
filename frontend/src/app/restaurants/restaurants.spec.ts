import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of } from 'rxjs';

import { Auth } from '../auth';
import { Menu } from '../menu';
import { Restaurants } from '../restaurants';
import { I18nService } from '../i18n/i18n.service';
import { RestaurantsPage } from './restaurants';

describe('RestaurantsPage', () => {
  let fixture: ComponentFixture<RestaurantsPage>;
  let component: RestaurantsPage;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [RestaurantsPage],
      providers: [
        {
          provide: Restaurants,
          useValue: {
            getRestaurants: () => of([{
              id: 1,
              name: 'North Kitchen',
              description: 'Local meals',
              address: 'Main Street 1',
              phone: '',
              image_url: '',
              opening_time: '09:00:00',
              closing_time: '21:00:00',
              working_days: [0, 1, 2, 3, 4, 5, 6],
              is_active: true,
            }]),
          },
        },
        { provide: Menu, useValue: { getItems: () => of([]) } },
        { provide: Auth, useValue: { getCurrentUser: () => ({ role: 'manager' }) } },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(RestaurantsPage);
    component = fixture.componentInstance;
    TestBed.inject(I18nService).setLanguage('en');
    fixture.detectChanges();
  });

  it('loads restaurant listings', () => {
    expect(component.restaurants).toHaveLength(1);
    expect(fixture.nativeElement.textContent).toContain('North Kitchen');
  });

  it('shows restaurant and menu management to managers', () => {
    expect(component.canManage).toBe(true);
    expect(fixture.nativeElement.textContent).toContain('Register a restaurant');
    expect(fixture.nativeElement.textContent).toContain('Menu management');
  });
});
