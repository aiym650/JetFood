import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import {
  ExternalIntegrationInput,
  ExternalIntegrationRecord,
  IntegrationLogRecord,
  IntegrationType,
  Integration as IntegrationService,
} from '../integration';
import { Auth } from '../auth';
import { I18nService } from '../i18n/i18n.service';

@Component({
  selector: 'app-integration',
  imports: [CommonModule, FormsModule],
  templateUrl: './integration.html',
  styleUrl: './integration.css',
})
export class IntegrationComponent implements OnInit {
  integrations: ExternalIntegrationRecord[] = [];
  logs: IntegrationLogRecord[] = [];
  currentUser: { role: string } | null = null;
  formOpen = false;
  editingId: number | null = null;
  saving = false;
  actionError = '';
  logsVisible = false;
  form: ExternalIntegrationInput = this.emptyForm();
  loading = false;
  error = '';

  constructor(
    private integrationService: IntegrationService,
    private auth: Auth,
    private changeDetector: ChangeDetectorRef,
    public i18n: I18nService
  ) {
    this.i18n.currentLang$
      .pipe(takeUntilDestroyed())
      .subscribe(() => this.changeDetector.markForCheck());
  }

  ngOnInit(): void {
    this.currentUser = this.auth.getCurrentUser();
    this.loadIntegrations();
  }

  get canManage(): boolean {
    return ['admin', 'manager'].includes(this.currentUser?.role ?? '');
  }

  get canDelete(): boolean {
    return this.currentUser?.role === 'admin';
  }

  private emptyForm(): ExternalIntegrationInput {
    return {
      name: '',
      integration_type: 'payment_gateway',
      api_endpoint: '',
      api_key: '',
      status: 'active',
      config: {},
    };
  }

  integrationTypeLabel(type: string): string {
    const key = `integrationTypes.${type}`;
    const label = this.i18n.t(key);
    return label === key ? type : label;
  }

  setIntegrationType(type: string): void {
    const supportedTypes: IntegrationType[] = [
      'payment_gateway',
      'mapping_service',
      'notification_service',
      'analytics_service',
      'inventory_system',
    ];
    const selectedType = supportedTypes.find(value => value === type);
    if (selectedType) this.form.integration_type = selectedType;
  }

  integrationStatusLabel(status: string): string {
    const key = `integrationStatuses.${status}`;
    const label = this.i18n.t(key);
    return label === key ? status : label;
  }

  loadIntegrations(): void {
    this.loading = true;
    this.error = '';
    this.integrationService.getIntegrations().subscribe({
      next: (data) => {
        this.integrations = data;
        this.loading = false;
        this.changeDetector.markForCheck();
      },
      error: () => {
        this.error = this.i18n.t('integrationLoadFailed');
        this.loading = false;
        this.changeDetector.markForCheck();
      }
    });
  }

  testIntegration(id: number): void {
    this.integrationService.testIntegration(id).subscribe({
      next: () => {
        alert(this.i18n.t('integrationTestStarted'));
        this.changeDetector.markForCheck();
      },
      error: () => {
        alert(this.i18n.t('integrationTestFailed'));
        this.changeDetector.markForCheck();
      }
    });
  }

  syncIntegration(id: number): void {
    this.integrationService.syncIntegration(id).subscribe({
      next: () => {
        alert(this.i18n.t('integrationSyncCompleted'));
        this.loadIntegrations();
        this.changeDetector.markForCheck();
      },
      error: () => {
        alert(this.i18n.t('integrationSyncFailed'));
        this.changeDetector.markForCheck();
      }
    });
  }

  beginCreate(): void {
    this.editingId = null;
    this.form = this.emptyForm();
    this.actionError = '';
    this.formOpen = true;
  }

  beginEdit(integration: ExternalIntegrationRecord): void {
    this.editingId = integration.id;
    this.form = {
      name: integration.name,
      integration_type: integration.integration_type,
      api_endpoint: integration.api_endpoint,
      status: integration.status,
      config: integration.config,
      api_key: '',
    };
    this.actionError = '';
    this.formOpen = true;
  }

  saveIntegration(): void {
    if (!this.form.name.trim() || !this.form.api_endpoint.trim()) {
      this.actionError = this.i18n.t('integrationRequiredFields');
      return;
    }
    this.saving = true;
    this.actionError = '';
    const payload = {
      ...this.form,
      name: this.form.name.trim(),
      api_endpoint: this.form.api_endpoint.trim(),
    };
    if (this.editingId !== null && !payload.api_key?.trim()) {
      delete payload.api_key;
    }
    const request = this.editingId === null
      ? this.integrationService.createIntegration(payload)
      : this.integrationService.updateIntegration(this.editingId, payload);
    request.subscribe({
      next: () => {
        this.saving = false;
        this.formOpen = false;
        this.loadIntegrations();
      },
      error: () => {
        this.saving = false;
        this.actionError = this.i18n.t('integrationSaveFailed');
        this.changeDetector.markForCheck();
      },
    });
  }

  deleteIntegration(integration: ExternalIntegrationRecord): void {
    if (!this.canDelete || !confirm(this.i18n.t('confirmDeleteIntegration'))) return;
    this.integrationService.deleteIntegration(integration.id).subscribe({
      next: () => this.loadIntegrations(),
      error: () => {
        this.actionError = this.i18n.t('integrationDeleteFailed');
        this.changeDetector.markForCheck();
      },
    });
  }

  toggleLogs(): void {
    this.logsVisible = !this.logsVisible;
    if (!this.logsVisible) return;
    this.integrationService.getLogs().subscribe({
      next: (logs) => {
        this.logs = logs;
        this.changeDetector.markForCheck();
      },
      error: () => {
        this.actionError = this.i18n.t('integrationLoadFailed');
        this.changeDetector.markForCheck();
      },
    });
  }
}
