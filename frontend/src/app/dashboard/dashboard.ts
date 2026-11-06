import { ChangeDetectorRef, Component, DestroyRef, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Auth } from '../auth';
import { Orders } from '../orders';
import { FoodItem, Menu } from '../menu';
import { I18nService } from '../i18n/i18n.service';
import { Addresses, DeliveryAddress } from '../addresses';

interface CartLine {
  item: FoodItem;
  quantity: number;
}

interface StoredCartLine {
  itemId: number;
  quantity: number;
}

@Component({
  selector: 'app-dashboard',
  imports: [CommonModule, RouterModule],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.css',
})
export class Dashboard implements OnInit {
  currentUser: any = null;
  role = '';
  cart: CartLine[] = [];
  cartOpen = false;
  searchTerm = '';
  minPrice: number | null = null;
  maxPrice: number | null = null;
  deliveryAddress = '';
  paymentMethod: 'online' | 'cash' = 'cash';
  savedAddresses: DeliveryAddress[] = [];
  selectedAddressId: number | null = null;
  savedAddressError = '';
  checkoutError = '';
  checkoutSuccess = '';
  cartNotice = '';
  submittingOrder = false;
  foodItems: FoodItem[] = [];
  menuLoading = false;
  menuError = '';

  get categories(): string[] {
    return [
      this.i18n.t('allCategories'),
      ...new Set(this.foodItems.map(item => this.i18n.catalogLabel(item.category))),
    ];
  }
  selectedCategory = 'Все';

  constructor(
    private auth: Auth,
    private router: Router,
    private route: ActivatedRoute,
    private ordersService: Orders,
    private menuService: Menu,
    private addressesService: Addresses,
    private changeDetector: ChangeDetectorRef,
    private destroyRef: DestroyRef,
    public i18n: I18nService
  ) {
    this.i18n.currentLang$
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => this.changeDetector.markForCheck());
  }

  ngOnInit(): void {
    this.currentUser = this.auth.getCurrentUser();
    this.role = this.currentUser?.role || '';
    this.route.queryParamMap
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((params) => {
        this.searchTerm = params.get('search') ?? '';
        this.changeDetector.markForCheck();
      });

    if (!this.auth.isLoggedIn()) {
      this.router.navigate(['/landing']);
      return;
    }

    this.loadMenu();
    this.loadSavedAddresses();
  }

  loadSavedAddresses(): void {
    this.addressesService.getAddresses().subscribe({
      next: (addresses) => {
        this.savedAddresses = addresses;
        const defaultAddress = addresses.find(address => address.is_default);
        if (defaultAddress && !this.deliveryAddress) {
          this.selectSavedAddress(String(defaultAddress.id));
        }
        this.changeDetector.markForCheck();
      },
      error: () => {
        this.savedAddressError = this.i18n.t('addressesLoadFailed');
        this.changeDetector.markForCheck();
      },
    });
  }

  selectSavedAddress(value: string): void {
    this.selectedAddressId = value ? Number(value) : null;
    const address = this.savedAddresses.find(item => item.id === this.selectedAddressId);
    if (address) {
      this.deliveryAddress = [address.address_line, address.city, address.postal_code]
        .filter(Boolean)
        .join(', ');
    }
  }

  setPaymentMethod(value: string): void {
    if (value === 'online' || value === 'cash') {
      this.paymentMethod = value;
    }
  }

  loadMenu(): void {
    this.menuLoading = true;
    this.menuError = '';
    this.menuService.getItems().subscribe({
      next: (items) => {
        this.foodItems = items.map(item => ({
          ...item,
          price: Number(item.price),
        }));
        this.restoreCart(this.foodItems);
        this.menuLoading = false;
        this.changeDetector.markForCheck();
      },
      error: () => {
        this.menuError = this.i18n.t('menuLoadFailed');
        this.menuLoading = false;
        this.changeDetector.markForCheck();
      },
    });
  }

  logout(): void {
    this.auth.logout();
    this.router.navigate(['/landing']);
  }

  selectCategory(category: string): void {
    this.selectedCategory = category;
  }

  setPriceFilter(bound: 'min' | 'max', value: string): void {
    const parsed = value.trim() === '' ? null : Number(value);
    const price = parsed !== null && Number.isFinite(parsed) && parsed >= 0 ? parsed : null;
    if (bound === 'min') this.minPrice = price;
    else this.maxPrice = price;
  }

  categoryLabel(category: string): string {
    return this.i18n.catalogLabel(category);
  }

  itemName(item: FoodItem): string {
    return this.i18n.catalogLabel(item.name);
  }

  itemDescription(item: FoodItem): string {
    return this.i18n.catalogLabel(item.description);
  }

  get allCategoriesSelected(): boolean {
    return this.selectedCategory === 'Все' || this.selectedCategory === this.i18n.t('allCategories');
  }

  get filteredItems(): FoodItem[] {
    const query = this.searchTerm.trim().toLocaleLowerCase('ru');
    return this.foodItems.filter(item => {
      const matchesCategory = this.allCategoriesSelected || this.categoryLabel(item.category) === this.selectedCategory;
      const searchableText = [
        item.name,
        this.itemName(item),
        item.description,
        this.itemDescription(item),
        item.category,
        this.categoryLabel(item.category),
      ].join(' ');
      const matchesSearch = !query || searchableText
        .toLocaleLowerCase('ru')
        .includes(query);
      const matchesMinPrice = this.minPrice === null || item.price >= this.minPrice;
      const matchesMaxPrice = this.maxPrice === null || item.price <= this.maxPrice;
      return matchesCategory && matchesSearch && matchesMinPrice && matchesMaxPrice;
    });
  }

  addToCart(item: FoodItem): void {
    if (this.submittingOrder) {
      return;
    }

    if (this.cartItemCount >= 50) {
      this.checkoutError = this.i18n.t('maxOrderItems');
      return;
    }

    const line = this.cart.find(entry => entry.item.id === item.id);
    if (line) {
      line.quantity += 1;
    } else {
      this.cart.push({ item, quantity: 1 });
    }
    this.cartOpen = true;
    this.checkoutError = '';
    this.checkoutSuccess = '';
    this.saveCart();
  }

  changeQuantity(line: CartLine, change: number): void {
    if (this.submittingOrder) {
      return;
    }

    if (change > 0 && this.cartItemCount >= 50) {
      this.checkoutError = this.i18n.t('maxOrderItems');
      return;
    }

    line.quantity += change;
    if (line.quantity < 1) {
      this.cart = this.cart.filter(entry => entry !== line);
    }
    this.checkoutError = '';
    this.saveCart();
  }

  get cartItemCount(): number {
    return this.cart.reduce((count, line) => count + line.quantity, 0);
  }

  get cartTotal(): number {
    return this.cart.reduce((total, line) => total + line.item.price * line.quantity, 0);
  }

  clearCart(): void {
    if (this.submittingOrder) {
      return;
    }

    this.cart = [];
    this.cartOpen = false;
    this.checkoutError = '';
    this.cartNotice = '';
    const storageKey = this.cartStorageKey();
    if (storageKey) {
      localStorage.removeItem(storageKey);
    }
  }

  private cartStorageKey(): string | null {
    const userId = this.currentUser?.id;
    return Number.isSafeInteger(userId) && userId > 0 ? `jetfood-cart-${userId}` : null;
  }

  private saveCart(): void {
    const storageKey = this.cartStorageKey();
    if (storageKey) {
      const storedCart: StoredCartLine[] = this.cart.map(({ item, quantity }) => ({
        itemId: item.id,
        quantity,
      }));
      localStorage.setItem(storageKey, JSON.stringify(storedCart));
    }
  }

  private restoreCart(items: FoodItem[]): void {
    const storageKey = this.cartStorageKey();
    this.cartNotice = '';
    if (!storageKey) {
      return;
    }

    const rawCart = localStorage.getItem(storageKey);
    if (!rawCart) {
      return;
    }

    let storedCart: unknown;
    try {
      storedCart = JSON.parse(rawCart);
    } catch (error) {
      console.warn('Unable to restore the saved JetFood cart:', error);
      localStorage.removeItem(storageKey);
      this.cartNotice = this.i18n.t('cartRestoreError');
      return;
    }

    if (!Array.isArray(storedCart) || !storedCart.every(this.isStoredCartLine)) {
      localStorage.removeItem(storageKey);
      this.cartNotice = this.i18n.t('cartInvalid');
      return;
    }

    let unavailableItem = false;
    let totalQuantity = 0;
    this.cart = storedCart.reduce<CartLine[]>((restored, line) => {
      const item = items.find(menuItem => menuItem.id === line.itemId);
      if (!item) {
        unavailableItem = true;
        return restored;
      }

      const quantity = Math.min(line.quantity, 50 - totalQuantity);
      if (quantity < line.quantity) {
        unavailableItem = true;
      }
      if (quantity > 0) {
        restored.push({ item, quantity });
        totalQuantity += quantity;
      }
      return restored;
    }, []);

    if (unavailableItem) {
      this.cartNotice = this.i18n.t('cartUnavailable');
    }
    this.cartOpen = this.cart.length > 0;
    this.saveCart();
  }

  private isStoredCartLine(value: unknown): value is StoredCartLine {
    if (!value || typeof value !== 'object') {
      return false;
    }
    const line = value as Record<string, unknown>;
    return typeof line['itemId'] === 'number'
      && Number.isSafeInteger(line['itemId'])
      && line['itemId'] > 0
      && typeof line['quantity'] === 'number'
      && Number.isSafeInteger(line['quantity'])
      && line['quantity'] > 0;
  }

  checkout(): void {
    if (this.submittingOrder) {
      return;
    }

    if (!this.cart.length || !this.deliveryAddress.trim()) {
      this.checkoutError = this.i18n.t('missingDeliveryAddress');
      return;
    }

    this.checkoutError = '';
    this.checkoutSuccess = '';
    this.submittingOrder = true;
    this.ordersService.createOrder({
      delivery_address: this.deliveryAddress.trim(),
      payment_method: this.paymentMethod,
      items: this.cart.map(({ item, quantity }) => ({
        item_id: item.id,
        quantity,
      })),
    }).subscribe({
      next: () => {
        this.submittingOrder = false;
        this.clearCart();
        this.deliveryAddress = '';
        this.checkoutSuccess = this.i18n.t(
          this.paymentMethod === 'online' ? 'orderCreatedOnline' : 'orderCreatedCash'
        );
        this.changeDetector.markForCheck();
      },
      error: () => {
        this.checkoutError = this.i18n.t('orderCreateFailed');
        this.submittingOrder = false;
        this.changeDetector.markForCheck();
      },
    });
  }

  hasAccess(feature: string): boolean {
    const role = this.role;
    const permissions: any = {
      'orders': ['admin', 'manager', 'delivery', 'customer'],
      'analytics': ['admin', 'manager', 'analyst'],
      'reports': ['admin', 'manager', 'analyst'],
      'integration': ['admin', 'manager'],
      'users': ['admin', 'manager']
    };
    return permissions[feature]?.includes(role) || false;
  }
}
