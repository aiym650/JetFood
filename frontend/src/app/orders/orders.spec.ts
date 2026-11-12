import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpErrorResponse } from '@angular/common/http';
import { provideRouter } from '@angular/router';
import { BehaviorSubject, of, throwError } from 'rxjs';
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
    delivery_started_at: null,
    estimated_arrival_time: null,
    actual_delivery_time: null,
    delivery_confirmed_at: null,
    created_at: '',
    updated_at: '',
    items: [],
  });

  let component: OrdersPage;
  let fixture: ComponentFixture<OrdersPage>;
  let authUserSubject: BehaviorSubject<{ id: number; username: string; role: string } | null>;
  let ordersService: {
    getOrders: ReturnType<typeof vi.fn>;
    updateOrderStatus: ReturnType<typeof vi.fn>;
    modifyOrder: ReturnType<typeof vi.fn>;
    getDeliveryRoute: ReturnType<typeof vi.fn>;
    saveDeliveryRoute: ReturnType<typeof vi.fn>;
    confirmDelivery: ReturnType<typeof vi.fn>;
    getDeliveryCouriers: ReturnType<typeof vi.fn>;
    assignDeliveryPerson: ReturnType<typeof vi.fn>;
  };

  beforeEach(async () => {
    authUserSubject = new BehaviorSubject<{ id: number; username: string; role: string } | null>({
      id: 1,
      username: 'test',
      role: 'customer',
    });
    ordersService = {
      getOrders: vi.fn().mockReturnValue(of([])),
      updateOrderStatus: vi.fn().mockReturnValue(of({})),
      modifyOrder: vi.fn(),
      getDeliveryRoute: vi.fn().mockReturnValue(of(null)),
      saveDeliveryRoute: vi.fn(),
      confirmDelivery: vi.fn(),
      getDeliveryCouriers: vi.fn().mockReturnValue(of([])),
      assignDeliveryPerson: vi.fn().mockReturnValue(of({})),
    };

    await TestBed.configureTestingModule({
      imports: [OrdersPage],
      providers: [
        provideRouter([]),
        { provide: Orders, useValue: ordersService },
        { provide: Menu, useValue: { getItems: () => of([]) } },
        { provide: Auth, useValue: {
          getCurrentUser: () => authUserSubject.value,
          currentUser$: authUserSubject.asObservable(),
          refreshCurrentUser: () => of(authUserSubject.value),
          isLoggedIn: () => true,
        } },
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

  it('verifies the logged-in user before loading manager order actions', () => {
    expect(ordersService.getOrders).toHaveBeenCalledTimes(1);
    expect(component.currentUser?.role).toBe('customer');
    expect(component.canManageOrderFlow()).toBe(false);
  });

  it('updates order permissions when the signed-in account changes in another tab', () => {
    authUserSubject.next({ id: 7, username: 'demo_manager', role: 'manager' });

    expect(component.currentUser?.username).toBe('demo_manager');
    expect(component.canManageOrderFlow()).toBe(true);
    expect(ordersService.getOrders).toHaveBeenCalledTimes(2);
  });

  it('shows translated order statuses', () => {
    expect(component.statusLabel('pending')).toBe('Ожидает подтверждения ресторана');
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

  it('requires both map points before saving a delivery route', () => {
    component.routeOriginAddress = 'Restaurant address';

    component.saveDeliveryRoute(32);

    expect(component.routeSaveError).toBe('Отметьте на карте точки A и B.');
    expect(ordersService.saveDeliveryRoute).not.toHaveBeenCalled();
  });

  it('saves route addresses and both selected map points', () => {
    const savedRoute = {
      id: 4,
      order: 33,
      origin_address: 'Restaurant address',
      destination_address: 'Customer address',
      origin_latitude: 43.2389,
      origin_longitude: 76.8897,
      destination_latitude: 43.2511,
      destination_longitude: 76.9142,
      route_distance_meters: 4200,
      estimated_duration_seconds: 420,
      notes: '',
      directions_url: 'https://www.openstreetmap.org/directions',
      updated_by: 2,
      updated_by_name: 'courier',
      updated_at: '',
    };
    component.routeOriginAddress = ' Restaurant address ';
    component.routeCoordinates = {
      origin_latitude: 43.2389,
      origin_longitude: 76.8897,
      destination_latitude: 43.2511,
      destination_longitude: 76.9142,
    };
    component.routeMetrics = {
      route_distance_meters: 4200,
      estimated_duration_seconds: 420,
    };
    ordersService.saveDeliveryRoute.mockReturnValueOnce(of(savedRoute));

    component.saveDeliveryRoute(33);

    expect(ordersService.saveDeliveryRoute).toHaveBeenCalledWith(33, {
      origin_address: 'Restaurant address',
      notes: '',
      origin_latitude: 43.2389,
      origin_longitude: 76.8897,
      destination_latitude: 43.2511,
      destination_longitude: 76.9142,
      route_distance_meters: 4200,
      estimated_duration_seconds: 420,
    });
    expect(component.deliveryRoutes[33]).toEqual(savedRoute);
  });

  it('allows route management only for the assigned courier or managers', () => {
    const order = { ...makeOrder(34, 'preparing'), delivery_person: 8 };
    component.currentUser = { id: 8, role: 'delivery' };
    expect(component.canManageRoute(order)).toBe(true);

    component.currentUser = { id: 9, role: 'delivery' };
    expect(component.canManageRoute(order)).toBe(false);

    component.currentUser = { id: 10, role: 'manager' };
    expect(component.canManageRoute(order)).toBe(true);
  });

  it('lets managers confirm and move an order into preparation', () => {
    component.currentUser = { id: 10, role: 'manager' };
    const order = makeOrder(35, 'pending');

    component.advanceOrderStatus(order, 'confirmed');

    expect(ordersService.updateOrderStatus).toHaveBeenCalledWith(35, 'confirmed');
    expect(ordersService.getOrders).toHaveBeenCalledTimes(2);
  });

  it('lets a manager notify the customer that food is ready for pickup', () => {
    component.currentUser = { id: 10, role: 'manager' };
    const order = makeOrder(37, 'preparing');

    component.advanceOrderStatus(order, 'ready_for_pickup');

    expect(ordersService.updateOrderStatus).toHaveBeenCalledWith(37, 'ready_for_pickup');
  });

  it('requires a saved route before the courier can start delivery', () => {
    const order = { ...makeOrder(36, 'ready_for_pickup'), delivery_person: 8 };
    component.currentUser = { id: 8, role: 'delivery' };

    component.advanceOrderStatus(order, 'delivering');

    expect(ordersService.updateOrderStatus).not.toHaveBeenCalled();
    expect(component.statusActionErrors[36]).toBe('Перед началом доставки постройте и сохраните маршрут.');
  });

  it('shows the backend reason when route saving fails', () => {
    component.routeOriginAddress = 'Restaurant address';
    component.routeCoordinates = {
      origin_latitude: 43.2389,
      origin_longitude: 76.8897,
      destination_latitude: 43.2511,
      destination_longitude: 76.9142,
    };
    component.routeMetrics = {
      route_distance_meters: 4200,
      estimated_duration_seconds: 420,
    };
    ordersService.saveDeliveryRoute.mockReturnValueOnce(throwError(() => new HttpErrorResponse({
      status: 403,
      error: { detail: 'Only the assigned courier can manage this route.' },
    })));

    component.saveDeliveryRoute(38);

    expect(component.routeSaveError).toBe('Only the assigned courier can manage this route.');
  });

  it('shows the backend reason when courier assignment fails', () => {
    const order = makeOrder(39, 'pending');
    component.currentUser = { id: 10, role: 'manager' };
    component.selectedCourierIds[order.id] = 15;
    ordersService.assignDeliveryPerson.mockReturnValueOnce(throwError(() => new HttpErrorResponse({
      status: 400,
      error: { delivery_person_id: ['Select a valid choice.'] },
    })));

    component.assignCourier(order);

    expect(component.assignmentErrors[order.id]).toBe('Select a valid choice.');
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
