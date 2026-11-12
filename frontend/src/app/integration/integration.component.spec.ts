import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { vi } from 'vitest';
import { Integration as IntegrationService, ExternalIntegrationRecord } from '../integration';
import { Auth } from '../auth';
import { I18nService } from '../i18n/i18n.service';
import { IntegrationComponent } from './integration';

describe('IntegrationComponent', () => {
  let fixture: ComponentFixture<IntegrationComponent>;
  let component: IntegrationComponent;
  let service: {
    getIntegrations: ReturnType<typeof vi.fn>;
    createIntegration: ReturnType<typeof vi.fn>;
    updateIntegration: ReturnType<typeof vi.fn>;
    deleteIntegration: ReturnType<typeof vi.fn>;
    getLogs: ReturnType<typeof vi.fn>;
    testIntegration: ReturnType<typeof vi.fn>;
    syncIntegration: ReturnType<typeof vi.fn>;
  };

  const savedIntegration: ExternalIntegrationRecord = {
    id: 2,
    name: 'Payments',
    integration_type: 'payment_gateway',
    status: 'active',
    api_endpoint: 'https://payments.example.test',
    api_key_present: true,
    config: {},
    last_sync: null,
    created_at: '',
    updated_at: '',
  };

  beforeEach(async () => {
    service = {
      getIntegrations: vi.fn().mockReturnValue(of([])),
      createIntegration: vi.fn().mockReturnValue(of(savedIntegration)),
      updateIntegration: vi.fn().mockReturnValue(of(savedIntegration)),
      deleteIntegration: vi.fn().mockReturnValue(of(undefined)),
      getLogs: vi.fn().mockReturnValue(of([])),
      testIntegration: vi.fn().mockReturnValue(of({ message: 'ok' })),
      syncIntegration: vi.fn().mockReturnValue(of({ message: 'ok' })),
    };
    await TestBed.configureTestingModule({
      imports: [IntegrationComponent],
      providers: [
        { provide: IntegrationService, useValue: service },
        { provide: Auth, useValue: { getCurrentUser: () => ({ role: 'manager' }) } },
      ],
    }).compileComponents();
    TestBed.inject(I18nService).setLanguage('en');
    fixture = TestBed.createComponent(IntegrationComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('lets managers open the create form', () => {
    component.beginCreate();
    fixture.detectChanges(false);

    expect(component.canManage).toBe(true);
    expect(fixture.nativeElement.textContent).toContain('Add integration');
  });

  it('validates required fields before calling the backend', () => {
    component.beginCreate();
    component.saveIntegration();

    expect(component.actionError).toContain('Enter the name');
    expect(service.createIntegration).not.toHaveBeenCalled();
  });

  it('saves a configured integration and refreshes the API list', () => {
    component.beginCreate();
    component.form = {
      name: 'Payments',
      integration_type: 'payment_gateway',
      api_endpoint: 'https://payments.example.test',
      api_key: 'write-only-secret',
      status: 'active',
      config: {},
    };

    component.saveIntegration();

    expect(service.createIntegration).toHaveBeenCalledWith(expect.objectContaining({
      name: 'Payments',
      api_key: 'write-only-secret',
    }));
    expect(service.getIntegrations).toHaveBeenCalledTimes(2);
    expect(component.formOpen).toBe(false);
  });

  it('does not replace a saved key when the edit password field is left blank', () => {
    component.beginEdit(savedIntegration);
    component.saveIntegration();

    expect(service.updateIntegration).toHaveBeenCalledWith(
      savedIntegration.id,
      expect.not.objectContaining({ api_key: '' }),
    );
    expect(service.updateIntegration.mock.calls[0][1]).not.toHaveProperty('api_key');
  });

  it('does not expose delete controls to a manager', () => {
    component.deleteIntegration(savedIntegration);

    expect(component.canDelete).toBe(false);
    expect(service.deleteIntegration).not.toHaveBeenCalled();
  });
});
