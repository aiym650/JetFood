import { ChangeDetectorRef, Component, DestroyRef, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Auth } from '../auth';
import { CartQuote, Orders } from '../orders';
import { CardPaymentInput, CardPaymentResult, Payments } from '../payments';
import { FoodItem, Menu } from '../menu';
import { Restaurant, Restaurants } from '../restaurants';
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
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.css',
})
export class Dashboard implements OnInit {
  promoDraft = '';
  appliedPromo = '';
  promoError = '';
  quoteLoading = false;
  cartQuote: CartQuote | null = null;
  private quoteVersion = 0;
  currentUser: any = null;
  role = '';
  cart: CartLine[] = [];
  cartOpen = false;
  searchTerm = '';
  minPrice: number | null = null;
  maxPrice: number | null = null;
  deliveryAddress = '';
  paymentMethod: 'online' | 'cash' = 'cash';
  cardNumber = '';
  cardExpiry = '';
  cardCvv = '';
  cardholderName = '';
  cardValidationAttempted = false;
  pendingPaymentOrderId: number | null = null;
  paymentError = '';
  paymentResult: CardPaymentResult | null = null;
  savedAddresses: DeliveryAddress[] = [];
  selectedAddressId: number | null = null;
  savedAddressError = '';
  checkoutError = '';
  checkoutSuccess = '';
  cartNotice = '';
  submittingOrder = false;
  restaurants: Restaurant[] = [];
  selectedRestaurant: Restaurant | null = null;
  restaurantsLoading = false;
  restaurantsError = '';
  foodItems: FoodItem[] = [];
  menuLoading = false;
  menuError = '';

  get categories(): string[] {
    return [
      this.i18n.t('allCategories'),
      ...new Set(this.selectedRestaurantItems.map(item => this.i18n.catalogLabel(item.category))),
    ];
  }
  selectedCategory = 'Все';

  constructor(
    private auth: Auth,
    private router: Router,
    private route: ActivatedRoute,
    private ordersService: Orders,
    private paymentsService: Payments,
    private menuService: Menu,
    private restaurantsService: Restaurants,
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

    this.loadRestaurants();
    this.loadMenu();
    this.loadSavedAddresses();
  }

  loadRestaurants(): void {
    this.restaurantsLoading = true;
    this.restaurantsError = '';
    this.restaurantsService.getRestaurants().subscribe({
      next: (restaurants) => {
        this.restaurants = restaurants;
        this.restaurantsLoading = false;
        this.changeDetector.markForCheck();
      },
      error: () => {
        this.restaurantsError = this.i18n.t('restaurantsLoadFailed');
        this.restaurantsLoading = false;
        this.changeDetector.markForCheck();
      },
    });
  }

  selectRestaurant(restaurant: Restaurant): void {
    this.selectedRestaurant = restaurant;
    this.selectedCategory = this.i18n.t('allCategories');
    this.searchTerm = '';
    this.minPrice = null;
    this.maxPrice = null;
  }

  backToRestaurants(): void {
    this.selectedRestaurant = null;
    this.selectedCategory = this.i18n.t('allCategories');
    this.searchTerm = '';
  }

  get filteredRestaurants(): Restaurant[] {
    const query = this.searchTerm.trim().toLocaleLowerCase('ru');
    return this.restaurants.filter(restaurant =>
      !query || [
        restaurant.name,
        this.i18n.catalogLabel(restaurant.name),
        restaurant.cuisine ?? "",
        restaurant.description,
        this.i18n.catalogLabel(restaurant.description),
        restaurant.address,
        this.i18n.catalogLabel(restaurant.address),
      ]
        .join(' ')
        .toLocaleLowerCase('ru')
        .includes(query),
    );
  }

  restaurantItemCount(restaurant: Restaurant): number {
    return this.foodItems.filter(item => item.restaurant === restaurant.id && item.is_active !== false).length;
  }

  private get selectedRestaurantItems(): FoodItem[] {
    return this.selectedRestaurant
      ? this.foodItems.filter(item => item.restaurant === this.selectedRestaurant?.id)
      : [];
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
    if (this.pendingPaymentOrderId !== null) {
      return;
    }
    if (value === 'online' || value === 'cash') {
      this.paymentMethod = value;
      this.paymentError = '';
      this.paymentResult = null;
      this.clearCardDetails();
    }
  }

  formatCardNumber(value: string): void {
    const digits = value.replace(/\D/g, '').slice(0, 16);
    this.cardNumber = (digits.match(/.{1,4}/g) ?? []).join(' ');
  }

  formatCardExpiry(value: string): void {
    const digits = value.replace(/\D/g, '').slice(0, 4);
    this.cardExpiry = digits.length > 2
      ? `${digits.slice(0, 2)}/${digits.slice(2)}`
      : digits;
  }

  formatCardCvv(value: string): void {
    this.cardCvv = value.replace(/\D/g, '').slice(0, 3);
  }

  formatCardholderName(value: string): void {
    this.cardholderName = value
      .toUpperCase()
      .replace(/[^A-Z\s-]/g, '')
      .replace(/\s{2,}/g, ' ')
      .slice(0, 120);
  }

  cardNumberError(): string {
    if (!this.cardValidationAttempted) return '';
    const digits = this.cardNumber.replace(/\s/g, '');
    return this.isLuhnValid(digits) ? '' : this.i18n.t('invalidCardNumber');
  }

  cardExpiryError(): string {
    if (!this.cardValidationAttempted) return '';
    if (!/^(0[1-9]|1[0-2])\/\d{2}$/.test(this.cardExpiry)) {
      return this.i18n.t('invalidCardExpiry');
    }
    const [monthText, yearText] = this.cardExpiry.split('/');
    const month = Number(monthText);
    const year = 2000 + Number(yearText);
    const now = new Date();
    return year < now.getFullYear() || (year === now.getFullYear() && month < now.getMonth() + 1)
      ? this.i18n.t('expiredCard')
      : '';
  }

  cardCvvError(): string {
    if (!this.cardValidationAttempted) return '';
    return /^\d{3}$/.test(this.cardCvv) ? '' : this.i18n.t('invalidCvv');
  }

  cardholderError(): string {
    if (!this.cardValidationAttempted) return '';
    return /^[A-Z]+(?:[ -][A-Z]+)*$/.test(this.cardholderName.trim())
      ? ''
      : this.i18n.t('cardholderRequired');
  }

  retryPayment(): void {
    this.paymentError = '';
    this.cardValidationAttempted = false;
    this.paymentResult = null;
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
        const requested = Number(this.route.snapshot.queryParamMap.get('addItem'));
        const dish = this.foodItems.find(item => item.id === requested);
        if (dish) {
          this.addToCart(dish);
          this.router.navigate([], { queryParams: { addItem: null }, queryParamsHandling: 'merge', replaceUrl: true });
        }
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
    return this.selectedRestaurantItems.filter(item => {
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
    if (item.is_active === false) return;
    if (this.submittingOrder || this.pendingPaymentOrderId !== null) {
      return;
    }

    if (this.cart.some(line => line.item.restaurant !== item.restaurant)) {
      if (!confirm(this.i18n.t('confirmReplaceCart'))) return;
      this.cart = [];
      this.appliedPromo = '';
      this.promoDraft = '';
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
    if (this.submittingOrder || this.pendingPaymentOrderId !== null) {
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
    if (this.submittingOrder || this.pendingPaymentOrderId !== null) {
      return;
    }

    this.cart = [];
    this.removePromo();
    sessionStorage.removeItem(`jetfood-checkout-${this.currentUser?.id}`);
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
    this.refreshQuote();
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
      if (!item || item.is_active === false) {
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

    if (this.paymentMethod === 'online') {
      this.cardValidationAttempted = true;
      if (
        this.cardNumberError()
        || this.cardExpiryError()
        || this.cardCvvError()
        || this.cardholderError()
      ) {
        return;
      }
    }

    this.checkoutError = '';
    this.checkoutSuccess = '';
    this.paymentError = '';
    this.paymentResult = null;

    if (this.pendingPaymentOrderId !== null) {
      this.submitCardPayment(this.pendingPaymentOrderId);
      return;
    }

    this.submittingOrder = true;
    const input = {
      delivery_address: this.deliveryAddress.trim(),
      payment_method: this.paymentMethod,
      promo_code: this.appliedPromo,
      items: this.cart.map(({ item, quantity }) => ({
        item_id: item.id,
        quantity,
      })),
    };
    const requestBody = JSON.stringify(input);
    const requestStorageKey = `jetfood-checkout-${this.currentUser.id}`;
    let saved: { body: string; key: string } | null = null;
    try { saved = JSON.parse(sessionStorage.getItem(requestStorageKey) ?? 'null'); } catch { /* Replace invalid state. */ }
    if (saved?.body !== requestBody) saved = { body: requestBody, key: crypto.randomUUID() };
    sessionStorage.setItem(requestStorageKey, JSON.stringify(saved));
    this.ordersService.createOrder(input, saved!.key).subscribe({
      next: (order) => {
        if (this.paymentMethod === 'online') {
          this.pendingPaymentOrderId = order.id;
          this.submitCardPayment(order.id);
          return;
        }
        this.submittingOrder = false;
        this.clearCart();
        this.deliveryAddress = '';
        this.checkoutSuccess = this.i18n.t('orderCreatedCash');
        this.changeDetector.markForCheck();
      },
      error: (error) => {
        this.checkoutError = this.orderError(error);
        this.submittingOrder = false;
        this.clearCardDetails();
        this.changeDetector.markForCheck();
      },
    });
  }

  private orderError(error: { status?: number; error?: any }): string {
    if (error.status === 0) return this.i18n.t('checkoutConnectionFailed');
    if (error.error?.promo_error) return this.promotionError(error);
    if (error.status === 401) return this.i18n.t('checkoutSessionExpired');
    if (error.status === 409) return this.i18n.t('checkoutRequestConflict');
    if (error.status === 429 || error.status === 503) return this.i18n.t('checkoutBusy');
    if (error.error && typeof error.error === 'object' && !Array.isArray(error.error)) {
      if (error.error.delivery_address) return this.i18n.t('missingDeliveryAddress');
      if (error.error.items) return this.i18n.t('checkoutItemsChanged');
    }
    // DRF may return a list for business validation. Show its actual explanation.
    if (error.status === 400) {
      const body = error.error;
      const raw = Array.isArray(body) ? body : body?.non_field_errors ?? body?.detail;
      const details = Array.isArray(raw) ? raw : [raw];
      const message = details.find((value: unknown) => typeof value === 'string' && value.trim());
      if (message) return message;
    }
    return this.i18n.t('orderCreateFailed');
  }

  applyPromo(): void {
    this.appliedPromo = this.promoDraft.trim().toUpperCase();
    this.promoDraft = this.appliedPromo;
    this.refreshQuote();
  }

  removePromo(): void {
    this.appliedPromo = '';
    this.promoDraft = '';
    this.refreshQuote();
  }

  private promotionError(error: any): string {
    const reason = error.error?.promo_error;
    const code = Array.isArray(reason) ? reason[0] : reason;
    return this.i18n.t(code ? `promoErrors.${code}` : 'quoteFailed');
  }

  refreshQuote(): void {
    const version = ++this.quoteVersion;
    this.cartQuote = null;
    this.promoError = '';
    this.quoteLoading = false;
    if (!this.cart.length) return;
    this.quoteLoading = true;
    this.ordersService.quote(this.cart.map(line => ({ item_id: line.item.id, quantity: line.quantity })), this.appliedPromo).subscribe({
      next: quote => {
        if (version !== this.quoteVersion) return;
        this.cartQuote = quote;
        this.quoteLoading = false;
        this.changeDetector.markForCheck();
      },
      error: error => {
        if (version !== this.quoteVersion) return;
        this.promoError = this.promotionError(error);
        this.quoteLoading = false;
        this.changeDetector.markForCheck();
      },
    });
  }

  private submitCardPayment(orderId: number): void {
    const card: CardPaymentInput = {
      card_number: this.cardNumber.replace(/\s/g, ''),
      expiry: this.cardExpiry,
      cvv: this.cardCvv,
      cardholder_name: this.cardholderName.trim(),
    };
    this.clearCardDetails();
    this.submittingOrder = true;
    this.paymentsService.payOrder(orderId, card).subscribe({
      next: (payment) => {
        this.paymentResult = payment;
        this.submittingOrder = false;
        if (payment.status === 'paid') {
          this.pendingPaymentOrderId = null;
          this.clearCart();
          this.deliveryAddress = '';
          this.checkoutSuccess = this.i18n.t('paymentApproved');
        } else {
          this.paymentError = this.translatePaymentMessage(payment.failure_reason || payment.message);
        }
        this.changeDetector.markForCheck();
      },
      error: (error: { error?: unknown }) => {
        this.paymentError = this.extractPaymentError(error.error);
        this.submittingOrder = false;
        this.changeDetector.markForCheck();
      },
    });
  }

  private clearCardDetails(): void {
    this.cardNumber = '';
    this.cardExpiry = '';
    this.cardCvv = '';
    this.cardholderName = '';
    this.cardValidationAttempted = false;
  }

  private isLuhnValid(cardNumber: string): boolean {
    if (!/^\d{16}$/.test(cardNumber)) return false;
    let sum = 0;
    let doubleDigit = false;
    for (let index = cardNumber.length - 1; index >= 0; index -= 1) {
      let digit = Number(cardNumber[index]);
      if (doubleDigit) {
        digit *= 2;
        if (digit > 9) digit -= 9;
      }
      sum += digit;
      doubleDigit = !doubleDigit;
    }
    return sum % 10 === 0;
  }

  private extractPaymentError(error: unknown): string {
    if (error && typeof error === 'object') {
      const values = Object.values(error as Record<string, unknown>).flat();
      const message = values.find(value => typeof value === 'string');
      if (typeof message === 'string') return this.translatePaymentMessage(message);
    }
    return this.i18n.t('cardPaymentFailed');
  }

  private translatePaymentMessage(message: string): string {
    const translations: Record<string, string> = {
      'Card declined': 'cardDeclined',
      'Card declined.': 'cardDeclined',
      'Insufficient funds': 'insufficientFunds',
      'Enter a valid card number.': 'invalidCardNumber',
      'Enter expiry as MM/YY.': 'invalidCardExpiry',
      'Card expiry must be in the future.': 'expiredCard',
      'Enter a 3 digit CVV.': 'invalidCvv',
      'Enter the cardholder name.': 'cardholderRequired',
    };
    const translationKey = translations[message];
    return translationKey ? this.i18n.t(translationKey) : message;
  }

  paymentCardLabel(brand: string | null, last4: string | null): string {
    if (!brand || !last4) return '';
    const label = brand === 'visa'
      ? 'Visa'
      : brand === 'mastercard'
        ? 'Mastercard'
        : this.i18n.t('otherCard');
    return `${label} **** ${last4}`;
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
