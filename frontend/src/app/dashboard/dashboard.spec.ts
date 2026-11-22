import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of, Subject, throwError } from 'rxjs';
import { vi } from 'vitest';

import { Dashboard } from './dashboard';
import { Auth } from '../auth';
import { OrderRecord, Orders } from '../orders';
import { CardPaymentResult, Payments } from '../payments';
import { Menu } from '../menu';
import { Restaurants } from '../restaurants';
import { Addresses } from '../addresses';
import { I18nService } from '../i18n/i18n.service';

describe('Dashboard', () => {
  let component: Dashboard;
  let fixture: ComponentFixture<Dashboard>;

  beforeEach(async () => {
    localStorage.removeItem('jetfood-cart-45');
    sessionStorage.removeItem('jetfood-checkout-45');
    const menuItems = [
      { id: 1, name: 'Пицца Маргарита', description: 'Томаты, моцарелла, базилик', price: 890, image_url: '', category: 'Пицца', rating: 4.8, restaurant: 1 },
      { id: 2, name: 'Бургер Классический', description: 'Говядина, сыр, овощи, соус', price: 650, image_url: '', category: 'Бургеры', rating: 4.7, restaurant: 2 },
      { id: 3, name: 'Рамен с курицей', description: 'Куриный бульон, лапша, яйцо', price: 750, image_url: '', category: 'Супы', rating: 4.9, restaurant: 3 },
    ];
    const restaurants = [
      { id: 1, name: 'North Kitchen', description: 'Local meals', address: 'Main Street 1', phone: '', image_url: '', opening_time: '09:00:00', closing_time: '21:00:00', working_days: [0, 1, 2, 3, 4, 5, 6], is_active: true },
      { id: 2, name: 'Grill House', description: 'Grilled food', address: 'Main Street 2', phone: '', image_url: '', opening_time: '10:00:00', closing_time: '22:00:00', working_days: [0, 1, 2, 3, 4, 5, 6], is_active: true },
      { id: 3, name: 'Asian Kitchen', description: 'Soups and sushi', address: 'Main Street 3', phone: '', image_url: '', opening_time: '11:00:00', closing_time: '23:00:00', working_days: [0, 1, 2, 3, 4, 5, 6], is_active: true },
    ];

    await TestBed.configureTestingModule({
      imports: [Dashboard],
      providers: [
        provideRouter([]),
        { provide: Auth, useValue: { getCurrentUser: () => ({ id: 45, username: 'test', role: 'customer' }), isLoggedIn: () => true } },
        { provide: Orders, useValue: { createOrder: () => of({}), quote: () => of({ items_amount: '890.00', discount_amount: '0.00', delivery_fee: '0.00', delivery_discount: '0.00', total_amount: '890.00', promo_code: '' }) } },
        { provide: Payments, useValue: { payOrder: () => of({}) } },
        { provide: Menu, useValue: { getItems: () => of(menuItems) } },
        { provide: Restaurants, useValue: { getRestaurants: () => of(restaurants) } },
        { provide: Addresses, useValue: { getAddresses: () => of([]) } },
      ],
    }).compileComponents();

    TestBed.inject(I18nService).setLanguage('ru');
    fixture = TestBed.createComponent(Dashboard);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('switches dashboard labels between English and Russian', () => {
    component.i18n.setLanguage('en');
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Restaurants');
    expect(fixture.nativeElement.textContent).toContain('North Kitchen');
    expect(fixture.nativeElement.textContent).not.toContain('Margherita Pizza');
    (fixture.nativeElement.querySelector('.restaurant-card') as HTMLButtonElement).click();
    fixture.detectChanges(false);
    expect(component.selectedRestaurant?.name).toBe('North Kitchen');
    expect(fixture.nativeElement.textContent).toContain('Margherita Pizza');
    expect(fixture.nativeElement.textContent).toContain('Pizza');

    component.i18n.setLanguage('ru');
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('К списку ресторанов');
  });

  it('filters menu items by category and search term', () => {
    component.selectRestaurant(component.restaurants[0]);
    component.selectCategory('Пицца');
    expect(component.filteredItems.map(item => item.name)).toEqual(['Пицца Маргарита']);

    component.selectRestaurant(component.restaurants[2]);
    component.selectCategory('Все');
    component.selectRestaurant(component.restaurants[2]);
    component.searchTerm = 'рамэн';
    expect(component.filteredItems).toEqual([]);
    component.searchTerm = 'рамен';
    expect(component.filteredItems.map(item => item.name)).toEqual(['Рамен с курицей']);
  });

  it('filters menu items by minimum and maximum price', () => {
    component.selectRestaurant(component.restaurants[2]);
    component.setPriceFilter('min', '700');
    component.setPriceFilter('max', '800');

    expect(component.filteredItems.map(item => item.name)).toEqual(['Рамен с курицей']);

    component.setPriceFilter('max', '600');
    expect(component.filteredItems).toEqual([]);
  });

  it('updates cart quantities and total', () => {
    const item = component.foodItems[0];
    component.addToCart(item);
    component.addToCart(item);

    expect(component.cartItemCount).toBe(2);
    expect(component.cartTotal).toBe(item.price * 2);

    component.changeQuantity(component.cart[0], -1);
    expect(component.cartItemCount).toBe(1);
    expect(component.cartTotal).toBe(item.price);
  });

  it('submits menu item identifiers without trusting client prices', () => {
    const createOrder = vi.spyOn(TestBed.inject(Orders), 'createOrder');
    const item = component.foodItems[0];
    component.addToCart(item);
    component.deliveryAddress = 'Test address';

    component.checkout();

    expect(createOrder).toHaveBeenCalledWith(expect.objectContaining({
      payment_method: 'cash',
      items: [{ item_id: item.id, quantity: 1 }],
    }), expect.any(String));
    expect(createOrder.mock.calls[0][0].items[0]).not.toHaveProperty('price_per_item');
    expect(createOrder.mock.calls[0][0].items[0]).not.toHaveProperty('item_name');
  });

  it('accepts only supported payment choices', () => {
    component.setPaymentMethod('online');
    expect(component.paymentMethod).toBe('online');
    component.setPaymentMethod('bank_transfer');
    expect(component.paymentMethod).toBe('online');
  });

  it('shows the payment confirmation action in the open online cart', () => {
    (fixture.nativeElement.querySelector('.restaurant-card') as HTMLButtonElement).click();
    fixture.detectChanges(false);
    (fixture.nativeElement.querySelector('.food-card .add-to-cart-btn') as HTMLButtonElement).click();
    fixture.detectChanges(false);
    const paymentSelect = fixture.nativeElement.querySelector('.cart-footer select') as HTMLSelectElement;
    paymentSelect.value = 'online';
    paymentSelect.dispatchEvent(new Event('change'));
    fixture.detectChanges(false);

    const checkoutButton = fixture.nativeElement.querySelector('.checkout-btn') as HTMLButtonElement;
    expect(checkoutButton.textContent).toContain(component.i18n.t('placeOrderAndPay'));
  });

  it('validates card details before creating an online order', () => {
    const createOrder = vi.spyOn(TestBed.inject(Orders), 'createOrder');
    component.formatCardNumber('4242424242424242');
    component.formatCardExpiry('1299');
    expect(component.cardNumber).toBe('4242 4242 4242 4242');
    expect(component.cardExpiry).toBe('12/99');

    component.addToCart(component.foodItems[0]);
    component.deliveryAddress = 'Test address';
    component.setPaymentMethod('online');
    component.cardNumber = '4242 4242 4242 4243';
    component.cardExpiry = '00/20';
    component.cardCvv = '12';
    component.cardholderName = '';

    component.checkout();

    expect(createOrder).not.toHaveBeenCalled();
    expect(component.cardNumberError()).toBe(component.i18n.t('invalidCardNumber'));
    expect(component.cardExpiryError()).toBe(component.i18n.t('invalidCardExpiry'));
    expect(component.cardCvvError()).toBe(component.i18n.t('invalidCvv'));
    expect(component.cardholderError()).toBe(component.i18n.t('cardholderRequired'));
  });

  it('shows a success receipt and clears card details after payment', () => {
    const createdOrder: OrderRecord = {
      id: 77,
      order_number: 'ORD-77',
      customer: 45,
      customer_name: 'test',
      delivery_person: null,
      delivery_person_name: null,
      status: 'pending',
      priority: 'normal',
      total_amount: 890,
      delivery_address: 'Test address',
      delivery_notes: '',
      estimated_delivery_time: null,
      delivery_started_at: null,
      estimated_arrival_time: null,
      actual_delivery_time: null,
      delivery_confirmed_at: null,
      created_at: '',
      updated_at: '',
      items: [],
    };
    const paidPayment: CardPaymentResult = {
      id: 1,
      order: 77,
      order_number: 'ORD-77',
      order_status: 'confirmed',
      customer_name: 'test',
      method: 'online',
      status: 'paid',
      amount: '890.00',
      transaction_id: 'SIM-ABC123',
      card_brand: 'visa',
      card_last4: '4242',
      failure_reason: '',
      refund_reason: '',
      created_at: '',
      paid_at: '2026-11-18T10:00:00Z',
      refunded_at: null,
      message: 'Payment approved.',
    };
    const createOrder = vi.spyOn(TestBed.inject(Orders), 'createOrder')
      .mockReturnValue(of(createdOrder));
    const payOrder = vi.spyOn(TestBed.inject(Payments), 'payOrder')
      .mockReturnValue(of(paidPayment));
    component.addToCart(component.foodItems[0]);
    component.deliveryAddress = 'Test address';
    component.setPaymentMethod('online');
    component.cardNumber = '4242 4242 4242 4242';
    component.cardExpiry = '12/99';
    component.cardCvv = '123';
    component.cardholderName = 'TEST CUSTOMER';

    component.checkout();
    fixture.detectChanges();

    expect(createOrder).toHaveBeenCalledOnce();
    expect(payOrder).toHaveBeenCalledWith(77, {
      card_number: '4242424242424242',
      expiry: '12/99',
      cvv: '123',
      cardholder_name: 'TEST CUSTOMER',
    });
    expect(component.cardNumber).toBe('');
    expect(component.cardExpiry).toBe('');
    expect(component.cardCvv).toBe('');
    expect(component.cardholderName).toBe('');
    expect(component.paymentResult?.status).toBe('paid');
    expect(fixture.nativeElement.textContent).toContain('Visa **** 4242');
  });

  it('retries a declined payment on the same order', () => {
    const createdOrder: OrderRecord = {
      id: 78,
      order_number: 'ORD-78',
      customer: 45,
      customer_name: 'test',
      delivery_person: null,
      delivery_person_name: null,
      status: 'pending',
      priority: 'normal',
      total_amount: 890,
      delivery_address: 'Test address',
      delivery_notes: '',
      estimated_delivery_time: null,
      delivery_started_at: null,
      estimated_arrival_time: null,
      actual_delivery_time: null,
      delivery_confirmed_at: null,
      created_at: '',
      updated_at: '',
      items: [],
    };
    const failedPayment: CardPaymentResult = {
      id: 1,
      order: 78,
      order_number: 'ORD-78',
      order_status: 'pending',
      customer_name: 'test',
      method: 'online',
      status: 'failed',
      amount: '890.00',
      transaction_id: '',
      card_brand: 'visa',
      card_last4: '0002',
      failure_reason: 'Card declined',
      refund_reason: '',
      created_at: '',
      paid_at: null,
      refunded_at: null,
      message: 'Card declined',
    };
    const paidPayment: CardPaymentResult = {
      ...failedPayment,
      status: 'paid',
      order_status: 'confirmed',
      transaction_id: 'SIM-ABC123',
      card_last4: '4242',
      failure_reason: '',
      paid_at: '2026-11-18T10:00:00Z',
      message: 'Payment approved.',
    };
    const createOrder = vi.spyOn(TestBed.inject(Orders), 'createOrder')
      .mockReturnValue(of(createdOrder));
    const payOrder = vi.spyOn(TestBed.inject(Payments), 'payOrder')
      .mockReturnValueOnce(of(failedPayment))
      .mockReturnValueOnce(of(paidPayment));
    component.addToCart(component.foodItems[0]);
    component.deliveryAddress = 'Test address';
    component.setPaymentMethod('online');
    component.cardNumber = '4000 0000 0000 0002';
    component.cardExpiry = '12/99';
    component.cardCvv = '123';
    component.cardholderName = 'TEST CUSTOMER';

    component.checkout();
    expect(component.paymentError).toBe(component.i18n.t('cardDeclined'));
    expect(component.cardNumber).toBe('');
    expect(component.pendingPaymentOrderId).toBe(78);

    component.retryPayment();
    component.cardNumber = '4242 4242 4242 4242';
    component.cardExpiry = '12/99';
    component.cardCvv = '123';
    component.cardholderName = 'TEST CUSTOMER';
    component.checkout();

    expect(createOrder).toHaveBeenCalledOnce();
    expect(payOrder).toHaveBeenCalledTimes(2);
    expect(component.paymentResult?.status).toBe('paid');
    expect(component.pendingPaymentOrderId).toBeNull();
  });

  it('uses the saved default address for checkout', () => {
    vi.spyOn(TestBed.inject(Addresses), 'getAddresses').mockReturnValue(of([{
      id: 8,
      label: 'Home',
      recipient_name: '',
      phone: '',
      address_line: '1 Main Street',
      city: 'Astana',
      postal_code: '010000',
      instructions: '',
      is_default: true,
    }]));

    component.loadSavedAddresses();

    expect(component.selectedAddressId).toBe(8);
    expect(component.deliveryAddress).toBe('1 Main Street, Astana, 010000');
  });

  it('restores the cart from item IDs using current catalog prices', () => {
    component.addToCart(component.foodItems[0]);
    component.addToCart(component.foodItems[0]);
    component.cart = [];

    component.loadMenu();

    expect(component.cartItemCount).toBe(2);
    expect(component.cart[0].item.price).toBe(890);
    expect(JSON.parse(localStorage.getItem('jetfood-cart-45') ?? '[]')).toEqual([
      { itemId: 1, quantity: 2 },
    ]);
  });

  it('removes unavailable menu items from a restored cart', () => {
    localStorage.setItem('jetfood-cart-45', JSON.stringify([{ itemId: 999, quantity: 1 }]));

    component.loadMenu();

    expect(component.cart).toEqual([]);
    expect(component.cartNotice).toContain('Некоторые блюда больше недоступны');
    expect(localStorage.getItem('jetfood-cart-45')).toBe('[]');
  });

  it('does not allow more than 50 items in the cart', () => {
    const item = component.foodItems[0];
    for (let count = 0; count < 50; count += 1) {
      component.addToCart(item);
    }

    component.addToCart(item);

    expect(component.cartItemCount).toBe(50);
    expect(component.checkoutError).toContain('не более 50');
  });

  it('locks the cart while checkout is in flight and clears it after success', () => {
    const pendingOrder = new Subject<OrderRecord>();
    const orders = TestBed.inject(Orders);
    const createOrder = vi.spyOn(orders, 'createOrder').mockReturnValue(pendingOrder.asObservable());
    const item = component.foodItems[0];
    component.addToCart(item);
    component.deliveryAddress = 'Test address';

    component.checkout();
    component.addToCart(component.foodItems[1]);
    component.clearCart();

    expect(createOrder).toHaveBeenCalledOnce();
    expect(component.cartItemCount).toBe(1);
    expect(component.submittingOrder).toBe(true);

    pendingOrder.next({
      id: 1,
      order_number: 'ORD-TEST-001',
      customer: 45,
      customer_name: 'test',
      delivery_person: null,
      delivery_person_name: null,
      status: 'pending',
      priority: 'normal',
      total_amount: 890,
      delivery_address: 'Test address',
      delivery_notes: '',
      estimated_delivery_time: null,
      delivery_started_at: null,
      estimated_arrival_time: null,
      actual_delivery_time: null,
      delivery_confirmed_at: null,
      created_at: '',
      updated_at: '',
      items: [],
    });

    expect(component.cart).toEqual([]);
    expect(component.submittingOrder).toBe(false);
    expect(localStorage.getItem('jetfood-cart-45')).toBeNull();
  });
  it('requires confirmation before replacing a restaurant cart', () => {
    component.addToCart(component.foodItems[0]);
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false);
    component.addToCart(component.foodItems[1]);
    expect(component.cart[0].item.id).toBe(1);
    confirm.mockReturnValue(true);
    component.addToCart(component.foodItems[1]);
    expect(component.cart).toHaveLength(1);
    expect(component.cart[0].item.id).toBe(2);
    confirm.mockRestore();
  });

  it('recalculates the applied code after quantity changes and ignores stale quotes', () => {
    const first = new Subject<any>();
    const second = new Subject<any>();
    const quote = vi.spyOn(TestBed.inject(Orders), 'quote').mockReturnValueOnce(first).mockReturnValueOnce(second);
    component.appliedPromo = 'SAVE';
    component.addToCart(component.foodItems[0]);
    component.changeQuantity(component.cart[0], 1);
    expect(quote).toHaveBeenLastCalledWith([{ item_id: 1, quantity: 2 }], 'SAVE');
    second.next({ total_amount: '1602.00' });
    first.next({ total_amount: '801.00' });
    expect(component.cartQuote?.total_amount).toBe('1602.00');
  });

  it('explains a blocked connection and reuses the checkout key on retry', () => {
    const create = vi.spyOn(TestBed.inject(Orders), 'createOrder')
      .mockReturnValue(throwError(() => ({ status: 0 })));
    component.addToCart(component.foodItems[0]);
    component.deliveryAddress = 'Test address';
    component.checkout();
    expect(component.checkoutError).toBe(component.i18n.t('checkoutConnectionFailed'));
    expect(component.cartItemCount).toBe(1);
    expect(component.submittingOrder).toBe(false);
    component.checkout();
    expect(create.mock.calls[1][1]).toBe(create.mock.calls[0][1]);
  });

  it('shows the server explanation for a rejected order instead of a generic failure', () => {
    vi.spyOn(TestBed.inject(Orders), 'createOrder').mockReturnValue(throwError(() => ({
      status: 400, error: ['You have reached the maximum of 5 pending orders'],
    })));
    component.addToCart(component.foodItems[0]);
    component.deliveryAddress = 'Test address';
    component.checkout();
    expect(component.checkoutError).toBe('You have reached the maximum of 5 pending orders');
    expect(component.cartItemCount).toBe(1);
  });

});
