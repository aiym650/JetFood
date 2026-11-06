import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { LanguageSwitcher } from '../shared/language-switcher/language-switcher';
import { I18nService } from '../i18n/i18n.service';

@Component({
  selector: 'app-landing',
  imports: [CommonModule, LanguageSwitcher],
  templateUrl: './landing.html',
  styleUrl: './landing.css',
})
export class LandingComponent {
  constructor(private router: Router, public i18n: I18nService) {}

  goToLogin(): void {
    this.router.navigate(['/login']);
  }

  goToRegister(): void {
    this.router.navigate(['/register']);
  }
}
