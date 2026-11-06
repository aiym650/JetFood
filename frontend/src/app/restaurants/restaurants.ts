import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { FoodItem, FoodItemInput, Menu } from '../menu';
import { Restaurant, RestaurantInput, Restaurants } from '../restaurants';
import { Auth } from '../auth';
import { I18nService } from '../i18n/i18n.service';

@Component({
  selector: 'app-restaurants',
  imports: [CommonModule, FormsModule],
  templateUrl: './restaurants.html',
  styleUrl: './restaurants.css',
})
export class RestaurantsPage implements OnInit {
  currentUser: { role: string } | null = null;
  restaurants: Restaurant[] = [];
  selectedRestaurant: Restaurant | null = null;
  menuItems: FoodItem[] = [];
  loading = false;
  menuLoading = false;
  saving = false;
  error = '';
  menuError = '';
  restaurantFormError = '';
  menuFormError = '';
  editingRestaurantId: number | null = null;
  editingMenuItemId: number | null = null;

  restaurantForm = this.emptyRestaurantForm();
  menuForm = this.emptyMenuForm();

  readonly weekdays = [
    { value: 0, key: 'monday' },
    { value: 1, key: 'tuesday' },
    { value: 2, key: 'wednesday' },
    { value: 3, key: 'thursday' },
    { value: 4, key: 'friday' },
    { value: 5, key: 'saturday' },
    { value: 6, key: 'sunday' },
  ];

  get canManage(): boolean {
    return ['admin', 'manager'].includes(this.currentUser?.role ?? '');
  }

  constructor(
    private restaurantsService: Restaurants,
    private menuService: Menu,
    private auth: Auth,
    private changeDetector: ChangeDetectorRef,
    public i18n: I18nService,
  ) {}

  ngOnInit(): void {
    this.currentUser = this.auth.getCurrentUser();
    this.loadRestaurants();
  }

  loadRestaurants(): void {
    this.loading = true;
    this.error = '';
    this.restaurantsService.getRestaurants().subscribe({
      next: (restaurants) => {
        this.restaurants = restaurants;
        if (this.selectedRestaurant) {
          this.selectedRestaurant = restaurants.find(item => item.id === this.selectedRestaurant?.id) ?? null;
          if (this.selectedRestaurant) this.loadMenu(this.selectedRestaurant);
        }
        this.loading = false;
        this.changeDetector.markForCheck();
      },
      error: () => {
        this.error = this.i18n.t('restaurantsLoadFailed');
        this.loading = false;
        this.changeDetector.markForCheck();
      },
    });
  }

  selectRestaurant(restaurant: Restaurant): void {
    this.selectedRestaurant = restaurant;
    this.resetMenuForm();
    this.loadMenu(restaurant);
  }

  loadMenu(restaurant: Restaurant): void {
    this.menuLoading = true;
    this.menuError = '';
    this.menuService.getItems(restaurant.id).subscribe({
      next: (items) => {
        this.menuItems = items;
        this.menuLoading = false;
        this.changeDetector.markForCheck();
      },
      error: () => {
        this.menuError = this.i18n.t('restaurantMenuLoadFailed');
        this.menuLoading = false;
        this.changeDetector.markForCheck();
      },
    });
  }

  toggleWorkingDay(day: number, checked: boolean): void {
    const days = new Set(this.restaurantForm.working_days);
    if (checked) days.add(day);
    else days.delete(day);
    this.restaurantForm.working_days = [...days].sort();
  }

  saveRestaurant(): void {
    this.restaurantFormError = '';
    if (this.restaurantForm.working_days.length === 0) {
      this.restaurantFormError = this.i18n.t('chooseWorkingDay');
      return;
    }

    this.saving = true;
    const request = this.editingRestaurantId
      ? this.restaurantsService.updateRestaurant(this.editingRestaurantId, this.restaurantForm)
      : this.restaurantsService.createRestaurant(this.restaurantForm);
    request.subscribe({
      next: (restaurant) => {
        this.selectedRestaurant = restaurant;
        this.resetRestaurantForm();
        this.loadRestaurants();
        this.saving = false;
        this.changeDetector.markForCheck();
      },
      error: () => {
        this.restaurantFormError = this.i18n.t('restaurantSaveFailed');
        this.saving = false;
        this.changeDetector.markForCheck();
      },
    });
  }

  editRestaurant(restaurant: Restaurant): void {
    this.editingRestaurantId = restaurant.id;
    this.restaurantForm = {
      name: restaurant.name,
      description: restaurant.description,
      address: restaurant.address,
      phone: restaurant.phone,
      image_url: restaurant.image_url,
      opening_time: restaurant.opening_time.slice(0, 5),
      closing_time: restaurant.closing_time.slice(0, 5),
      working_days: [...restaurant.working_days],
      is_active: restaurant.is_active,
    };
  }

  deleteRestaurant(restaurant: Restaurant): void {
    if (!confirm(this.i18n.t('confirmDeleteRestaurant'))) return;
    this.restaurantsService.deleteRestaurant(restaurant.id).subscribe({
      next: () => {
        if (this.selectedRestaurant?.id === restaurant.id) {
          this.selectedRestaurant = null;
          this.menuItems = [];
        }
        this.loadRestaurants();
      },
      error: () => {
        this.error = this.i18n.t('restaurantDeleteFailed');
        this.changeDetector.markForCheck();
      },
    });
  }

  saveMenuItem(): void {
    if (!this.selectedRestaurant) return;
    this.menuFormError = '';
    this.saving = true;
    const input: FoodItemInput = {
      ...this.menuForm,
      price: Number(this.menuForm.price),
      restaurant: this.selectedRestaurant.id,
    };
    const request = this.editingMenuItemId
      ? this.menuService.updateItem(this.editingMenuItemId, input)
      : this.menuService.createItem(input);
    request.subscribe({
      next: () => {
        this.resetMenuForm();
        this.loadMenu(this.selectedRestaurant!);
        this.saving = false;
        this.changeDetector.markForCheck();
      },
      error: () => {
        this.menuFormError = this.i18n.t('menuItemSaveFailed');
        this.saving = false;
        this.changeDetector.markForCheck();
      },
    });
  }

  editMenuItem(item: FoodItem): void {
    this.editingMenuItemId = item.id;
    this.menuForm = {
      name: item.name,
      description: item.description,
      category: item.category,
      price: Number(item.price),
      image_url: item.image_url,
      is_active: item.is_active ?? true,
    };
  }

  deleteMenuItem(item: FoodItem): void {
    if (!confirm(this.i18n.t('confirmDeleteMenuItem'))) return;
    this.menuService.deleteItem(item.id).subscribe({
      next: () => this.selectedRestaurant && this.loadMenu(this.selectedRestaurant),
      error: () => {
        this.menuError = this.i18n.t('menuItemDeleteFailed');
        this.changeDetector.markForCheck();
      },
    });
  }

  resetRestaurantForm(): void {
    this.editingRestaurantId = null;
    this.restaurantForm = this.emptyRestaurantForm();
    this.restaurantFormError = '';
  }

  resetMenuForm(): void {
    this.editingMenuItemId = null;
    this.menuForm = this.emptyMenuForm();
    this.menuFormError = '';
  }

  private emptyRestaurantForm(): RestaurantInput {
    return {
      name: '',
      description: '',
      address: '',
      phone: '',
      image_url: '',
      opening_time: '09:00',
      closing_time: '21:00',
      working_days: [0, 1, 2, 3, 4, 5, 6],
      is_active: true,
    };
  }

  private emptyMenuForm(): Omit<FoodItemInput, 'restaurant'> {
    return {
      name: '',
      description: '',
      category: '',
      price: 0,
      image_url: '',
      is_active: true,
    };
  }
}
