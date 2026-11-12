import { Inject, Injectable } from '@angular/core';
import { DOCUMENT } from '@angular/common';
import { BehaviorSubject } from 'rxjs';
import { translations } from './translations';

const catalogTranslationKeys: Record<string, string> = {
  'Пицца': 'menuCategories.pizza',
  'Бургеры': 'menuCategories.burgers',
  'Супы': 'menuCategories.soups',
  'Суши': 'menuCategories.sushi',
  'Салаты': 'menuCategories.salads',
  'Паста': 'menuCategories.pasta',
  'Мексиканская': 'menuCategories.mexican',
  'Мясо': 'menuCategories.meat',
  'Пицца Маргарита': 'menuItems.margherita',
  'Бургер Классический': 'menuItems.classicBurger',
  'Рамен с курицей': 'menuItems.chickenRamen',
  'Суши сет': 'menuItems.sushiSet',
  'Салат Цезарь': 'menuItems.caesarSalad',
  'Паста Карбонара': 'menuItems.carbonara',
  'Тако с говядиной': 'menuItems.beefTacos',
  'Стейк из телятины': 'menuItems.vealSteak',
  'Томаты, моцарелла, базилик': 'menuDescriptions.margherita',
  'Говядина, сыр, овощи, соус': 'menuDescriptions.classicBurger',
  'Куриный бульон, лапша, яйцо': 'menuDescriptions.chickenRamen',
  '8 нигири, 6 роллов': 'menuDescriptions.sushiSet',
  'Курица, пармезан, соус': 'menuDescriptions.caesarSalad',
  'Бекон, сливки, пармезан': 'menuDescriptions.carbonara',
  '3 тако, говядина, сальса': 'menuDescriptions.beefTacos',
  '300г, картофель, овощи': 'menuDescriptions.vealSteak',
  'Джет Пицца': 'restaurantCatalog.jetPizza',
  'Гриль Хаус': 'restaurantCatalog.grillHouse',
  'Азиатская кухня': 'restaurantCatalog.asianKitchen',
  'Свежий стол': 'restaurantCatalog.freshTable',
  'Алматы, улица Абая, 10': 'restaurantCatalog.jetPizzaAddress',
  'Алматы, улица Сатпаева, 25': 'restaurantCatalog.grillHouseAddress',
  'Алматы, улица Панфилова, 8': 'restaurantCatalog.asianKitchenAddress',
  'Алматы, проспект Достык, 14': 'restaurantCatalog.freshTableAddress',
  'Пицца и паста': 'restaurantCatalog.jetPizzaDescription',
  'Бургеры и блюда на гриле': 'restaurantCatalog.grillHouseDescription',
  'Супы и суши': 'restaurantCatalog.asianKitchenDescription',
  'Салаты и легкие блюда': 'restaurantCatalog.freshTableDescription',
};

@Injectable({
  providedIn: 'root'
})
export class I18nService {
  private currentLang = new BehaviorSubject<'en' | 'ru'>('en');
  currentLang$ = this.currentLang.asObservable();

  constructor(@Inject(DOCUMENT) private document: Document) {
    const savedLang = localStorage.getItem('lang') as 'en' | 'ru';
    if (savedLang && (savedLang === 'en' || savedLang === 'ru')) {
      this.currentLang.next(savedLang);
    }
    this.document.documentElement.lang = this.currentLang.value;
  }

  setLanguage(lang: 'en' | 'ru'): void {
    this.currentLang.next(lang);
    localStorage.setItem('lang', lang);
    this.document.documentElement.lang = lang;
  }

  getCurrentLang(): 'en' | 'ru' {
    return this.currentLang.value;
  }

  translate(key: string): string {
    const lang = this.currentLang.value;
    const keys = key.split('.');
    let value: any = translations[lang];

    for (const k of keys) {
      value = value?.[k];
    }

    return value || key;
  }

  t(key: string): string {
    return this.translate(key);
  }

  catalogLabel(value: string): string {
    const key = catalogTranslationKeys[value];
    return key ? this.t(key) : value;
  }
}
