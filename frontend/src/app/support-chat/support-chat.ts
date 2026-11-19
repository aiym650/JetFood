import { ChangeDetectorRef, Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';
import { Auth } from '../auth';
import { Support, SupportCase } from '../support';
import { I18nService } from '../i18n/i18n.service';

@Component({
  selector: 'app-support-chat',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './support-chat.html',
  styleUrl: './support-chat.css',
})
export class SupportChat {
  isOpen = false;
  loading = false;
  saving = false;
  error = '';
  cases: SupportCase[] = [];
  selectedCase: SupportCase | null = null;
  orderNumber = '';
  issueDescription = '';
  messageDraft = '';

  constructor(
    private auth: Auth,
    private support: Support,
    private changeDetector: ChangeDetectorRef,
    public i18n: I18nService,
  ) {}

  get currentRole(): string {
    return this.auth.getCurrentUser()?.role ?? '';
  }

  get canUseChat(): boolean {
    return this.currentRole === 'customer';
  }

  toggleChat(): void {
    this.isOpen = !this.isOpen;
    if (this.isOpen) this.loadCases();
  }

  loadCases(): void {
    this.loading = true;
    this.error = '';
    this.support.getCases().subscribe({
      next: (cases) => {
        this.cases = cases;
        if (this.selectedCase) {
          this.selectedCase = cases.find(item => item.id === this.selectedCase?.id) ?? null;
        }
        this.loading = false;
        this.changeDetector.markForCheck();
      },
      error: (error: unknown) => this.handleError(error),
    });
  }

  selectCase(supportCase: SupportCase): void {
    this.selectedCase = supportCase;
    this.error = '';
  }

  startNewCase(): void {
    this.selectedCase = null;
    this.orderNumber = '';
    this.issueDescription = '';
    this.error = '';
  }

  openCase(): void {
    const orderNumber = this.orderNumber.trim();
    const issueDescription = this.issueDescription.trim();
    if (!issueDescription || this.saving) return;

    this.saving = true;
    this.error = '';
    this.support.openCase(orderNumber, issueDescription).subscribe({
      next: (supportCase) => {
        this.selectedCase = supportCase;
        this.cases = [supportCase, ...this.cases];
        this.issueDescription = '';
        this.saving = false;
        this.changeDetector.markForCheck();
      },
      error: (error: unknown) => this.handleError(error),
    });
  }

  sendMessage(): void {
    const body = this.messageDraft.trim();
    if (!body || !this.selectedCase || this.saving) return;

    this.saving = true;
    this.error = '';
    this.support.sendMessage(this.selectedCase.id, body).subscribe({
      next: (supportCase) => {
        this.selectedCase = supportCase;
        this.cases = this.cases.map(item => item.id === supportCase.id ? supportCase : item);
        this.messageDraft = '';
        this.saving = false;
        this.changeDetector.markForCheck();
      },
      error: (error: unknown) => this.handleError(error),
    });
  }

  statusLabel(status: string): string {
    return this.i18n.t(`supportStatus.${status}`);
  }

  private handleError(error: unknown): void {
    console.error('Support chat request failed.', error);
    if (error instanceof HttpErrorResponse && error.status === 503) {
      this.error = this.i18n.t('supportAiUnavailable');
    } else if (error instanceof HttpErrorResponse && error.error && typeof error.error === 'object') {
      const fieldErrors = Object.values(error.error)
        .flatMap(value => Array.isArray(value) ? value : [value])
        .find(value => typeof value === 'string');
      this.error = typeof fieldErrors === 'string'
        ? fieldErrors
        : this.i18n.t('supportRequestFailed');
    } else {
      this.error = this.i18n.t('supportRequestFailed');
    }
    this.loading = false;
    this.saving = false;
    this.changeDetector.markForCheck();

    const persistedCaseId = error instanceof HttpErrorResponse
      && typeof error.error?.case_id === 'number'
      ? error.error.case_id
      : null;
    if (persistedCaseId !== null) {
      this.support.getCases().subscribe({
        next: (cases) => {
          this.cases = cases;
          this.selectedCase = cases.find(item => item.id === persistedCaseId) ?? null;
          if (this.selectedCase) {
            this.orderNumber = '';
            this.issueDescription = '';
            this.messageDraft = '';
          }
          this.changeDetector.markForCheck();
        },
        error: (refreshError: unknown) => {
          console.error('Could not reload the saved AI support conversation.', refreshError);
        },
      });
    }
  }
}
