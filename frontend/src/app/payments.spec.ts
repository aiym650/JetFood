import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { Payments } from './payments';

describe('Payments API integration', () => {
  let service: Payments;
  let httpTesting: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(Payments);
    httpTesting = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpTesting.verify());

  it('loads the persisted payment records from the backend API', () => {
    let paymentStatus = '';
    service.getPayments().subscribe(payments => paymentStatus = payments[0].status);
    httpTesting.expectOne('http://localhost:8000/api/payments/').flush({
      count: 1,
      results: [{
        id: 5,
        order: 12,
        order_number: 'ORD-12',
        customer_name: 'customer',
        method: 'online',
        status: 'paid',
        amount: '1600.00',
        transaction_id: 'SIM-test',
        card_brand: 'visa',
        card_last4: '4242',
        failure_reason: '',
        refund_reason: '',
        created_at: '',
        paid_at: '',
        refunded_at: null,
      }],
    });

    expect(paymentStatus).toBe('paid');
  });

  it('posts cash confirmation and refund actions to their payment endpoints', () => {
    let confirmed = false;
    service.confirmCashPayment(21).subscribe(() => confirmed = true);
    const confirmation = httpTesting.expectOne('http://localhost:8000/api/payments/21/confirm-cash/');
    expect(confirmation.request.method).toBe('POST');
    confirmation.flush({ id: 21 });

    let refunded = false;
    service.refundPayment(21, 'Duplicate order').subscribe(() => refunded = true);
    const refund = httpTesting.expectOne('http://localhost:8000/api/payments/21/refund/');
    expect(refund.request.body).toEqual({ reason: 'Duplicate order' });
    refund.flush({ id: 21 });

    expect(confirmed).toBe(true);
    expect(refunded).toBe(true);
  });

  it('submits card details only to the order payment endpoint', () => {
    let resultStatus = '';
    service.payOrder(12, {
      card_number: '4242424242424242',
      expiry: '12/99',
      cvv: '123',
      cardholder_name: 'Test Customer',
    }).subscribe(result => resultStatus = result.status);
    const request = httpTesting.expectOne('http://localhost:8000/api/payments/12/pay/');
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({
      card_number: '4242424242424242',
      expiry: '12/99',
      cvv: '123',
      cardholder_name: 'Test Customer',
    });
    request.flush({ status: 'paid' });

    expect(resultStatus).toBe('paid');
  });
});
