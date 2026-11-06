import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Integration as IntegrationService } from '../integration';
import { I18nService } from '../i18n/i18n.service';

@Component({
  selector: 'app-integration',
  imports: [CommonModule],
  templateUrl: './integration.html',
  styleUrl: './integration.css',
})
export class IntegrationComponent implements OnInit {
  integrations: any[] = [];
  loading = false;
  error = '';

  constructor(
    private integrationService: IntegrationService,
    private changeDetector: ChangeDetectorRef,
    public i18n: I18nService
  ) {
    this.i18n.currentLang$
      .pipe(takeUntilDestroyed())
      .subscribe(() => this.changeDetector.markForCheck());
  }

  ngOnInit(): void {
    this.loadIntegrations();
  }

  integrationTypeLabel(type: string): string {
    const key = `integrationTypes.${type}`;
    const label = this.i18n.t(key);
    return label === key ? type : label;
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
}
