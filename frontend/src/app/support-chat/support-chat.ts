import {
  AfterViewChecked,
  ChangeDetectorRef,
  Component,
  DestroyRef,
  ElementRef,
  inject,
  ViewChild,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';
import { Auth } from '../auth';
import { Support, SupportCase } from '../support';
import { I18nService } from '../i18n/i18n.service';

type ChatLanguage = 'ru' | 'kk' | 'en';
type ChatView = 'chat' | 'help' | 'history';

@Component({
  selector: 'app-support-chat',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './support-chat.html',
  styleUrls: ['./support-chat.css', './support-chat-pages.css'],
})
export class SupportChat implements AfterViewChecked {
  private readonly destroyRef = inject(DestroyRef);
  @ViewChild('messageList') private messageList?: ElementRef<HTMLElement>;
  @ViewChild('launcher') private launcher?: ElementRef<HTMLButtonElement>;
  @ViewChild('composer') set composer(element: ElementRef<HTMLTextAreaElement> | undefined) {
    if (element && this.isOpen && this.selectedCase && !this.saving)
      element.nativeElement.focus({ preventScroll: true });
  }
  @ViewChild('languageStart') set languageStart(
    element: ElementRef<HTMLButtonElement> | undefined,
  ) {
    if (element && this.isOpen && !this.saving)
      element.nativeElement.focus({ preventScroll: true });
  }

  isOpen = false;
  view: ChatView = 'chat';
  language: ChatLanguage | null = null;
  loading = false;
  saving = false;
  replyPending = false;
  faqLoading = false;
  faqError = false;
  settingsOpen = false;
  orderEditorOpen = false;
  operatorFormOpen = false;
  error = '';
  operatorNotice = '';
  cases: SupportCase[] = [];
  selectedCase: SupportCase | null = null;
  faqItems: { question: string; answer: string }[] = [];
  messageDraft = '';
  orderNumber = '';
  issueDescription = '';
  pendingBody = '';
  retryMode: 'reply' | 'message' | 'load' | null = null;
  private failedSend: { caseId: number; body: string; requestId: string } | null = null;
  private scrollPending = false;
  private followMessages = true;
  private faqVersion = 0;

  readonly quickTopics = [
    { key: 'quickOrder', icon: 'order' },
    { key: 'quickPromo', icon: 'promo' },
    { key: 'quickPayment', icon: 'payment' },
    { key: 'chatQuickMenu', icon: 'menu' },
  ];

  constructor(
    private auth: Auth,
    private support: Support,
    private changeDetector: ChangeDetectorRef,
    public i18n: I18nService,
  ) {}

  get canUseChat(): boolean {
    return this.auth.getCurrentUser()?.role === 'customer';
  }
  get activeLanguage(): ChatLanguage {
    return this.selectedCase?.language ?? this.language ?? this.i18n.getCurrentLang?.() ?? 'en';
  }
  get showSuggestions(): boolean {
    return (
      !!this.selectedCase &&
      this.selectedCase.status !== 'resolved' &&
      !this.selectedCase.messages.some((message) => message.sender === 'customer') &&
      !this.pendingBody
    );
  }
  text(key: string): string {
    return this.i18n.inLanguage?.(key, this.activeLanguage) ?? this.i18n.t(key);
  }

  ngAfterViewChecked(): void {
    if (this.scrollPending && this.messageList) {
      this.messageList.nativeElement.scrollTop = this.messageList.nativeElement.scrollHeight;
      this.scrollPending = false;
    }
  }

  onScroll(): void {
    const element = this.messageList?.nativeElement;
    if (element)
      this.followMessages = element.scrollHeight - element.scrollTop - element.clientHeight < 80;
  }

  toggleChat(): void {
    this.isOpen = !this.isOpen;
    if (this.isOpen && !this.saving) this.loadCases();
    if (!this.isOpen) this.launcher?.nativeElement.focus();
  }

  onPanelKeydown(event: KeyboardEvent): void {
    if (event.key === 'Escape') {
      if (this.settingsOpen) this.settingsOpen = false;
      else this.toggleChat();
      event.stopPropagation();
    }
  }

  showView(view: ChatView): void {
    this.view = view;
    this.settingsOpen = false;
    this.scrollPending = true;
    if (view === 'help') this.loadFaq();
  }

  loadCases(): void {
    this.loading = true;
    this.error = '';
    this.support
      .getCases()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (cases) => {
          this.cases = cases;
          const restored = this.selectedCase
            ? (cases.find((item) => item.id === this.selectedCase?.id) ?? cases[0])
            : cases[0];
          if (restored) this.acceptCase(restored);
          this.loading = false;
          this.loadFaq();
          this.changeDetector.markForCheck();
        },
        error: (error) => this.handleError(error, 'load'),
      });
  }

  chooseLanguage(language: ChatLanguage): void {
    if (this.saving || this.loading) return;
    this.saving = true;
    this.error = '';
    const request = this.selectedCase
      ? this.support.updateCase(this.selectedCase.id, { language })
      : this.support.openCase('', '', language);
    request.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (supportCase) => {
        this.language = language;
        this.acceptCase(supportCase);
        this.settingsOpen = false;
        this.saving = false;
        this.loadFaq();
        this.changeDetector.markForCheck();
      },
      error: (error) => this.handleError(error),
    });
  }

  selectCase(supportCase: SupportCase): void {
    if (this.saving) return;
    this.clearTransientState();
    this.acceptCase(supportCase);
    this.orderNumber = supportCase.order_number;
    this.view = 'chat';
    this.followMessages = true;
    this.scrollPending = true;
    this.loadFaq();
  }

  startNewCase(): void {
    if (this.saving) return;
    this.clearTransientState();
    this.selectedCase = null;
    this.language = null;
    this.orderNumber = '';
    this.view = 'chat';
  }

  private clearTransientState(): void {
    this.error = '';
    this.operatorNotice = '';
    this.messageDraft = '';
    this.pendingBody = '';
    this.issueDescription = '';
    this.failedSend = null;
    this.retryMode = null;
    this.orderEditorOpen = false;
    this.operatorFormOpen = false;
    this.settingsOpen = false;
  }

  private acceptCase(supportCase: SupportCase): void {
    this.selectedCase = supportCase;
    this.language = supportCase.language ?? this.language;
    this.cases = [supportCase, ...this.cases.filter((item) => item.id !== supportCase.id)];
    if (this.followMessages) this.scrollPending = true;
  }

  caseTitle(supportCase: SupportCase): string {
    return (
      supportCase.messages.find((message) => message.sender === 'customer')?.body ||
      supportCase.issue_description ||
      this.text('chatGeneralQuestion')
    );
  }

  askTopic(key: string): void {
    if (!this.selectedCase || this.saving) return;
    this.messageDraft = this.text(key);
    this.sendMessage();
  }

  onComposerKeydown(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
      event.preventDefault();
      this.sendMessage();
    }
  }

  resizeComposer(event: Event): void {
    const textarea = event.target as HTMLTextAreaElement;
    textarea.style.height = 'auto';
    textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`;
  }

  sendMessage(): void {
    const body = this.messageDraft.trim();
    if (
      !body ||
      body.length > 4000 ||
      !this.selectedCase ||
      this.saving ||
      this.selectedCase.status === 'resolved'
    )
      return;
    this.failedSend = { caseId: this.selectedCase.id, body, requestId: crypto.randomUUID() };
    this.messageDraft = '';
    this.submitMessage();
  }

  private submitMessage(): void {
    if (!this.failedSend || this.saving) return;
    const { caseId, body, requestId } = this.failedSend;
    this.pendingBody = body;
    this.saving = true;
    this.replyPending = true;
    this.error = '';
    this.retryMode = null;
    this.followMessages = true;
    this.scrollPending = true;
    this.support
      .sendMessage(caseId, body, requestId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (supportCase) => {
          this.acceptCase(supportCase);
          this.pendingBody = '';
          this.failedSend = null;
          this.saving = false;
          this.replyPending = false;
          // An idempotent replay may recover a saved question whose AI reply failed.
          if (supportCase.messages.at(-1)?.sender === 'customer') {
            this.error = this.text('supportAiUnavailable');
            this.retryMode = 'reply';
          }
          this.changeDetector.markForCheck();
        },
        error: (error) => this.handleError(error, 'message'),
      });
  }

  retry(): void {
    if (this.saving) return;
    if (this.retryMode === 'load') {
      this.loadCases();
      return;
    }
    if (this.retryMode === 'message' && this.failedSend) {
      this.submitMessage();
      return;
    }
    if (!this.selectedCase) return;
    this.saving = true;
    this.replyPending = true;
    this.error = '';
    this.support
      .retry(this.selectedCase.id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (supportCase) => {
          this.acceptCase(supportCase);
          this.pendingBody = '';
          this.failedSend = null;
          this.retryMode = null;
          this.saving = false;
          this.replyPending = false;
          this.changeDetector.markForCheck();
        },
        error: (error) => this.handleError(error, 'reply'),
      });
  }

  loadFaq(): void {
    const version = ++this.faqVersion;
    this.faqLoading = true;
    this.faqError = false;
    this.support
      .faq(this.activeLanguage)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (items) => {
          if (version !== this.faqVersion) return;
          this.faqItems = items;
          this.faqLoading = false;
          this.changeDetector.markForCheck();
        },
        error: () => {
          if (version !== this.faqVersion) return;
          this.faqLoading = false;
          this.faqError = true;
          this.changeDetector.markForCheck();
        },
      });
  }

  openOperatorForm(): void {
    this.issueDescription =
      this.messageDraft.trim() ||
      [...(this.selectedCase?.messages ?? [])]
        .reverse()
        .find((message) => message.sender === 'customer')?.body ||
      '';
    this.operatorFormOpen = true;
  }

  requestOperator(): void {
    const issue = this.issueDescription.trim();
    if (this.saving || !issue || issue.length > 4000) return;
    this.saving = true;
    this.error = '';
    const request = this.selectedCase
      ? this.support.updateCase(this.selectedCase.id, {
          operator_requested: true,
          issue_description: issue,
        })
      : this.support.openCase(this.orderNumber.trim(), issue, this.activeLanguage, true);
    request.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (supportCase) => {
        this.acceptCase(supportCase);
        this.saving = false;
        this.operatorFormOpen = false;
        this.operatorNotice = this.text('operatorCreated');
        this.view = 'chat';
        this.changeDetector.markForCheck();
      },
      error: (error) => this.handleError(error),
    });
  }

  linkOrder(): void {
    if (!this.selectedCase || this.saving) return;
    this.saving = true;
    this.error = '';
    this.support
      .updateCase(this.selectedCase.id, { order_number: this.orderNumber.trim() })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (supportCase) => {
          this.acceptCase(supportCase);
          this.orderEditorOpen = false;
          this.saving = false;
          this.changeDetector.markForCheck();
        },
        error: (error) => this.handleError(error),
      });
  }

  statusLabel(status: string): string {
    return this.text(`supportStatus.${status}`);
  }

  private handleError(error: unknown, mode: 'message' | 'reply' | 'load' | null = null): void {
    this.loading = false;
    this.saving = false;
    this.replyPending = false;
    this.retryMode = mode;
    if (
      error instanceof HttpErrorResponse &&
      error.status === 503 &&
      (mode === 'reply' || (mode === 'message' && typeof error.error?.case_id === 'number'))
    ) {
      this.error = this.text('supportAiUnavailable');
      this.retryMode = 'reply';
    } else if (error instanceof HttpErrorResponse && error.status === 429) {
      this.error = this.text('chatRateLimit');
    } else if (mode === 'message') {
      this.error = this.text('chatMessageFailed');
    } else {
      this.error = this.text('supportRequestFailed');
    }
    if (error instanceof HttpErrorResponse && error.error?.order_number) {
      this.error = this.text('chatOrderInvalid');
    }
    const caseId = error instanceof HttpErrorResponse ? error.error?.case_id : null;
    if (typeof caseId === 'number') {
      // Recover directly by ID; old conversations may not be on the first list page.
      this.support
        .getCase(caseId)
        .pipe(takeUntilDestroyed(this.destroyRef))
        .subscribe({
          next: (supportCase) => {
            if (this.selectedCase?.id !== caseId) return;
            this.acceptCase(supportCase);
            this.pendingBody = '';
            this.failedSend = null;
            this.changeDetector.markForCheck();
          },
          error: () => this.changeDetector.markForCheck(),
        });
    }
    this.changeDetector.markForCheck();
  }
}
