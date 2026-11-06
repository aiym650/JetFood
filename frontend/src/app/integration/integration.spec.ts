import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of } from 'rxjs';

import { IntegrationComponent } from './integration';
import { Integration } from '../integration';
import { I18nService } from '../i18n/i18n.service';

describe('IntegrationComponent', () => {
  let component: IntegrationComponent;
  let fixture: ComponentFixture<IntegrationComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [IntegrationComponent],
      providers: [
        { provide: Integration, useValue: { getIntegrations: () => of([]) } },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(IntegrationComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('updates integration labels when the language changes', () => {
    const i18n = TestBed.inject(I18nService);
    i18n.setLanguage('ru');
    fixture.detectChanges(false);

    expect(fixture.nativeElement.textContent).toContain('Внешние интеграции');
    expect(fixture.nativeElement.textContent).toContain('Интеграции не настроены');
  });
});
