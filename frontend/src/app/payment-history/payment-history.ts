import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Auth } from '../auth';
import { I18nService } from '../i18n/i18n.service';
import { PaymentRecord, Payments } from '../payments';

@Component({
  selector: 'app-payment-history',
  imports: [CommonModule, FormsModule],
  templateUrl: './payment-history.html',
  styleUrl: './payment-history.css',
})
export class PaymentHistoryPage implements OnInit {
  payments: PaymentRecord[] = [];
  currentUser: { role: string } | null = null;
  loading = false;
  error = '';
  actionError = '';
  refundPaymentId: number | null = null;
  refundReason = '';
  saving = false;

  get canManage(): boolean {
    return ['admin', 'manager'].includes(this.currentUser?.role ?? '');
  }

  get canConfirmCash(): boolean {
    return ['admin', 'manager', 'delivery'].includes(this.currentUser?.role ?? '');
  }

  constructor(
    private paymentsService: Payments,
    private auth: Auth,
    private changeDetector: ChangeDetectorRef,
    public i18n: I18nService,
  ) {}

  ngOnInit(): void {
    this.currentUser = this.auth.getCurrentUser();
    this.loadPayments();
  }

  loadPayments(): void {
    this.loading = true;
    this.error = '';
    this.paymentsService.getPayments().subscribe({
      next: (payments) => {
        this.payments = payments;
        this.loading = false;
        this.changeDetector.markForCheck();
      },
      error: () => {
        this.error = this.i18n.t('paymentsLoadFailed');
        this.loading = false;
        this.changeDetector.markForCheck();
      },
    });
  }

  beginRefund(payment: PaymentRecord): void {
    this.refundPaymentId = payment.id;
    this.refundReason = '';
    this.actionError = '';
  }

  submitRefund(paymentId: number): void {
    if (!this.refundReason.trim()) {
      this.actionError = this.i18n.t('refundReasonRequired');
      return;
    }
    this.saving = true;
    this.actionError = '';
    this.paymentsService.refundPayment(paymentId, this.refundReason.trim()).subscribe({
      next: () => {
        this.refundPaymentId = null;
        this.refundReason = '';
        this.saving = false;
        this.loadPayments();
      },
      error: () => {
        this.actionError = this.i18n.t('refundFailed');
        this.saving = false;
        this.changeDetector.markForCheck();
      },
    });
  }

  confirmCash(payment: PaymentRecord): void {
    this.saving = true;
    this.actionError = '';
    this.paymentsService.confirmCashPayment(payment.id).subscribe({
      next: () => {
        this.saving = false;
        this.loadPayments();
      },
      error: () => {
        this.actionError = this.i18n.t('paymentConfirmationFailed');
        this.saving = false;
        this.changeDetector.markForCheck();
      },
    });
  }

  paymentMethodLabel(method: string): string {
    return this.i18n.t(method === 'online' ? 'onlinePaymentSimulation' : 'cashOnDelivery');
  }

  paymentStatusLabel(status: string): string {
    return this.i18n.t(`paymentStatuses.${status}`);
  }
}
