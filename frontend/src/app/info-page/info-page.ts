import { ChangeDetectorRef, Component, DestroyRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { I18nService } from '../i18n/i18n.service';
import { LanguageSwitcher } from '../shared/language-switcher/language-switcher';

@Component({
  selector: 'app-info-page',
  imports: [CommonModule, RouterLink, LanguageSwitcher],
  templateUrl: './info-page.html',
  styleUrl: './info-page.css',
})
export class InfoPage {
  readonly titleKey: string;
  readonly descriptionKey: string;

  constructor(
    route: ActivatedRoute,
    private changeDetector: ChangeDetectorRef,
    private destroyRef: DestroyRef,
    public i18n: I18nService
  ) {
    this.titleKey = this.requireTranslationKey(route.snapshot.data['titleKey']);
    this.descriptionKey = this.requireTranslationKey(route.snapshot.data['descriptionKey']);

    this.i18n.currentLang$.pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => this.changeDetector.markForCheck());
  }

  private requireTranslationKey(value: unknown): string {
    if (typeof value !== 'string') {
      throw new Error('Information page route is missing a translation key.');
    }

    return value;
  }
}
