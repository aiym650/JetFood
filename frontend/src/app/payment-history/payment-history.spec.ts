import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { vi } from 'vitest';

import { Auth } from '../auth';
import { I18nService } from '../i18n/i18n.service';
import { PaymentRecord, Payments } from '../payments';
import { PaymentHistoryPage } from './payment-history';

describe('PaymentHistoryPage', () => {
  let fixture: ComponentFixture<PaymentHistoryPage>;
  let component: PaymentHistoryPage;
  const payment: PaymentRecord = {
    id: 1,
    order: 10,
    order_number: 'ORD-10',
    customer_name: 'customer',
    method: 'online',
    status: 'paid',
    amount: '25.00',
    transaction_id: 'SIM-ABC123',
    card_brand: 'visa',
    card_last4: '4242',
    failure_reason: '',
    refund_reason: '',
    created_at: '2026-11-05T10:00:00Z',
    paid_at: '2026-11-05T10:00:00Z',
    refunded_at: null,
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PaymentHistoryPage],
      providers: [
        {
          provide: Payments,
          useValue: {
            getPayments: () => of([payment]),
            confirmCashPayment: () => of(payment),
            refundPayment: () => of({ ...payment, status: 'refunded' }),
          },
        },
        { provide: Auth, useValue: { getCurrentUser: () => ({ role: 'manager' }) } },
      ],
    }).compileComponents();

    TestBed.inject(I18nService).setLanguage('en');
    fixture = TestBed.createComponent(PaymentHistoryPage);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('loads payment history and enables manager refund controls', () => {
    expect(component.payments).toHaveLength(1);
    expect(component.canManage).toBe(true);
    expect(fixture.nativeElement.textContent).toContain('ORD-10');
    expect(fixture.nativeElement.textContent).toContain('Visa **** 4242');
    expect(fixture.nativeElement.textContent).toContain('Payment receipt');
    expect(fixture.nativeElement.textContent).toContain('Issue refund');
  });

  it('shows a failed badge and decline reason without revealing card details', () => {
    const failedPayment: PaymentRecord = {
      ...payment,
      status: 'failed',
      card_last4: '0002',
      failure_reason: 'Card declined',
      paid_at: null,
    };
    vi.spyOn(TestBed.inject(Payments), 'getPayments').mockReturnValue(of([failedPayment]));
    component.loadPayments();
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('Failed');
    expect(fixture.nativeElement.textContent).toContain('Card declined.');
    expect(fixture.nativeElement.textContent).not.toContain('4000000000000002');
  });
});
