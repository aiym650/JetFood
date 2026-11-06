import { ChangeDetectorRef, Component } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { I18nService } from '../../i18n/i18n.service';

@Component({
  selector: 'app-language-switcher',
  imports: [],
  templateUrl: './language-switcher.html',
  styleUrl: './language-switcher.css',
})
export class LanguageSwitcher {
  currentLang = 'en';

  constructor(private i18n: I18nService, private changeDetector: ChangeDetectorRef) {
    this.i18n.currentLang$.pipe(takeUntilDestroyed()).subscribe(lang => {
      this.currentLang = lang;
      this.changeDetector.markForCheck();
    });
  }

  switchLanguage(lang: 'en' | 'ru'): void {
    this.i18n.setLanguage(lang);
  }
}
