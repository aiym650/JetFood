/** Acceptance scenarios: real Angular components, explicitly mocked backend/provider replies. */
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter, ActivatedRoute } from '@angular/router';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { BehaviorSubject, of, Subject, throwError } from 'rxjs';
import { vi } from 'vitest';
import { Auth } from './auth';
import { Support } from './support';
import { SupportChat } from './support-chat/support-chat';
import { ReviewForm } from './orders/review-form';
import { OrdersPage } from './orders/orders';
import { PaymentResult } from './payment-history/payment-result';
import { Payments } from './payments';
import { Dashboard } from './dashboard/dashboard';
import { Orders } from './orders';
import { Menu } from './menu';
import { Restaurants } from './restaurants';
import { Addresses } from './addresses';
import { Loyalty } from './loyalty';
import { LoyaltyPanel } from './profile/loyalty-panel';
import { I18nService } from './i18n/i18n.service';
import { commerceTranslations } from './i18n/commerce-translations';

const buyer = { id: 501, role: 'customer', username: 'acceptance' };
const payment = (status = 'pending'): any => ({ id: 11, customer: 501, order: 91, order_number: 'ORD-91', amount: '2500.00', status, paid_at: status === 'paid' ? '2026-11-23T10:00:00Z' : null });
const review: any = { id: 21, order: 91, user_id: 501, restaurant_rating: 4, food_rating: 4, courier_rating: 4, delivery_speed_rating: 4, comment: 'The food was cold but service was helpful.', status: 'published', photos: [] };
const order: any = { id: 91, order_number: 'ORD-91', customer: 501, status: 'delivered', items: [], delivery_address: 'Test', created_at: '2026-11-23T10:00:00Z' };
const dish: any = { id: 3, name: 'Meal', description: 'A fresh meal', price: 4000, restaurant: 1, category: 'Main', rating: 4, is_active: true, image_url: '' };
const quote: any = { items_amount: '4000.00', discount_amount: '400.00', delivery_fee: '500.00', delivery_discount: '0.00', total_amount: '4100.00', promo_code: 'WELCOME', cashback_balance: '2000.00', cashback_max: '1080.00', cashback_amount: '0.00', cashback_forecast: '180.00', cashback_spend_percent: '30' };
const account: any = { available: '2000.00', reserved: '100.00', debt: '0.00', policy: { base_percent: '3', promotional_percent: '7', spend_percent: '30', milestone_every: '5', milestone_minimum: '3000', milestone_bonus: '500' }, entries: [{ id: 1, order_id: 91, kind: 'earn', available_delta: '120.00', reserved_delta: '0.00', debt_delta: '0.00', created_at: '2026-11-23T10:00:00Z' }] };

describe('Acceptance T01–T06 Support AI (mock backend)', () => {
  let fixture: ComponentFixture<SupportChat>; let component: SupportChat; let api: any;
  const conversation = (messages: any[] = []): any => ({ id: 1, customer: 501, language: 'en', status: 'open', messages, order: null });
  const answer = (body: string): any => conversation([{ id: 1, sender: 'customer', body: 'Question' }, { id: 2, sender: 'assistant', body }]);
  beforeEach(async () => {
    api = { getCases: vi.fn(() => of([conversation()])), getCase: vi.fn(() => of(conversation())), faq: vi.fn(() => of([])), sendMessage: vi.fn(() => of(answer('Open Orders to check your order.'))) };
    await TestBed.configureTestingModule({ imports: [SupportChat], providers: [{ provide: Auth, useValue: { getCurrentUser: () => buyer } }, { provide: Support, useValue: api }] }).compileComponents();
    TestBed.inject(I18nService).setLanguage('en'); fixture = TestBed.createComponent(SupportChat); component = fixture.componentInstance;
    component.toggleChat(); fixture.detectChanges();
  });
  it('T01 Sends a question and displays the reply', () => {
    component.messageDraft = 'Where is my order?'; component.sendMessage(); fixture.detectChanges();
    expect(api.sendMessage).toHaveBeenCalledOnce(); expect(fixture.nativeElement.textContent).toContain('Open Orders to check your order.');
  });
  it('T02 Rejects a whitespace-only question', () => {
    component.messageDraft = '   '; component.sendMessage(); expect(api.sendMessage).not.toHaveBeenCalled();
  });
  it('T03 Shows waiting state and prevents duplicate submission', () => {
    const pending = new Subject<any>(); api.sendMessage.mockReturnValue(pending); component.messageDraft = 'Help me'; component.sendMessage(); component.messageDraft = 'Help me'; component.sendMessage(); fixture.detectChanges();
    expect(api.sendMessage).toHaveBeenCalledOnce(); expect(component.replyPending).toBe(true); expect(fixture.nativeElement.querySelector('.typing-indicator')).not.toBeNull();
  });
  it('T04 Explains service unavailability and offers retry', () => {
    api.sendMessage.mockReturnValue(throwError(() => new HttpErrorResponse({ status: 503, error: { case_id: 1 } })));
    component.messageDraft = 'Help me'; component.sendMessage(); fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain(component.text('supportAiUnavailable')); expect(component.retryMode).toBe('reply');
  });
  it('T05 Restores conversation history when reopened', () => {
    api.getCases.mockReturnValue(of([answer('Saved answer')])); component.toggleChat(); component.toggleChat(); fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Saved answer');
  });
  it('T06 Displays an honest lack-of-information answer safely', () => {
    api.sendMessage.mockReturnValue(of(answer('I have no verified refund deadline. Please contact support. <script>alert(1)</script>')));
    component.messageDraft = 'Refund deadline?'; component.sendMessage(); fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('I have no verified refund deadline.'); expect(fixture.nativeElement.querySelector('script')).toBeNull();
  });
});

describe('Acceptance T07–T12 Reviews (mock API)', () => {
  let fixture: ComponentFixture<OrdersPage>; let component: OrdersPage; let http: any; let reviews: any[];
  beforeEach(async () => {
    reviews = [{ ...review }];
    http = { get: vi.fn(() => of(reviews)), post: vi.fn(() => of({ ...review })), patch: vi.fn(() => of({ ...review, status: 'pending_moderation' })) };
    await TestBed.configureTestingModule({ imports: [OrdersPage, ReviewForm], providers: [provideRouter([]), { provide: HttpClient, useValue: http },
      { provide: Orders, useValue: { getOrders: () => of([order]), getDeliveryRoute: () => of(null), getDeliveryCouriers: () => of([]) } },
      { provide: Menu, useValue: { getItems: () => of([]) } },
      { provide: Auth, useValue: { getCurrentUser: () => buyer, currentUser$: new BehaviorSubject(buyer), refreshCurrentUser: () => of(buyer), isLoggedIn: () => true } },
    ] }).compileComponents();
    TestBed.inject(I18nService).setLanguage('en'); fixture = TestBed.createComponent(OrdersPage); component = fixture.componentInstance; fixture.detectChanges();
  });
  it('T07 Submits a valid review and shows acknowledgement', () => {
    component.submitReview(91, { ...review, photos: [] }); fixture.detectChanges();
    expect(http.post).toHaveBeenCalledWith('http://localhost:8000/api/orders/91/review', expect.any(FormData)); expect(component.reviewSuccess[91]).toBeTruthy();
  });
  it('T08 Displays the rejection reason to the author', () => {
    component.ownReviews = { 91: { ...review, status: 'hidden', moderation_reason: 'Remove the private phone number.' } };
    // Open the real order details, which contain the existing review section.
    component.expandedOrderId = 91; fixture.changeDetectorRef.markForCheck(); fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Remove the private phone number.');
  });
  it('T09 Edits own review through the existing endpoint', () => {
    component.beginEditReview(review); component.submitReview(91, { ...review, comment: 'Corrected review text.', photos: [] });
    expect(http.patch).toHaveBeenCalledWith('http://localhost:8000/api/reviews/21', expect.any(FormData));
  });
  it('T10 Does not offer editing another user review', () => {
    const foreign = { ...review, user_id: 999 }; component.ownReviews = { 91: foreign }; component.beginEditReview(foreign); fixture.changeDetectorRef.markForCheck(); fixture.detectChanges();
    expect(fixture.nativeElement.textContent).not.toContain('Edit my review');
    expect(component.canEditReview(foreign)).toBe(false); expect(component.editingReviews[91]).toBeUndefined(); expect(http.patch).not.toHaveBeenCalled();
  });
  it('T11 Validates rating bounds and comment length in the form', () => {
    const formFixture = TestBed.createComponent(ReviewForm); const form = formFixture.componentInstance; const submitted = vi.spyOn(form.submitted, 'emit');
    for (const bad of [{ ...review, food_rating: 0 }, { ...review, food_rating: 6 }, { ...review, food_rating: 2.5 }, { ...review, comment: 'short' }, { ...review, comment: 'x'.repeat(1001) }]) { form.value = { ...bad, photos: [] }; form.submit(); }
    formFixture.detectChanges(); expect(submitted).not.toHaveBeenCalled(); expect(formFixture.nativeElement.textContent).toContain('10 to 1000');
  });
  it('T12 Displays pending moderation after a revision', () => {
    reviews[0].status = 'pending_moderation'; component.beginEditReview(review); component.submitReview(91, { ...review, photos: [] });
    component.expandedOrderId = 91; fixture.changeDetectorRef.markForCheck(); fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Awaiting moderation');
  });
});

describe('Acceptance T13–T20 Payment result (mock provider through backend)', () => {
  let fixture: ComponentFixture<PaymentResult>; let component: PaymentResult; let api: any;
  beforeEach(async () => {
    api = { verifyPayment: vi.fn(() => of({ payment: payment(), test_mode: true })), startCheckout: vi.fn(() => of({ payment: payment(), redirect_url: 'https://pay.freedompay.kz/checkout/test', test_mode: true })) };
    await TestBed.configureTestingModule({ imports: [PaymentResult], providers: [provideRouter([]), { provide: ActivatedRoute, useValue: { snapshot: { queryParamMap: new Map([['order', '91'], ['success', 'true']]) } } }, { provide: Payments, useValue: api }] }).compileComponents();
    TestBed.inject(I18nService).setLanguage('en'); fixture = TestBed.createComponent(PaymentResult); component = fixture.componentInstance; fixture.detectChanges();
  });
  it('T13 Displays the amount received from the backend', () => { expect(fixture.nativeElement.textContent).toContain('2500.00'); expect(fixture.nativeElement.textContent).toContain('Test mode'); });
  it('T14 Opens the provider payment page returned by the backend', () => {
    api.verifyPayment.mockReturnValue(of({ payment: payment('failed'), test_mode: true })); component.verify();
    const redirect = vi.spyOn(component, 'openProvider').mockImplementation(() => {}); component.retry();
    expect(redirect).toHaveBeenCalledWith('https://pay.freedompay.kz/checkout/test');
  });
  it('T15 Shows success only after backend confirms payment', () => { api.verifyPayment.mockReturnValue(of({ payment: payment('paid'), test_mode: true })); component.verify(); fixture.detectChanges(); expect(fixture.nativeElement.textContent).toContain('Payment confirmed by the backend'); });
  it('T16 Shows a confirmed payment failure', () => { api.verifyPayment.mockReturnValue(of({ payment: payment('failed'), test_mode: true })); component.verify(); fixture.detectChanges(); expect(fixture.nativeElement.textContent).toContain('Payment declined'); });
  it('T17 Shows cancellation without success', () => { api.verifyPayment.mockReturnValue(of({ payment: payment('cancelled'), test_mode: true })); component.verify(); fixture.detectChanges(); expect(fixture.nativeElement.textContent).toContain('Payment cancelled'); expect(fixture.nativeElement.textContent).not.toContain('Payment confirmed by the backend'); });
  it('T18 Blocks repeated payment clicks while creating a payment', () => {
    component.payment = payment('failed'); fixture.changeDetectorRef.markForCheck(); api.startCheckout.mockReturnValue(new Subject()); component.retry(); component.retry(); fixture.detectChanges();
    expect(api.startCheckout).toHaveBeenCalledOnce(); expect(fixture.nativeElement.querySelector('button')?.disabled).toBe(true);
  });
  it('T19 Keeps pending after a success redirect before backend confirmation', () => { expect(fixture.nativeElement.textContent).toContain('awaiting backend confirmation'); expect(fixture.nativeElement.textContent).not.toContain('Payment confirmed by the backend'); });
  it('T20 Allows retry only after a confirmed failure', () => {
    component.retry(); expect(api.startCheckout).not.toHaveBeenCalled(); component.payment = payment('failed');
    api.startCheckout.mockReturnValue(throwError(() => new Error('timeout'))); component.retry(); fixture.detectChanges();
    expect(api.startCheckout).toHaveBeenCalledOnce(); expect(fixture.nativeElement.textContent).toContain('Unable to verify payment');
  });
});

describe('Acceptance T21–T30 Cashback and combined flow (mock APIs)', () => {
  let fixture: ComponentFixture<Dashboard>; let component: Dashboard; let api: any; let pay: any;
  beforeEach(async () => {
    localStorage.removeItem('jetfood-cart-501'); sessionStorage.removeItem('jetfood-checkout-501');
    api = { quote: vi.fn(() => of({ ...quote })), createOrder: vi.fn(() => of({ ...order, status: 'pending' })) };
    pay = { startCheckout: vi.fn(() => of({ payment: payment(), redirect_url: 'https://pay.freedompay.kz/checkout/test', test_mode: true })) };
    await TestBed.configureTestingModule({ imports: [Dashboard, LoyaltyPanel, PaymentResult], providers: [provideRouter([]),
      { provide: Auth, useValue: { getCurrentUser: () => buyer, isLoggedIn: () => true } }, { provide: Orders, useValue: api }, { provide: Payments, useValue: pay },
      { provide: Menu, useValue: { getItems: () => of([dish]) } }, { provide: Restaurants, useValue: { getRestaurants: () => of([]) } }, { provide: Addresses, useValue: { getAddresses: () => of([]) } },
      { provide: Loyalty, useValue: { account: () => of(account) } },
      { provide: ActivatedRoute, useValue: { queryParamMap: of(new Map()), snapshot: { queryParamMap: new Map([['order', '91']]) } } },
    ] }).compileComponents();
    TestBed.inject(I18nService).setLanguage('en'); fixture = TestBed.createComponent(Dashboard); component = fixture.componentInstance; fixture.detectChanges(); component.addToCart(component.foodItems[0]); fixture.detectChanges();
  });
  it('T21 Displays the available cashback balance', () => { const panel = TestBed.createComponent(LoyaltyPanel); panel.detectChanges(); expect(panel.nativeElement.textContent).toContain('2000.00'); expect(panel.nativeElement.textContent).toContain('Available balance'); });
  it('T22 Applies an allowed bonus amount through the backend', () => { component.cashbackAmount = 500; component.refreshQuote(); expect(api.quote).toHaveBeenLastCalledWith([{ item_id: 3, quantity: 1 }], '', 500); });
  it('T23 Displays and enforces the server merchandise spending limit', () => { fixture.detectChanges(); const input: HTMLInputElement = fixture.nativeElement.querySelector('#cashback-amount'); expect(input.max).toBe('1080.00'); component.cashbackAmount = 1081; api.quote.mockReturnValue(throwError(() => ({ error: { cashback_amount: ['Limit exceeded'] } }))); component.refreshQuote(); fixture.detectChanges(); expect(fixture.nativeElement.textContent).toContain('exceeds your balance or the server limit'); });
  it('T24 Explains insufficient balance returned by the backend', () => { component.cashbackAmount = 9999; api.quote.mockReturnValue(throwError(() => ({ error: { cashback_amount: ['Insufficient balance'] } }))); component.refreshQuote(); fixture.detectChanges(); expect(component.cartQuote).toBeNull(); expect(fixture.nativeElement.textContent).toContain('exceeds your balance'); });
  it('T25 Keeps delivery separate from redeemed merchandise bonuses', () => { expect(fixture.nativeElement.textContent).toContain('500.00'); expect(fixture.nativeElement.querySelector('#cashback-amount')?.max).toBe('1080.00'); expect(fixture.nativeElement.textContent).toContain('Bonuses applied'); });
  it('T26 Updates the total from the backend after bonuses change', () => { api.quote.mockReturnValue(of({ ...quote, cashback_amount: '500.00', total_amount: '3600.00' })); component.cashbackAmount = 500; component.refreshQuote(); fixture.detectChanges(); expect(fixture.nativeElement.textContent).toContain('3600.00'); expect(component.cartQuote?.cashback_amount).toBe('500.00'); });
  it('T27 Displays the server cashback earnings forecast', () => { expect(fixture.nativeElement.textContent).toContain('Estimated JetPoints after payment and delivery'); expect(fixture.nativeElement.textContent).toContain('180.00'); });
  it('T28 Displays ledger operations and programme conditions', () => { const panel = TestBed.createComponent(LoyaltyPanel); panel.detectChanges(); expect(panel.nativeElement.textContent).toContain('Earned'); expect(panel.nativeElement.textContent).toContain('120.00'); expect(panel.nativeElement.textContent).toContain('Delivery is excluded'); });
  it('T29 Translates new interfaces into English and Russian', () => {
    for (const key of Object.keys(commerceTranslations.en)) { expect((commerceTranslations.ru as any)[key]).toBeTruthy(); }
    component.i18n.setLanguage('ru'); fixture.detectChanges(); expect(fixture.nativeElement.textContent).toContain(commerceTranslations.ru.cashbackUse);
    component.i18n.setLanguage('en'); fixture.detectChanges(); expect(fixture.nativeElement.textContent).toContain(commerceTranslations.en.cashbackUse);
  });
  it('T30 Cart → bonuses → hosted test payment → backend order status', () => {
    api.quote.mockReturnValue(of({ ...quote, cashback_amount: '500.00', total_amount: '3600.00' })); component.cashbackAmount = 500; component.refreshQuote();
    component.deliveryAddress = 'Test address'; component.setPaymentMethod('online'); const redirect = vi.spyOn(component, 'openPaymentPage').mockImplementation(() => {}); component.checkout();
    expect(api.createOrder).toHaveBeenCalledWith(expect.objectContaining({ cashback_amount: 500, payment_method: 'online' }), expect.any(String)); expect(redirect).toHaveBeenCalledOnce();
    // Reuse Payments with an explicitly mocked, verified backend response.
    pay.verifyPayment = vi.fn(() => of({ payment: { ...payment('paid'), order_status: 'confirmed' }, test_mode: true }));
    const resultFixture = TestBed.createComponent(PaymentResult); const result = resultFixture.componentInstance; result.orderId = 91; result.verify();
    resultFixture.changeDetectorRef.detectChanges();
    expect(resultFixture.nativeElement.textContent).toContain('Payment confirmed by the backend');
    expect(result.payment?.order_status).toBe('confirmed');
    expect(localStorage.getItem('jetfood-cart-501')).toBeNull();
  });
});
