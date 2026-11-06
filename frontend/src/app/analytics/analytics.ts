import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Analytics as AnalyticsService } from '../analytics';
import { I18nService } from '../i18n/i18n.service';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

@Component({
  selector: 'app-analytics',
  imports: [CommonModule],
  templateUrl: './analytics.html',
  styleUrl: './analytics.css',
})
export class AnalyticsComponent implements OnInit {
  analysis: any = null;
  loading = false;
  error = '';

  constructor(
    private analyticsService: AnalyticsService,
    private changeDetector: ChangeDetectorRef,
    public i18n: I18nService
  ) {
    this.i18n.currentLang$.pipe(takeUntilDestroyed()).subscribe(() => this.changeDetector.markForCheck());
  }

  ngOnInit(): void {
    this.loadAnalysis();
  }

  loadAnalysis(): void {
    this.loading = true;
    this.analyticsService.getSystemAnalysis().subscribe({
      next: (data) => {
        this.analysis = data;
        this.loading = false;
        this.changeDetector.markForCheck();
      },
      error: (err) => {
        this.error = this.i18n.t('analyticsLoadFailed');
        this.loading = false;
        this.changeDetector.markForCheck();
      }
    });
  }
}
