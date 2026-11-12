import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of, Subject } from 'rxjs';
import { vi } from 'vitest';

import { Dashboard } from './dashboard';
import { Auth } from '../auth';
import { OrderRecord, Orders } from '../orders';
import { Menu } from '../menu';
import { Addresses } from '../addresses';
import { I18nService } from '../i18n/i18n.service';

describe('Dashboard', () => {
  let component: Dashboard;
  let fixture: ComponentFixture<Dashboard>;

  beforeEach(async () => {
    localStorage.removeItem('jetfood-cart-45');
    const menuItems = [
      { id: 1, name: 'Пицца Маргарита', description: 'Томаты, моцарелла, базилик', price: 890, image_url: '', category: 'Пицца', rating: 4.8 },
      { id: 2, name: 'Бургер Классический', description: 'Говядина, сыр, овощи, соус', price: 650, image_url: '', category: 'Бургеры', rating: 4.7 },
      { id: 3, name: 'Рамен с курицей', description: 'Куриный бульон, лапша, яйцо', price: 750, image_url: '', category: 'Супы', rating: 4.9 },
    ];

    await TestBed.configureTestingModule({
      imports: [Dashboard],
      providers: [
        provideRouter([]),
        { provide: Auth, useValue: { getCurrentUser: () => ({ id: 45, username: 'test', role: 'customer' }), isLoggedIn: () => true } },
        { provide: Orders, useValue: { createOrder: () => of({}) } },
        { provide: Menu, useValue: { getItems: () => of(menuItems) } },
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
    expect(fixture.nativeElement.textContent).toContain('What would you like to order?');
    expect(fixture.nativeElement.textContent).toContain('Margherita Pizza');
    expect(fixture.nativeElement.textContent).toContain('Pizza');

    component.i18n.setLanguage('ru');
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Что будем заказывать?');
  });

  it('filters menu items by category and search term', () => {
    component.selectCategory('Пицца');
    expect(component.filteredItems.map(item => item.name)).toEqual(['Пицца Маргарита']);

    component.selectCategory('Все');
    component.searchTerm = 'рамэн';
    expect(component.filteredItems).toEqual([]);
    component.searchTerm = 'рамен';
    expect(component.filteredItems.map(item => item.name)).toEqual(['Рамен с курицей']);
  });

  it('filters menu items by minimum and maximum price', () => {
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
    }));
    expect(createOrder.mock.calls[0][0].items[0]).not.toHaveProperty('price_per_item');
    expect(createOrder.mock.calls[0][0].items[0]).not.toHaveProperty('item_name');
  });

  it('accepts only supported payment choices', () => {
    component.setPaymentMethod('online');
    expect(component.paymentMethod).toBe('online');
    component.setPaymentMethod('bank_transfer');
    expect(component.paymentMethod).toBe('online');
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
});
