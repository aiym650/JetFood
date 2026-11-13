import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router } from '@angular/router';
import { of } from 'rxjs';
import { vi } from 'vitest';

import { Auth } from '../auth';
import { Menu } from '../menu';
import { Restaurants } from '../restaurants';
import { I18nService } from '../i18n/i18n.service';
import { RestaurantsPage } from './restaurants';

describe('RestaurantsPage', () => {
  let fixture: ComponentFixture<RestaurantsPage>;
  let component: RestaurantsPage;
  const router = { navigate: vi.fn() };

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
        { provide: Menu, useValue: { getItems: () => of([{
          id: 1,
          name: 'Soup',
          description: 'Daily soup',
          category: 'Lunch',
          price: 8.5,
          image_url: '',
          rating: 4.5,
          restaurant: 1,
          is_active: true,
        }]) } },
        { provide: Auth, useValue: { getCurrentUser: () => ({ role: 'manager' }) } },
        { provide: Router, useValue: router },
        {
          provide: ActivatedRoute,
          useValue: {
            paramMap: of({ get: () => null }),
            snapshot: { paramMap: { get: () => null } },
          },
        },
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
    expect(fixture.nativeElement.textContent).not.toContain('Menu management');
  });

  it('navigates to the selected restaurant page', () => {
    component.selectRestaurant(component.restaurants[0]);

    expect(router.navigate).toHaveBeenCalledWith(['/restaurants', 1]);
  });

  it('lets customers view dishes on a restaurant detail page', () => {
    component.currentUser = { role: 'customer' };
    component.selectedRestaurant = component.restaurants[0];
    component.loadMenu(component.selectedRestaurant);
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('Soup');
    expect(fixture.nativeElement.textContent).not.toContain('Add dish');
    expect(fixture.nativeElement.textContent).not.toContain('Register a restaurant');
  });
});
