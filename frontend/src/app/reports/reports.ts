import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { CommonModule, DOCUMENT } from '@angular/common';
import { Inject } from '@angular/core';
import { ReportDownload, Reports as ReportsService } from '../reports';
import { I18nService } from '../i18n/i18n.service';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

interface ReportRow {
  id: number;
  title: string;
  report_type: string;
  status: string;
  format: string;
  created_at: string;
}

@Component({
  selector: 'app-reports',
  imports: [CommonModule],
  templateUrl: './reports.html',
  styleUrl: './reports.css',
})
export class ReportsComponent implements OnInit {
  reports: ReportRow[] = [];
  loading = false;
  error = '';

  constructor(
    private reportsService: ReportsService,
    private changeDetector: ChangeDetectorRef,
    @Inject(DOCUMENT) private document: Document,
    public i18n: I18nService
  ) {
    this.i18n.currentLang$.pipe(takeUntilDestroyed()).subscribe(() => this.changeDetector.markForCheck());
  }

  ngOnInit(): void {
    this.loadReports();
  }

  loadReports(): void {
    this.loading = true;
    this.error = '';
    this.reportsService.getReports().subscribe({
      next: (data) => {
        this.reports = data;
        this.loading = false;
        this.changeDetector.markForCheck();
      },
      error: () => {
        this.error = this.i18n.t('reportsLoadFailed');
        this.loading = false;
        this.changeDetector.markForCheck();
      }
    });
  }

  downloadReport(id: number): void {
    this.error = '';
    this.reportsService.downloadReport(id).subscribe({
      next: (data: ReportDownload) => {
        const report = this.reports.find(item => item.id === id);
        const contents = JSON.stringify({
          title: report?.title ?? `${this.i18n.t('reports')} ${id}`,
          type: report?.report_type ?? 'unknown',
          created_at: report?.created_at ?? null,
          summary: data.parameters,
        }, null, 2);
        const url = URL.createObjectURL(new Blob([contents], { type: 'application/json;charset=utf-8' }));
        const link = this.document.createElement('a');
        link.href = url;
        link.download = `jetfood-report-${id}.json`;
        this.document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(url);
        this.changeDetector.markForCheck();
      },
      error: () => {
        this.error = this.i18n.t('reportDownloadFailed');
        this.changeDetector.markForCheck();
      }
    });
  }

  reportTypeLabel(type: string): string {
    const key = `reportTypes.${type}`;
    const label = this.i18n.t(key);
    return label === key ? type : label;
  }

  reportStatusLabel(status: string): string {
    const key = `reportStatuses.${status}`;
    const label = this.i18n.t(key);
    return label === key ? status : label;
  }

  reportFormatLabel(format: string): string {
    const labels: Record<string, string> = {
      pdf: 'PDF',
      excel: 'Excel',
      csv: 'CSV',
    };
    return labels[format] ?? format;
  }
}
