import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpErrorResponse } from '@angular/common/http';
import { of, Subject, throwError } from 'rxjs';
import { vi } from 'vitest';
import { Auth } from '../auth';
import { I18nService } from '../i18n/i18n.service';
import { Support, SupportCase } from '../support';
import { SupportChat } from './support-chat';

describe('SupportChat', () => {
  let fixture: ComponentFixture<SupportChat>;
  let component: SupportChat;
  let api: Record<
    'getCases' | 'getCase' | 'openCase' | 'sendMessage' | 'updateCase' | 'retry' | 'faq',
    ReturnType<typeof vi.fn>
  >;
  const conversation = (messages: SupportCase['messages'] = []): SupportCase => ({
    id: 1,
    customer: 5,
    customer_name: 'customer',
    order: null,
    order_number: '',
    language: 'ru',
    issue_description: '',
    status: 'waiting_for_customer',
    resolution: '',
    messages,
    created_at: '2026-11-20T10:00:00Z',
    updated_at: '2026-11-20T10:00:00Z',
  });
  const userMessage = {
    id: 2,
    sender: 'customer' as const,
    body: 'Как применить промокод?',
    created_at: '2026-11-20T10:00:00Z',
  };
  const answer = {
    id: 3,
    sender: 'assistant' as const,
    body: 'Откройте корзину и введите код.',
    created_at: '2026-11-20T10:00:01Z',
  };

  beforeEach(async () => {
    api = {
      getCases: vi.fn().mockReturnValue(of([])),
      getCase: vi.fn().mockReturnValue(of(conversation([userMessage]))),
      openCase: vi.fn().mockReturnValue(of(conversation())),
      sendMessage: vi.fn().mockReturnValue(of(conversation([userMessage, answer]))),
      updateCase: vi.fn().mockReturnValue(of(conversation())),
      retry: vi.fn().mockReturnValue(of(conversation([userMessage, answer]))),
      faq: vi
        .fn()
        .mockReturnValue(
          of([{ question: 'Как оплатить?', answer: 'Выберите способ оплаты в корзине.' }]),
        ),
    };
    await TestBed.configureTestingModule({
      imports: [SupportChat],
      providers: [
        { provide: Auth, useValue: { getCurrentUser: () => ({ role: 'customer' }) } },
        { provide: Support, useValue: api },
      ],
    }).compileComponents();
    TestBed.inject(I18nService).setLanguage('ru');
    fixture = TestBed.createComponent(SupportChat);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  function open(): void {
    (fixture.nativeElement.querySelector('.support-launcher') as HTMLButtonElement).click();
    fixture.detectChanges();
  }

  it('shows a language picker and a clearly labelled AI chat on first open', async () => {
    open();
    await fixture.whenStable();
    fixture.detectChanges();
    const root: HTMLElement = fixture.nativeElement;
    expect(api.getCases).toHaveBeenCalledOnce();
    expect(root.querySelector('[role="dialog"]')).not.toBeNull();
    expect(root.textContent).toContain('Чем могу помочь?');
    expect(root.textContent).toContain('Русский');
    expect(root.textContent).toContain('Қазақша');
    expect(root.textContent).toContain('English');
    expect(root.querySelector('textarea')?.disabled).toBe(true);
  });

  it('saves language before enabling free-form questions without requiring an order', () => {
    open();
    (fixture.nativeElement.querySelector('.language-picker button') as HTMLButtonElement).click();
    fixture.detectChanges();
    expect(api.openCase).toHaveBeenCalledWith('', '', 'ru');
    expect(fixture.nativeElement.querySelector('.message-composer textarea').disabled).toBe(false);
    expect(fixture.nativeElement.querySelector('.order-editor')).toBeNull();
    expect(fixture.nativeElement.textContent).toContain('Или напишите свой вопрос');
  });

  it('shows an outgoing message and waiting indicator until the AI response arrives', () => {
    const response = new Subject<SupportCase>();
    api.sendMessage.mockReturnValue(response);
    component.selectCase(conversation());
    component.isOpen = true;
    component.messageDraft = userMessage.body;
    component.sendMessage();
    component.sendMessage();
    fixture.detectChanges();
    expect(api.sendMessage).toHaveBeenCalledOnce();
    expect(component.messageDraft).toBe('');
    expect(fixture.nativeElement.querySelector('.pending-message').textContent).toContain(
      userMessage.body,
    );
    expect(fixture.nativeElement.querySelector('.typing-indicator')).not.toBeNull();
    response.next(conversation([userMessage, answer]));
    fixture.changeDetectorRef.markForCheck();
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain(answer.body);
    expect(fixture.nativeElement.querySelector('.pending-message')).toBeNull();
    expect(component.saving).toBe(false);
  });

  it('sends a quick topic to the actual service', () => {
    component.selectCase(conversation());
    component.askTopic('quickOrder');
    expect(api.sendMessage).toHaveBeenCalledWith(1, 'Где мой заказ?', expect.any(String));
  });

  it('keeps the same request ID when retrying a network failure', () => {
    api.sendMessage.mockReturnValueOnce(throwError(() => new HttpErrorResponse({ status: 0 })));
    component.selectCase(conversation());
    component.messageDraft = userMessage.body;
    component.sendMessage();
    const initial = api.sendMessage.mock.calls[0];
    expect(component.pendingBody).toBe(userMessage.body);
    component.retry();
    expect(api.sendMessage.mock.calls[1]).toEqual(initial);
    expect(component.error).toBe('');
  });

  it('recovers a provider failure by direct conversation ID and retries only the AI reply', () => {
    api.sendMessage.mockReturnValue(
      throwError(() => new HttpErrorResponse({ status: 503, error: { case_id: 1 } })),
    );
    component.selectCase(conversation());
    component.messageDraft = userMessage.body;
    component.sendMessage();
    expect(api.getCase).toHaveBeenCalledWith(1);
    expect(component.selectedCase?.messages).toHaveLength(1);
    expect(component.pendingBody).toBe('');
    expect(component.retryMode).toBe('reply');
    component.retry();
    expect(api.sendMessage).toHaveBeenCalledOnce();
    expect(api.retry).toHaveBeenCalledWith(1);
    expect(component.selectedCase?.messages).toHaveLength(2);
  });

  it('does not pretend an idempotently recovered question already has an AI reply', () => {
    api.sendMessage.mockReturnValue(of(conversation([userMessage])));
    component.selectCase(conversation());
    component.messageDraft = userMessage.body;
    component.sendMessage();
    expect(component.retryMode).toBe('reply');
    expect(component.error).toBeTruthy();
  });

  it('retries the original message when a gateway returns 503 without a saved conversation ID', () => {
    api.sendMessage.mockReturnValueOnce(throwError(() => new HttpErrorResponse({ status: 503 })));
    component.selectCase(conversation());
    component.messageDraft = userMessage.body;
    component.sendMessage();
    expect(component.retryMode).toBe('message');
    component.retry();
    expect(api.sendMessage.mock.calls[1]).toEqual(api.sendMessage.mock.calls[0]);
    expect(api.retry).not.toHaveBeenCalled();
  });

  it('does not replace a newly selected conversation with a delayed recovery response', () => {
    const recovery = new Subject<SupportCase>();
    api.getCase.mockReturnValue(recovery);
    api.sendMessage.mockReturnValue(
      throwError(() => new HttpErrorResponse({ status: 503, error: { case_id: 1 } })),
    );
    component.selectCase(conversation());
    component.messageDraft = userMessage.body;
    component.sendMessage();
    component.selectCase({ ...conversation(), id: 2 });
    recovery.next(conversation([userMessage]));
    recovery.complete();
    expect(component.selectedCase?.id).toBe(2);
  });

  it('preserves Shift+Enter and IME composition and sends on Enter', () => {
    component.selectCase(conversation());
    component.messageDraft = userMessage.body;
    component.onComposerKeydown(new KeyboardEvent('keydown', { key: 'Enter', shiftKey: true }));
    component.onComposerKeydown(new KeyboardEvent('keydown', { key: 'Enter', isComposing: true }));
    expect(api.sendMessage).not.toHaveBeenCalled();
    component.onComposerKeydown(new KeyboardEvent('keydown', { key: 'Enter' }));
    expect(api.sendMessage).toHaveBeenCalledOnce();
  });

  it('restores history and safely displays model HTML as plain text', () => {
    const unsafe = { ...answer, body: '<img src=x onerror="alert(1)">' };
    api.getCases.mockReturnValue(of([conversation([userMessage, unsafe])]));
    open();
    expect(fixture.nativeElement.querySelector('.message-bubble img')).toBeNull();
    expect(fixture.nativeElement.textContent).toContain('<img src=x');
    component.showView('history');
    fixture.changeDetectorRef.markForCheck();
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('.history-item').textContent).toContain(
      userMessage.body,
    );
  });

  it('keeps verified FAQ accessible when loading conversations fails', () => {
    api.getCases.mockReturnValue(throwError(() => new HttpErrorResponse({ status: 0 })));
    open();
    component.showView('help');
    fixture.changeDetectorRef.markForCheck();
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('.faq-card').textContent).toContain('Как оплатить?');
  });

  it('requires an explicit problem description to create a staff request', () => {
    component.selectCase(conversation([userMessage]));
    component.openOperatorForm();
    expect(api.updateCase).not.toHaveBeenCalled();
    expect(component.issueDescription).toBe(userMessage.body);
    component.requestOperator();
    expect(api.updateCase).toHaveBeenCalledWith(1, {
      operator_requested: true,
      issue_description: userMessage.body,
    });
    expect(component.operatorNotice).toBeTruthy();
  });

  it('shows an action for a new conversation when the old one is resolved', () => {
    api.getCases.mockReturnValue(of([{ ...conversation(), status: 'resolved' }]));
    open();
    expect(fixture.nativeElement.querySelector('.message-composer')).toBeNull();
    expect(fixture.nativeElement.textContent).toContain('Новый');
  });
});
