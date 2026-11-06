import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';
import { vi } from 'vitest';

import { ReportsComponent } from './reports';
import { Reports } from '../reports';
import { I18nService } from '../i18n/i18n.service';

describe('ReportsComponent', () => {
  let component: ReportsComponent;
  let fixture: ComponentFixture<ReportsComponent>;
  let reportsService: {
    getReports: ReturnType<typeof vi.fn>;
    downloadReport: ReturnType<typeof vi.fn>;
  };

  beforeEach(async () => {
    reportsService = {
      getReports: vi.fn().mockReturnValue(of([{
        id: 7,
        title: 'Отчёт по продажам',
        report_type: 'sales',
        status: 'completed',
        format: 'pdf',
        created_at: '2026-11-05T10:00:00Z',
      }])),
      downloadReport: vi.fn(),
    };

    await TestBed.configureTestingModule({
      imports: [ReportsComponent],
      providers: [{ provide: Reports, useValue: reportsService }],
    }).compileComponents();

    TestBed.inject(I18nService).setLanguage('ru');
    fixture = TestBed.createComponent(ReportsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('creates a JSON download with the report summary', () => {
    const createObjectUrl = vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:report');
    const revokeObjectUrl = vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (this: HTMLAnchorElement) {
      expect(this.download).toBe('jetfood-report-7.json');
      expect(this.href).toBe('blob:report');
    });
    reportsService.downloadReport.mockReturnValue(of({
      message: 'Report download link',
      parameters: { total_revenue: '2500.00', total_orders: 3 },
    }));

    component.downloadReport(7);

    expect(createObjectUrl).toHaveBeenCalledOnce();
    expect(createObjectUrl.mock.calls[0][0]).toBeInstanceOf(Blob);
    expect(click).toHaveBeenCalledOnce();
    expect(revokeObjectUrl).toHaveBeenCalledWith('blob:report');
    vi.restoreAllMocks();
  });

  it('shows an error when report summary download fails', () => {
    reportsService.downloadReport.mockReturnValue(throwError(() => new Error('Request failed')));

    component.downloadReport(7);

    expect(component.error).toContain('Не удалось скачать сводку отчёта');
  });
});
