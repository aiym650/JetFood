import { Inject, Injectable } from '@angular/core';
import { DOCUMENT } from '@angular/common';
import { BehaviorSubject } from 'rxjs';
import { translations } from './translations';

const catalogTranslationKeys: Record<string, string> = {
  'Пицца': 'menuCategories.pizza',
  'Бургеры': 'catalogCuisineBurgers',
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
  'Донер и шаурма': 'catalogCuisineDoner',
  'Жареная курица': 'catalogCuisineFriedChicken',
  'Паназиатская кухня': 'catalogCuisinePanAsian',
  'Суши и японская кухня': 'catalogCuisineJapanese',
  'Казахская кухня': 'catalogCuisineKazakh',
  'Фастфуд и донер': 'catalogCuisineFastFood',
  'Комбо': 'catalogCategoryCombo',
  'Донеры': 'catalogCategoryDoner',
  'Донер': 'catalogCategoryDoner',
  'Сеты': 'catalogCategorySets',
  'Гарниры': 'catalogCategorySides',
  'Комбо 1,5 куриного донера и напиток': 'catalogMenuItems.donerAbayaChickenCombo',
  'Комбо 1,5 ассорти донера и напиток': 'catalogMenuItems.donerAbayaMixedCombo',
  'Комбо 1,5 говяжьего донера и напиток': 'catalogMenuItems.donerAbayaBeefCombo',
  'Комбо Level up Assorti 1,5': 'catalogMenuItems.satpaevaLevelUpCombo',
  'Донер в лаваше 1,5 говяжий и Напиток днс': 'catalogMenuItems.satpaevaBeefDonerCombo',
  'Донер в лаваше 1,5 куриный и Напиток днс': 'catalogMenuItems.satpaevaChickenDonerCombo',
  'Комбо Чипс Донер Куриный Днс': 'catalogMenuItems.satpaevaChickenChipsCombo',
  'Комбо чизбургер курица': 'catalogMenuItems.bahandiChickenCheeseburgerCombo',
  'Комбо чизбургер говядина': 'catalogMenuItems.bahandiBeefCheeseburgerCombo',
  'Комбо чизбургер курица х2': 'catalogMenuItems.bahandiDoubleChickenCheeseburgerCombo',
  'Комбо чизбургер говядина х2': 'catalogMenuItems.bahandiDoubleBeefCheeseburgerCombo',
  'Комбо чизбургер микс x2': 'catalogMenuItems.bahandiMixedCheeseburgerCombo',
  'Бургер говядина': 'catalogMenuItems.bahandiBeefBurger',
  'Бургер курица': 'catalogMenuItems.bahandiChickenBurger',
  'Чизбургер говядина': 'catalogMenuItems.bahandiBeefCheeseburger',
  'Чизбургер курица': 'catalogMenuItems.bahandiChickenCheeseburger',
  'Картофель фри': 'catalogMenuItems.bahandiFries',
  'Сет Бонапарт (80 шт и Пепперони и Маргарита и Кола 2 л)': 'catalogMenuItems.okadzakiBonaparteSet',
  'Сет Венеция (64 шт и Пепперони и Кола)': 'catalogMenuItems.okadzakiVeniceSet',
  'Комбо №1': 'catalogMenuItems.okadzakiComboOne',
  'Комбо №2': 'catalogMenuItems.okadzakiComboTwo',
  'Бургер с куриной котлетой с сыром, картофель фри, напиток и соус на выбор.': 'catalogMenuDescriptions.bahandiChickenCheeseburgerCombo',
  'Бургер с говяжьей котлетой с сыром, картофель фри, напиток и соус на выбор.': 'catalogMenuDescriptions.bahandiBeefCheeseburgerCombo',
  'Бургер с двойной куриной котлетой с сыром, картофель фри, напиток и соус на выбор.': 'catalogMenuDescriptions.bahandiDoubleChickenCheeseburgerCombo',
  'Бургер с двойной говяжьей котлетой с сыром, картофель фри, напиток и соус на выбор.': 'catalogMenuDescriptions.bahandiDoubleBeefCheeseburgerCombo',
  'Бургер с говяжьей и куриной котлетами с сыром, картофель фри, напиток и соус на выбор.': 'catalogMenuDescriptions.bahandiMixedCheeseburgerCombo',
  'Говяжий бургер с одной котлетой.': 'catalogMenuDescriptions.bahandiBeefBurger',
  'Куриный бургер с одной котлетой.': 'catalogMenuDescriptions.bahandiChickenBurger',
  'Говяжий бургер с одной котлетой и сыром.': 'catalogMenuDescriptions.bahandiBeefCheeseburger',
  'Куриный бургер с котлетой и сыром.': 'catalogMenuDescriptions.bahandiChickenCheeseburger',
  'проспект Абая, 89': 'catalogAddresses.abay89',
  'проспект Абая, 160/5': 'catalogAddresses.abay160_5',
  '8-й микрорайон, 1А': 'catalogAddresses.microdistrict8_1a',
  'улица Байтурсынова, 106': 'catalogAddresses.baitursynov106',
  '4-й микрорайон, 28/1': 'catalogAddresses.microdistrict4_28_1',
  'улица Радостовца, 292/4': 'catalogAddresses.radostovtsa292_4',
  'улица Розыбакиева, 162/3': 'catalogAddresses.rozybakieva162_3',
  'проспект Абая, 60': 'catalogAddresses.abay60',
  'улица Панфилова, 92': 'catalogAddresses.panfilov92',
  'проспект Абая, 27': 'catalogAddresses.abay27',
  'Самал-3, 4Д': 'catalogAddresses.samal3_4d',
  'улица Толе би, 229/3': 'catalogAddresses.tolebi229_3',
  'улица Толе би, 274А': 'catalogAddresses.tolebi274a',
  'улица Розыбакиева, 336, блок 15': 'catalogAddresses.rozybakieva336_block15',
  'улица Ораза Жандосова, 57': 'catalogAddresses.orazZhandosov57',
  'проспект Достык, 91/1': 'catalogAddresses.dostyk91_1',
  'улица Шолохова, 13': 'catalogAddresses.sholokhov13',
  'улица Жамбыла, 77': 'catalogAddresses.zhambyl77',
  'Самал-1, 2Б': 'catalogAddresses.samal1_2b',
  '5-й микрорайон, 12А': 'catalogAddresses.microdistrict5_12a',
  'Самал-3, 4Д/1': 'catalogAddresses.samal3_4d1',
  'улица Жибек Жолы, 106': 'catalogAddresses.zhibekZholy106',
  'улица Тимирязева, 42/3': 'catalogAddresses.timiryazev42_3',
  'улица Розыбакиева, 336, блок 2': 'catalogAddresses.rozybakieva336_block2',
  'проспект Сатпаева, 90/21': 'catalogAddresses.satpaeva90_21',
};

@Injectable({
  providedIn: 'root'
})
export class I18nService {
  private currentLang = new BehaviorSubject<'en' | 'ru' | 'kk'>('en');
  currentLang$ = this.currentLang.asObservable();

  constructor(@Inject(DOCUMENT) private document: Document) {
    const savedLang = localStorage.getItem('lang') as 'en' | 'ru' | 'kk';
    if (savedLang && (savedLang === 'en' || savedLang === 'ru' || savedLang === 'kk')) {
      this.currentLang.next(savedLang);
    }
    this.document.documentElement.lang = this.currentLang.value;
  }

  setLanguage(lang: 'en' | 'ru' | 'kk'): void {
    this.currentLang.next(lang);
    localStorage.setItem('lang', lang);
    this.document.documentElement.lang = lang;
  }

  getCurrentLang(): 'en' | 'ru' | 'kk' {
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

  inLanguage(key: string, language: 'en' | 'ru' | 'kk'): string {
    let value: any = translations[language];
    for (const part of key.split('.')) value = value?.[part];
    return typeof value === 'string' ? value : key;
  }

  t(key: string): string {
    return this.translate(key);
  }

  catalogLabel(value: string): string {
    const key = catalogTranslationKeys[value];
    if (!key) return value;
    const translated = this.t(key);
    return translated === key ? value : translated;
  }
}
