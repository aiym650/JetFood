import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of } from 'rxjs';
import { Auth } from '../auth';
import { Login } from '../auth/login/login';
import { I18nService } from './i18n.service';
import { translations } from './translations';

function strings(value: object, prefix = ''): Record<string, string> {
  return Object.assign({}, ...Object.entries(value).map(([key, entry]) => {
    const path = prefix ? `${prefix}.${key}` : key;
    return typeof entry === 'string' ? { [path]: entry } : strings(entry, path);
  }));
}

describe('Kazakh UI language', () => {
  beforeEach(() => localStorage.removeItem('lang'));
  afterEach(() => {
    localStorage.removeItem('lang');
    document.documentElement.lang = 'en';
  });

  it('has a nonempty translation for every English UI string, including nested statuses', () => {
    const english = strings(translations.en);
    const kazakh = strings(translations.kk);
    expect(Object.keys(english).filter(key => !kazakh[key]?.trim())).toEqual([]);
  });

  it('does not silently substitute English sentences for Kazakh UI text', () => {
    const invariantKeys = new Set([
      'restaurantCatalog.jetPizza', 'restaurantCatalog.grillHouse',
      'restaurantCatalog.asianKitchen', 'restaurantCatalog.freshTable',
      'reviewEyebrow', 'cashbackTitle', 'cardCvv', 'id',
    ]);
    const untranslated = Object.entries(strings(translations.kk))
      .filter(([key, text]) => /[a-z]/i.test(text) && !/[а-яәғқңөұүһі]/iu.test(text) && !invariantKeys.has(key))
      .map(([key]) => key);
    expect(untranslated).toEqual([]);
  });

  it('switches the login form EN → KZ → RU → EN using the visible language buttons', async () => {
    await TestBed.configureTestingModule({ imports: [Login], providers: [
      provideRouter([]), { provide: Auth, useValue: { login: () => of({}) } },
    ] }).compileComponents();
    const fixture = TestBed.createComponent(Login);
    await fixture.whenStable();
    const root: HTMLElement = fixture.nativeElement;
    const languageButtons = Array.from(root.querySelectorAll<HTMLButtonElement>('.lang-btn'));
    for (const [buttonText, lang, heading, submit] of [
      ['EN', 'en', 'Sign in to your account', 'Login'],
      ['KZ', 'kk', 'Аккаунтқа кіру', 'Кіру'],
      ['RU', 'ru', 'Вход в аккаунт', 'Войти'],
      ['EN', 'en', 'Sign in to your account', 'Login'],
    ]) {
      const button = languageButtons.find(button => button.textContent?.trim() === buttonText)!;
      button.click();
      await fixture.whenStable();
      expect(root.querySelector('h2')?.textContent).toBe(heading);
      expect(root.querySelector('[type="submit"]')?.textContent?.trim()).toBe(submit);
      expect(button.getAttribute('aria-pressed')).toBe('true');
      expect(languageButtons.filter(item => item.getAttribute('aria-pressed') === 'true')).toHaveLength(1);
      expect(localStorage.getItem('lang')).toBe(lang);
      expect(document.documentElement.lang).toBe(lang);
    }
  });

  it('restores Kazakh after reloading and still permits switching back', () => {
    localStorage.setItem('lang', 'kk');
    const service = new I18nService(document);
    expect(service.getCurrentLang()).toBe('kk');
    expect(service.t('logout')).toBe('Шығу');
    expect(service.t('orderStatuses.delivered')).toBe('Жеткізілді');
    expect(service.t('jpLevels.silver')).toBe('Күміс');
    service.setLanguage('ru');
    expect(service.t('logout')).toBe('Выйти');
    service.setLanguage('en');
    expect(service.t('logout')).toBe('Logout');
  });
});
