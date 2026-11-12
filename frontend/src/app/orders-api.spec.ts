import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { Orders } from './orders';

describe('Orders API integration', () => {
  let service: Orders;
  let httpTesting: HttpTestingController;

  beforeEach(() => {
    localStorage.setItem('token', 'ui-test-token');
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(Orders);
    httpTesting = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpTesting.verify();
    localStorage.removeItem('token');
  });

  it('submits checkout including the selected payment method', () => {
    let createdOrderId = 0;
    service.createOrder({
      delivery_address: '1 Main Street',
      payment_method: 'online',
      items: [{ item_id: 3, quantity: 2 }],
    }).subscribe(order => createdOrderId = order.id);
    const request = httpTesting.expectOne('http://localhost:8000/api/orders/');

    expect(request.request.method).toBe('POST');
    expect(request.request.headers.get('Authorization')).toBe('Token ui-test-token');
    expect(request.request.body.payment_method).toBe('online');
    request.flush({
      id: 49,
      order_number: 'ORD-49',
      customer: 1,
      customer_name: 'customer',
      delivery_person: null,
      delivery_person_name: null,
      status: 'pending',
      priority: 'normal',
      total_amount: '3200.00',
      delivery_address: '1 Main Street',
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

    expect(createdOrderId).toBe(49);
  });

  it('loads only courier accounts for order assignment', () => {
    let couriers: { id: number; username: string; role: string }[] = [];
    service.getDeliveryCouriers().subscribe(result => couriers = result);
    const request = httpTesting.expectOne('http://localhost:8000/api/auth/users/');

    expect(request.request.method).toBe('GET');
    expect(request.request.headers.get('Authorization')).toBe('Token ui-test-token');
    request.flush({ results: [
      { id: 4, username: 'courier-one', role: 'delivery' },
      { id: 5, username: 'customer-one', role: 'customer' },
    ] });

    expect(couriers).toEqual([{ id: 4, username: 'courier-one', role: 'delivery' }]);
  });

  it('saves the calculated route distance and driving duration', () => {
    let savedRoute: unknown;
    service.saveDeliveryRoute(49, {
      origin_address: 'Restaurant',
      notes: '',
      origin_latitude: 43.2389,
      origin_longitude: 76.8897,
      destination_latitude: 43.2511,
      destination_longitude: 76.9142,
      route_distance_meters: 4200,
      estimated_duration_seconds: 420,
    }).subscribe(route => savedRoute = route);
    const request = httpTesting.expectOne('http://localhost:8000/api/orders/49/route/');

    expect(request.request.method).toBe('PUT');
    expect(request.request.body.route_distance_meters).toBe(4200);
    expect(request.request.body.estimated_duration_seconds).toBe(420);
    request.flush({ route_distance_meters: 4200, estimated_duration_seconds: 420 });

    expect(savedRoute).toEqual({ route_distance_meters: 4200, estimated_duration_seconds: 420 });
  });
});
