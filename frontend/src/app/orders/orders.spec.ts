import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of } from 'rxjs';
import { vi } from 'vitest';

import { OrdersPage } from './orders';
import { OrderRecord, Orders } from '../orders';
import { Auth } from '../auth';
import { I18nService } from '../i18n/i18n.service';
import { Menu } from '../menu';

describe('OrdersPage', () => {
  const makeOrder = (id: number, status: string): OrderRecord => ({
    id,
    order_number: `ORD-${id}`,
    customer: 1,
    customer_name: 'test',
    delivery_person: null,
    delivery_person_name: null,
    status,
    priority: 'normal',
    total_amount: 0,
    delivery_address: '',
    delivery_notes: '',
    estimated_delivery_time: null,
    actual_delivery_time: null,
    delivery_confirmed_at: null,
    created_at: '',
    updated_at: '',
    items: [],
  });

  let component: OrdersPage;
  let fixture: ComponentFixture<OrdersPage>;
  let ordersService: {
    getOrders: ReturnType<typeof vi.fn>;
    updateOrderStatus: ReturnType<typeof vi.fn>;
    modifyOrder: ReturnType<typeof vi.fn>;
    getDeliveryRoute: ReturnType<typeof vi.fn>;
    saveDeliveryRoute: ReturnType<typeof vi.fn>;
    confirmDelivery: ReturnType<typeof vi.fn>;
  };

  beforeEach(async () => {
    ordersService = {
      getOrders: vi.fn().mockReturnValue(of([])),
      updateOrderStatus: vi.fn().mockReturnValue(of({})),
      modifyOrder: vi.fn(),
      getDeliveryRoute: vi.fn().mockReturnValue(of(null)),
      saveDeliveryRoute: vi.fn(),
      confirmDelivery: vi.fn(),
    };

    await TestBed.configureTestingModule({
      imports: [OrdersPage],
      providers: [
        provideRouter([]),
        { provide: Orders, useValue: ordersService },
        { provide: Menu, useValue: { getItems: () => of([]) } },
        { provide: Auth, useValue: { getCurrentUser: () => ({ username: 'test', role: 'customer' }), isLoggedIn: () => true } },
      ],
    }).compileComponents();

    TestBed.inject(I18nService).setLanguage('ru');
    fixture = TestBed.createComponent(OrdersPage);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('shows translated order statuses', () => {
    expect(component.statusLabel('pending')).toBe('Ожидает подтверждения');
    expect(component.statusLabel('delivered')).toBe('Доставлен');
  });

  it('toggles expanded order details', () => {
    component.toggleOrderDetails(12);
    expect(component.expandedOrderId).toBe(12);

    component.toggleOrderDetails(12);
    expect(component.expandedOrderId).toBeNull();
  });

  it('refreshes order statuses without entering the initial loading state', () => {
    component.orders = [makeOrder(12, 'pending')];
    ordersService.getOrders.mockReturnValueOnce(of([makeOrder(12, 'delivering')]));

    component.refreshOrders();

    expect(component.orders[0].status).toBe('delivering');
    expect(component.loading).toBe(false);
    expect(component.refreshing).toBe(false);
    expect(component.hasActiveOrders).toBe(true);
  });

  it('stops polling when all orders are complete', () => {
    component.orders = [
      makeOrder(12, 'delivered'),
      makeOrder(13, 'cancelled'),
    ];

    expect(component.hasActiveOrders).toBe(false);
  });

  it('confirms receipt and records the confirmation time', () => {
    const order = makeOrder(24, 'delivered');
    component.orders = [order];
    ordersService.confirmDelivery.mockReturnValueOnce(of({
      message: 'Delivery confirmed.',
      delivery_confirmed_at: '2025-01-01T10:00:00Z',
    }));

    component.confirmDelivery(order);

    expect(ordersService.confirmDelivery).toHaveBeenCalledWith(order.id);
    expect(component.orders[0].delivery_confirmed_at).toBe('2025-01-01T10:00:00Z');
  });

  it('loads the route when order details are expanded', () => {
    component.toggleOrderDetails(31);

    expect(ordersService.getDeliveryRoute).toHaveBeenCalledWith(31);
    expect(component.deliveryRoutes[31]).toBeNull();
  });

  it('cancels a pending order and reloads the list', () => {
    component.cancelOrder(12);

    expect(ordersService.updateOrderStatus).toHaveBeenCalledWith(12, 'cancelled');
    expect(ordersService.getOrders).toHaveBeenCalledTimes(2);
    expect(component.cancellingOrderId).toBeNull();
  });

  it('prepares an editable pending order and saves its changes', () => {
    const order = {
      ...makeOrder(19, 'pending'),
      delivery_address: 'Old address',
      delivery_notes: 'Old note',
      items: [{
        id: 2,
        menu_item_id: 7,
        item_name: 'Burger',
        quantity: 1,
        price_per_item: 15,
        subtotal: 15,
      }],
    };
    component.orders = [order];
    component.beginEditOrder(order);
    ordersService.modifyOrder.mockReturnValueOnce(of({
      ...order,
      delivery_address: 'New address',
      delivery_notes: 'New note',
    }));
    component.editAddress = 'New address';
    component.editNotes = 'New note';
    component.changeEditQuantity(0, 1);

    component.saveOrderEdit(order.id);

    expect(ordersService.modifyOrder).toHaveBeenCalledWith(order.id, {
      delivery_address: 'New address',
      delivery_notes: 'New note',
      items: [{ item_id: 7, quantity: 2 }],
    });
    expect(component.orders[0].delivery_address).toBe('New address');
    expect(component.editingOrderId).toBeNull();
  });
});
