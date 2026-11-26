import { ChangeDetectorRef, Component, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { Payments, PaymentRecord } from '../payments';
import { I18nService } from '../i18n/i18n.service';

@Component({
  selector: 'app-payment-result', standalone: true, imports: [CommonModule, RouterLink],
  template: `<section class="commerce-panel payment-result" aria-live="polite">
    <p *ngIf="testMode" class="commerce-notice">{{ i18n.t('paymentTestMode') }}</p>
    <h1>{{ i18n.t(statusKey) }}</h1>
    <p *ngIf="payment">#{{ payment.order_number }} · {{ payment.amount }} ₸</p>
    <p *ngIf="error" role="alert">{{ i18n.t('paymentUnavailable') }}</p>
    <button class="ui-button" (click)="verify()" [disabled]="busy">{{ i18n.t('paymentVerify') }}</button>
    <button *ngIf="payment?.status === 'pending'" class="ui-button ui-button-primary" (click)="continuePayment()" [disabled]="busy">{{ i18n.t('hostedPayment') }}</button>
    <button *ngIf="payment?.status === 'failed'" class="ui-button ui-button-primary" (click)="retry()" [disabled]="busy">{{ i18n.t('paymentRetry') }}</button>
    <a routerLink="/orders" class="ui-button">{{ i18n.t('backToOrders') }}</a>
  </section>`,
})
export class PaymentResult implements OnInit, OnDestroy {
  payment: PaymentRecord | null = null;
  testMode = false; busy = false; error = false;
  orderId = 0; private timer?: ReturnType<typeof setTimeout>; private polls = 0;
  constructor(private payments: Payments, private route: ActivatedRoute, public i18n: I18nService, private cdr: ChangeDetectorRef) {}
  get statusKey() {
    return ({ paid: 'paymentConfirmed', failed: 'paymentFailed', cancelled: 'paymentCancelled', expired: 'paymentExpired', refunded: 'paymentRefunded', partially_refunded: 'paymentPartialRefund' } as Record<string, string>)[this.payment?.status ?? ''] ?? 'paymentChecking';
  }
  ngOnInit() { this.orderId = Number(this.route.snapshot.queryParamMap.get('order')); if (Number.isSafeInteger(this.orderId) && this.orderId > 0) this.verify(); else this.error = true; }
  ngOnDestroy() { clearTimeout(this.timer); }
  verify() {
    if (this.busy || !this.orderId) return;
    clearTimeout(this.timer); this.busy = true; this.error = false;
    this.payments.verifyPayment(this.orderId).subscribe({
      next: result => { this.payment = result.payment; this.testMode = result.test_mode; this.busy = false;
        if (this.payment.paid_at) this.clearPaidCart();
        if (this.payment.status === 'pending' && this.polls++ < 5) this.timer = setTimeout(() => this.verify(), 5000);
        this.cdr.markForCheck(); },
      error: () => { this.busy = false; this.error = true; this.cdr.markForCheck(); },
    });
  }
  private clearPaidCart() {
    const key = `jetfood-payment-order-${this.orderId}`;
    try {
      const saved = JSON.parse(sessionStorage.getItem(key) ?? 'null');
      if (saved && Number.isSafeInteger(saved.userId) && saved.userId === this.payment?.customer) {
        const cartKey = `jetfood-cart-${saved.userId}`;
        const checkoutKey = `jetfood-checkout-${saved.userId}`;
        if (localStorage.getItem(cartKey) === saved.cart && sessionStorage.getItem(checkoutKey) === saved.checkout) {
          localStorage.removeItem(cartKey);
          sessionStorage.removeItem(checkoutKey);
        }
      }
    } catch { /* An older session may contain a plain pending marker. */ }
    sessionStorage.removeItem(key);
  }
  retry() {
    if (this.busy || this.payment?.status !== 'failed') return;
    this.start();
  }
  continuePayment() {
    if (this.busy || this.payment?.status !== 'pending') return;
    this.start();
  }
  private start() {
    this.busy = true; this.error = false;
    this.payments.startCheckout(this.orderId).subscribe({ next: result => {
      this.payment = result.payment; this.testMode = result.test_mode; this.busy = false;
      if (this.payment.paid_at) this.clearPaidCart();
      if (result.redirect_url) this.openProvider(result.redirect_url);
      this.cdr.markForCheck();
    }, error: () => { this.busy = false; this.error = true; this.cdr.markForCheck(); } });
  }
  openProvider(url: string) { const parsed = new URL(url); if (parsed.protocol === 'https:' && parsed.hostname.endsWith('.freedompay.kz')) window.location.assign(url); else this.error = true; }
}
