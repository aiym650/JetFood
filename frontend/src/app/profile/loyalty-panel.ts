import { ChangeDetectorRef, Component, HostListener, Input, OnDestroy, OnInit, DestroyRef, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { Loyalty, LoyaltyAccount } from '../loyalty';
import { I18nService } from '../i18n/i18n.service';

@Component({
  selector: 'app-loyalty-panel', standalone: true, imports: [CommonModule, RouterLink],
  templateUrl: './loyalty-panel.html', styleUrl: './loyalty-panel.css',
})
export class LoyaltyPanel implements OnInit, OnDestroy {
  @Input() compact = false;
  account: LoyaltyAccount | null = null;
  loading = false; error = false; moreLoading = false; moreError = false;
  secondsRemaining = 0;
  private receivedAt = 0;
  private initialSeconds = 0;
  private timer?: ReturnType<typeof setInterval>;
  private refreshTimer?: ReturnType<typeof setInterval>;
  private destroyRef = inject(DestroyRef);
  constructor(private loyalty: Loyalty, public i18n: I18nService, private cdr: ChangeDetectorRef) {}
  ngOnInit() {
    this.load();
    this.refreshTimer = setInterval(() => { if (!document.hidden) this.load(); }, 30000);
    this.timer = setInterval(() => {
      this.secondsRemaining = Math.max(0, this.initialSeconds - Math.floor((Date.now() - this.receivedAt) / 1000));
      this.cdr.markForCheck();
    }, 1000);
  }
  ngOnDestroy() { clearInterval(this.timer); clearInterval(this.refreshTimer); }
  @HostListener('window:focus') refreshOnFocus() { this.load(); }
  points(minor = 0): string {
    if (!Number.isSafeInteger(minor)) return '—';
    const value = Math.abs(minor);
    return `${minor < 0 ? '−' : ''}${Math.trunc(value / 100).toLocaleString(this.i18n.getCurrentLang())}.${String(value % 100).padStart(2, '0')}`;
  }
  get countdown(): string {
    return `${Math.floor(this.secondsRemaining / 86400)} ${this.i18n.t('jpDays')} ${Math.floor(this.secondsRemaining % 86400 / 3600)} ${this.i18n.t('jpHours')} ${Math.floor(this.secondsRemaining % 3600 / 60)} ${this.i18n.t('jpMinutes')}`;
  }
  get promotionStatus(): string {
    const status = this.account?.second_order?.status ?? 'waiting';
    return status === 'eligible' && this.secondsRemaining === 0 ? 'expired' : status;
  }
  load() {
    if (this.loading) return;
    this.loading = true; this.error = false;
    this.loyalty.account().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({ next: account => {
      this.account = account; this.loading = false;
      this.initialSeconds = account.second_order?.seconds_remaining ?? 0;
      this.secondsRemaining = this.initialSeconds; this.receivedAt = Date.now();
      this.cdr.markForCheck();
    }, error: () => { this.error = true; this.loading = false; this.cdr.markForCheck(); } });
  }
  loadMore() {
    if (!this.account?.next_before || this.moreLoading) return;
    this.moreLoading = true; this.moreError = false;
    this.loyalty.account(this.account.next_before).subscribe({ next: next => {
      if (this.account) this.account = { ...this.account, has_more: next.has_more, next_before: next.next_before, entries: [...this.account.entries, ...next.entries.filter(row => !this.account!.entries.some(old => old.id === row.id))] };
      this.moreLoading = false; this.cdr.markForCheck();
    }, error: () => { this.moreLoading = false; this.moreError = true; this.cdr.markForCheck(); } });
  }
}
