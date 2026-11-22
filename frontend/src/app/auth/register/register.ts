import { ChangeDetectorRef, Component, DestroyRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { Auth } from '../../auth';
import { LanguageSwitcher } from '../../shared/language-switcher/language-switcher';
import { I18nService } from '../../i18n/i18n.service';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

@Component({
  selector: 'app-register',
  imports: [CommonModule, FormsModule, RouterLink, LanguageSwitcher],
  templateUrl: './register.html',
  styleUrl: './register.css',
})
export class Register {
  username = '';
  email = '';
  password = '';
  confirmPassword = '';
  phone = '';
  errorMessage = '';
  loading = false;

  constructor(
    private auth: Auth,
    private router: Router,
    private changeDetector: ChangeDetectorRef,
    private destroyRef: DestroyRef,
    public i18n: I18nService
  ) {
    this.i18n.currentLang$.pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => this.changeDetector.markForCheck());
  }

  onSubmit(): void {
    if (this.loading) return;
    this.loading = true;
    this.errorMessage = '';
    this.username = this.username.trim();
    this.email = this.email.trim();
    this.phone = this.phone.trim();
    let validationKey = '';
    if (!this.username) validationKey = 'registrationFailedUsername';
    else if (!this.password) validationKey = 'registrationFailedPassword';
    else if (this.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(this.email)) validationKey = 'registrationFailedEmail';
    else if (this.phone && !/^\+?1?\d{9,15}$/.test(this.phone)) validationKey = 'registrationFailedPhone';
    if (validationKey) {
      this.errorMessage = this.i18n.t(validationKey);
      this.loading = false;
      return;
    }

    if (this.password !== this.confirmPassword) {
      this.errorMessage = this.i18n.t('passwordsNotMatch');
      this.loading = false;
      return;
    }

    if (this.password.length < 8) {
      this.errorMessage = this.i18n.t('passwordMinLength');
      this.loading = false;
      return;
    }

    this.auth.register({
      username: this.username,
      email: this.email,
      password: this.password,
      phone: this.phone
    }).subscribe({
      next: () => {
        this.loading = false;
        this.changeDetector.markForCheck();
        this.router.navigate(['/login']);
      },
      error: (error) => {
        this.loading = false;
        const fields = ['phone', 'email', 'username', 'password'];
        const field = fields.find(key => error.error && typeof error.error === 'object' && key in error.error);
        this.errorMessage = this.i18n.t(field
          ? 'registrationFailed' + field.charAt(0).toUpperCase() + field.slice(1)
          : 'registrationFailed');
        this.changeDetector.markForCheck();
      }
    });
  }
}
