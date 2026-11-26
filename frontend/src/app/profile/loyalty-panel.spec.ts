/** JetPoints UI tests: actual components, explicitly mocked backend responses. */
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of, Subject, throwError } from 'rxjs';
import { vi } from 'vitest';
import { Loyalty, LoyaltyAccount } from '../loyalty';
import { LoyaltyPanel } from './loyalty-panel';
import { I18nService } from '../i18n/i18n.service';

const makeAccount = (): LoyaltyAccount => ({
  available: '1234.50', reserved: '100.00', debt: '0.00', balance_minor: 123450,
  total_earned_minor: 150000, total_redeemed_minor: 26550,
  policy: { base_percent: '5.00', promotional_percent: '7.00', spend_percent: '30.00', silver_orders: '10', gold_orders: '20', silver_percent: '7', gold_percent: '10', second_order_days: '7' },
  level: { code: 'bronze', cashback_percent: '5.00', completed_orders: 4, target_orders: 10, next_level: 'silver', orders_remaining: 6, progress_percent: 40, month: '2026-11' },
  second_order: { status: 'eligible', reward_minor: 100000, deadline: '2026-12-01T00:00:00Z', seconds_remaining: 86400, first_order_id: 1, second_order_id: null, awarded_minor: 0 },
  entries: [{ id: 2, order_id: 10, order_number: 'JP-ORDER-10', kind: 'earn', category: 'cashback', amount_minor: 20000, available_delta: '200.00', reserved_delta: '0.00', debt_delta: '0.00', created_at: '2026-11-25T10:00:00Z' }],
  completed_rewards: [{ order_id: 10, order_number: 'JP-ORDER-10', earned_minor: 20000 }],
});

describe('JetPoints dashboard (mock backend)', () => {
  let fixture: ComponentFixture<LoyaltyPanel>; let component: LoyaltyPanel;
  let api: { account: ReturnType<typeof vi.fn> };
  beforeEach(async () => {
    api = { account: vi.fn(() => of(makeAccount())) };
    await TestBed.configureTestingModule({ imports: [LoyaltyPanel], providers: [provideRouter([]), { provide: Loyalty, useValue: api }] }).compileComponents();
    TestBed.inject(I18nService).setLanguage('en');
  });
  function render() {
    fixture = TestBed.createComponent(LoyaltyPanel); component = fixture.componentInstance; fixture.detectChanges();
  }
  afterEach(() => { fixture?.destroy(); vi.useRealTimers(); });
  it('displays backend JetPoints balance, KZT equivalent, net earned and redeemed totals', () => {
    render(); const text = fixture.nativeElement.textContent;
    expect(text).toContain('JetPoints'); expect(text).toContain('1234.50'); expect(text).toContain('1 JetPoint = 1 ₸');
    expect(text).toContain('1,500.00 JP'); expect(text).toContain('265.50 JP');
  });
  it('displays Bronze progress and the number of orders to Silver', () => {
    render(); expect(fixture.nativeElement.textContent).toContain('Bronze');
    expect(fixture.nativeElement.textContent).toContain('5.00%');
    expect(fixture.nativeElement.querySelector('[role="progressbar"]').getAttribute('aria-valuenow')).toBe('40');
    expect(fixture.nativeElement.textContent).toContain('Silver: 6');
  });
  it('displays Silver and next-level progress received from the backend', () => {
    const account = makeAccount(); account.level = { ...account.level!, code: 'silver', cashback_percent: '7.00', completed_orders: 12, target_orders: 20, next_level: 'gold', orders_remaining: 8, progress_percent: 60 };
    api.account.mockReturnValue(of(account)); render();
    expect(fixture.nativeElement.textContent).toContain('Silver'); expect(fixture.nativeElement.textContent).toContain('7.00%');
    expect(fixture.nativeElement.textContent).toContain('Gold: 8');
  });
  it('displays Gold at 100% without offering another level', () => {
    const account = makeAccount(); account.level = { ...account.level!, code: 'gold', cashback_percent: '10.00', completed_orders: 20, target_orders: null, next_level: null, orders_remaining: 0, progress_percent: 100 };
    api.account.mockReturnValue(of(account)); render();
    expect(fixture.nativeElement.textContent).toContain('10.00%'); expect(fixture.nativeElement.textContent).toContain('Highest level reached');
    expect(fixture.nativeElement.querySelector('[role="progressbar"]').getAttribute('aria-valuenow')).toBe('100');
  });
  it('counts down the second-order deadline and displays expiry', () => {
    vi.useFakeTimers(); const account = makeAccount(); account.second_order!.seconds_remaining = 2;
    api.account.mockReturnValue(of(account)); render();
    expect(fixture.nativeElement.textContent).toContain('Time left');
    vi.advanceTimersByTime(3000); fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('The qualifying period has ended.');
    expect(fixture.nativeElement.querySelector('.jp-countdown')).toBeNull();
  });
  it('shows a credited second-order reward and its ledger entry', () => {
    const account = makeAccount(); account.second_order!.status = 'awarded'; account.second_order!.awarded_minor = 100000;
    account.entries[0] = { ...account.entries[0], category: 'second_order', amount_minor: 100000 };
    api.account.mockReturnValue(of(account)); render();
    expect(fixture.nativeElement.textContent).toContain('Reward credited to your account!');
    expect(fixture.nativeElement.querySelector('.jp-ledger').textContent).toContain('Second-order bonus');
    expect(fixture.nativeElement.querySelector('.jp-ledger').textContent).toContain('1,000.00 JP');
  });
  it('shows a reversed reward instead of a new claim', () => {
    const account = makeAccount(); account.second_order!.status = 'reversed'; account.second_order!.awarded_minor = 0;
    api.account.mockReturnValue(of(account)); render();
    expect(fixture.nativeElement.textContent).toContain('Reward reversed after a cancellation or refund.');
    expect(fixture.nativeElement.querySelector('.jp-countdown')).toBeNull();
  });
  it('shows loading, an error, and a successful retry', () => {
    const pending = new Subject<LoyaltyAccount>(); api.account.mockReturnValueOnce(pending); render();
    expect(fixture.nativeElement.querySelector('[role="status"]')).not.toBeNull();
    pending.error(new Error('Unavailable')); fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('[role="alert"]')).not.toBeNull();
    (fixture.nativeElement.querySelector('[role="alert"] button') as HTMLButtonElement).click(); fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('1234.50'); expect(fixture.nativeElement.querySelector('[role="alert"]')).toBeNull();
  });
  it('displays an empty ledger without manufacturing transactions', () => {
    const account = makeAccount(); account.entries = []; account.completed_rewards = [];
    api.account.mockReturnValue(of(account)); render();
    expect(fixture.nativeElement.querySelector('.jp-empty')).not.toBeNull();
    expect(fixture.nativeElement.querySelectorAll('.jp-ledger li')).toHaveLength(0);
  });
  it('loads another history page and removes duplicated rows', () => {
    const first = makeAccount(); first.has_more = true; first.next_before = 2;
    const next = makeAccount(); next.entries = [...first.entries, { ...first.entries[0], id: 1, order_number: 'JP-ORDER-1' }];
    api.account.mockReturnValueOnce(of(first)).mockReturnValueOnce(of(next)); render(); component.loadMore(); fixture.detectChanges();
    expect(api.account).toHaveBeenLastCalledWith(2); expect(fixture.nativeElement.querySelectorAll('.jp-ledger li')).toHaveLength(2);
  });
  it('renders JetPoints in Russian and English', () => {
    render(); component.i18n.setLanguage('ru'); fixture.changeDetectorRef.markForCheck(); fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Бронзовый'); expect(fixture.nativeElement.textContent).toContain('Бонус за второй заказ');
    component.i18n.setLanguage('en'); fixture.changeDetectorRef.markForCheck(); fixture.detectChanges(); expect(fixture.nativeElement.textContent).toContain('Bronze');
  });
  it('shows a compact dashboard card with a link to full history', () => {
    fixture = TestBed.createComponent(LoyaltyPanel); component = fixture.componentInstance; component.compact = true; fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('a')?.getAttribute('href')).toBe('/profile'); expect(fixture.nativeElement.querySelector('.jp-ledger')).toBeNull();
  });
});
