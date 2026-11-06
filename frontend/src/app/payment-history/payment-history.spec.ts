import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of } from 'rxjs';

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
    expect(fixture.nativeElement.textContent).toContain('Issue refund');
  });
});
