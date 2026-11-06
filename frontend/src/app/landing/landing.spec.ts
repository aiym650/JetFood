import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { LandingComponent } from './landing';

describe('LandingComponent', () => {
  let fixture: ComponentFixture<LandingComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [LandingComponent],
      providers: [provideRouter([])],
    }).compileComponents();

    fixture = TestBed.createComponent(LandingComponent);
    fixture.detectChanges();
  });

  it('switches landing content and document language', () => {
    const component = fixture.componentInstance;
    component.i18n.setLanguage('en');
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Food delivered in 30 minutes');
    expect(document.documentElement.lang).toBe('en');

    component.i18n.setLanguage('ru');
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Доставка еды за 30 минут');
    expect(document.documentElement.lang).toBe('ru');
  });
});
