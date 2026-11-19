import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpErrorResponse } from '@angular/common/http';
import { of, throwError } from 'rxjs';
import { vi } from 'vitest';

import { Auth } from '../auth';
import { I18nService } from '../i18n/i18n.service';
import { Support, SupportCase } from '../support';
import { SupportChat } from './support-chat';

describe('SupportChat', () => {
  let fixture: ComponentFixture<SupportChat>;
  let component: SupportChat;
  let supportService: {
    getCases: ReturnType<typeof vi.fn>;
    openCase: ReturnType<typeof vi.fn>;
    sendMessage: ReturnType<typeof vi.fn>;
  };

  const supportCase: SupportCase = {
    id: 1,
    customer: 5,
    customer_name: 'customer',
    order: 10,
    order_number: 'ORD-10',
    issue_description: 'Where is my order?',
    status: 'waiting_for_customer',
    resolution: '',
    messages: [],
    created_at: '2026-01-01T10:00:00Z',
    updated_at: '2026-01-01T10:00:00Z',
  };

  beforeEach(async () => {
    supportService = {
      getCases: vi.fn().mockReturnValue(of([])),
      openCase: vi.fn().mockReturnValue(of(supportCase)),
      sendMessage: vi.fn().mockReturnValue(of(supportCase)),
    };

    await TestBed.configureTestingModule({
      imports: [SupportChat],
      providers: [
        { provide: Auth, useValue: { getCurrentUser: () => ({ role: 'customer' }) } },
        { provide: Support, useValue: supportService },
        { provide: I18nService, useValue: { t: (key: string) => key } },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(SupportChat);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('opens the floating chat and loads the customer case list', () => {
    fixture.nativeElement.querySelector('.support-launcher').click();
    fixture.detectChanges();

    expect(supportService.getCases).toHaveBeenCalledOnce();
    expect(fixture.nativeElement.querySelector('.support-panel')).not.toBeNull();
    expect(fixture.nativeElement.textContent).toContain('supportOrderNumber');
  });

  it('starts an AI chat without requiring an order number', () => {
    component.issueDescription = 'Where is my order?';

    component.openCase();

    expect(supportService.openCase).toHaveBeenCalledWith('', 'Where is my order?');
    expect(component.selectedCase).toEqual(supportCase);
  });

  it('opens the saved conversation when the AI request times out', () => {
    supportService.openCase.mockReturnValue(throwError(() => new HttpErrorResponse({
      status: 503,
      error: { detail: 'AI unavailable', case_id: supportCase.id },
    })));
    supportService.getCases.mockReturnValue(of([supportCase]));
    component.issueDescription = 'Where is my order?';

    component.openCase();

    expect(component.selectedCase).toEqual(supportCase);
    expect(component.issueDescription).toBe('');
    expect(component.error).toBe('supportAiUnavailable');
  });
});
