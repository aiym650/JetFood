import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router } from '@angular/router';
import { of } from 'rxjs';
import { vi } from 'vitest';

import { Auth } from '../auth';
import { Menu } from '../menu';
import { Restaurant, Restaurants } from '../restaurants';
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
          createRestaurant: () => of({} as Restaurant),
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

  it('searches branch addresses and sorts restaurants with verified ratings first', () => {
    const makeRestaurant = (
      id: number,
      name: string,
      rating: number,
      reviews: number,
      branchAddress: string,
    ): Restaurant => ({
      id,
      name,
      cuisine: 'Бургеры',
      description: '',
      address: branchAddress,
      phone: '',
      image_url: '',
      opening_time: null,
      closing_time: null,
      working_days: [],
      is_active: true,
      avg_rating: rating,
      reviews_count: reviews,
      branches: [{
        id: id * 10,
        address: branchAddress,
        phone: '',
        opening_time: null,
        closing_time: null,
        working_days: [],
        is_active: true,
        delivery_available: null,
        delivery_info: '',
        source_url: '',
      }],
    });

    component.restaurants = [
      makeRestaurant(1, 'A Burger', 4.2, 2, 'Satpaeva 10'),
      makeRestaurant(2, 'B Burger', 4.8, 1, 'Abay 20'),
      makeRestaurant(3, 'C Burger', 0, 0, 'Main Street 30'),
    ];
    component.search = 'Satpaeva';
    expect(component.filteredRestaurants.map(item => item.name)).toEqual(['A Burger']);

    component.search = '';
    component.sortBy = 'rating';
    expect(component.filteredRestaurants.map(item => item.name)).toEqual(['B Burger', 'A Burger', 'C Burger']);
  });

  it('saves unknown opening hours as null rather than rejecting or submitting blanks', () => {
    const createRestaurant = vi.spyOn(TestBed.inject(Restaurants), 'createRestaurant');
    component.restaurantForm = {
      ...component.restaurantForm,
      name: 'Unknown Hours Kitchen',
      address: 'Main Street 10',
      opening_time: '',
      closing_time: '',
      working_days: [],
    };

    component.saveRestaurant();

    expect(createRestaurant).toHaveBeenCalledWith(expect.objectContaining({
      opening_time: null,
      closing_time: null,
      working_days: [],
    }));
    expect(component.restaurantFormError).toBe('');
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

  it('renders restaurant and review labels in Kazakh', () => {
    TestBed.inject(I18nService).setLanguage('kk');
    fixture.changeDetectorRef.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('Мейрамханалар');
    expect(fixture.nativeElement.textContent).toContain('Мейрамхана атауы');

    component.selectedRestaurant = component.restaurants[0];
    fixture.changeDetectorRef.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Пікірлер');
    expect(fixture.nativeElement.textContent).toContain('Әзірге жарияланған пікірлер жоқ.');
    expect(fixture.nativeElement.textContent).not.toContain('No published reviews yet.');
  });
});
