import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { Addresses, DeliveryAddress, DeliveryAddressInput } from '../addresses';
import { Auth, AuthUser } from '../auth';
import { I18nService } from '../i18n/i18n.service';

interface ProfileInput {
  username: string;
  email: string;
  phone: string;
  address: string;
}

interface AddressForm extends DeliveryAddressInput {}

@Component({
  selector: 'app-profile',
  imports: [CommonModule, FormsModule],
  templateUrl: './profile.html',
  styleUrl: './profile.css',
})
export class ProfilePage implements OnInit {
  profile: ProfileInput = { username: '', email: '', phone: '', address: '' };
  addresses: DeliveryAddress[] = [];
  addressForm: AddressForm = this.emptyAddressForm();
  passwordForm = { old_password: '', new_password: '', confirm_password: '' };
  accountPassword = '';
  editingAddressId: number | null = null;
  currentUser: AuthUser | null = null;
  profileLoading = false;
  addressesLoading = false;
  profileSaving = false;
  passwordSaving = false;
  addressSaving = false;
  accountDeleting = false;
  profileMessage = '';
  profileError = '';
  passwordMessage = '';
  passwordError = '';
  addressMessage = '';
  addressError = '';
  accountError = '';

  get isCustomer(): boolean {
    return this.currentUser?.role === 'customer';
  }

  constructor(
    private http: HttpClient,
    private addressesService: Addresses,
    private auth: Auth,
    private router: Router,
    private changeDetector: ChangeDetectorRef,
    public i18n: I18nService,
  ) {}

  ngOnInit(): void {
    this.currentUser = this.auth.getCurrentUser();
    this.loadProfile();
    this.loadAddresses();
  }

  loadProfile(): void {
    this.profileLoading = true;
    this.profileError = '';
    this.http.get<AuthUser & ProfileInput>('http://localhost:8000/api/auth/profile/').subscribe({
      next: (user) => {
        this.profile = {
          username: user.username,
          email: user.email,
          phone: user.phone ?? '',
          address: user.address ?? '',
        };
        this.currentUser = user;
        this.auth.updateCurrentUser(user);
        this.profileLoading = false;
        this.changeDetector.markForCheck();
      },
      error: (error: unknown) => {
        this.profileError = this.errorMessage(error, 'profileLoadFailed');
        this.profileLoading = false;
        this.changeDetector.markForCheck();
      },
    });
  }

  saveProfile(): void {
    this.profileSaving = true;
    this.profileError = '';
    this.profileMessage = '';
    this.http.patch<AuthUser>('http://localhost:8000/api/auth/profile/', this.profile).subscribe({
      next: (user) => {
        this.currentUser = user;
        this.auth.updateCurrentUser(user);
        this.profileMessage = this.i18n.t('profileSaved');
        this.profileSaving = false;
        this.changeDetector.markForCheck();
      },
      error: (error: unknown) => {
        this.profileError = this.errorMessage(error, 'profileSaveFailed');
        this.profileSaving = false;
        this.changeDetector.markForCheck();
      },
    });
  }

  loadAddresses(): void {
    this.addressesLoading = true;
    this.addressError = '';
    this.addressesService.getAddresses().subscribe({
      next: (addresses) => {
        this.addresses = addresses;
        this.addressesLoading = false;
        this.changeDetector.markForCheck();
      },
      error: (error: unknown) => {
        this.addressError = this.errorMessage(error, 'addressesLoadFailed');
        this.addressesLoading = false;
        this.changeDetector.markForCheck();
      },
    });
  }

  saveAddress(): void {
    this.addressSaving = true;
    this.addressError = '';
    this.addressMessage = '';
    const request = this.editingAddressId
      ? this.addressesService.updateAddress(this.editingAddressId, this.addressForm)
      : this.addressesService.createAddress(this.addressForm);
    request.subscribe({
      next: () => {
        this.resetAddressForm();
        this.addressMessage = this.i18n.t('addressSaved');
        this.addressSaving = false;
        this.loadAddresses();
        this.changeDetector.markForCheck();
      },
      error: (error: unknown) => {
        this.addressError = this.errorMessage(error, 'addressSaveFailed');
        this.addressSaving = false;
        this.changeDetector.markForCheck();
      },
    });
  }

  editAddress(address: DeliveryAddress): void {
    this.editingAddressId = address.id;
    this.addressForm = {
      label: address.label,
      recipient_name: address.recipient_name,
      phone: address.phone,
      address_line: address.address_line,
      city: address.city,
      postal_code: address.postal_code,
      instructions: address.instructions,
      is_default: address.is_default,
    };
  }

  setDefaultAddress(address: DeliveryAddress): void {
    this.addressesService.updateAddress(address.id, {
      label: address.label,
      recipient_name: address.recipient_name,
      phone: address.phone,
      address_line: address.address_line,
      city: address.city,
      postal_code: address.postal_code,
      instructions: address.instructions,
      is_default: true,
    }).subscribe({
      next: () => this.loadAddresses(),
      error: (error: unknown) => {
        this.addressError = this.errorMessage(error, 'addressSaveFailed');
        this.changeDetector.markForCheck();
      },
    });
  }

  deleteAddress(address: DeliveryAddress): void {
    if (!confirm(this.i18n.t('confirmDeleteAddress'))) return;
    this.addressesService.deleteAddress(address.id).subscribe({
      next: () => {
        if (this.editingAddressId === address.id) this.resetAddressForm();
        this.loadAddresses();
      },
      error: (error: unknown) => {
        this.addressError = this.errorMessage(error, 'addressDeleteFailed');
        this.changeDetector.markForCheck();
      },
    });
  }

  changePassword(): void {
    this.passwordMessage = '';
    this.passwordError = '';
    if (this.passwordForm.new_password !== this.passwordForm.confirm_password) {
      this.passwordError = this.i18n.t('passwordsNotMatch');
      return;
    }

    this.passwordSaving = true;
    this.http.post('http://localhost:8000/api/auth/change-password/', {
      old_password: this.passwordForm.old_password,
      new_password: this.passwordForm.new_password,
    }).subscribe({
      next: () => {
        this.passwordForm = { old_password: '', new_password: '', confirm_password: '' };
        this.passwordMessage = this.i18n.t('passwordChanged');
        this.passwordSaving = false;
        this.changeDetector.markForCheck();
      },
      error: (error: unknown) => {
        this.passwordError = this.errorMessage(error, 'passwordChangeFailed');
        this.passwordSaving = false;
        this.changeDetector.markForCheck();
      },
    });
  }

  deleteAccount(): void {
    if (!confirm(this.i18n.t('confirmDeleteAccount'))) return;
    this.accountDeleting = true;
    this.accountError = '';
    this.http.delete('http://localhost:8000/api/auth/account/', {
      body: { password: this.accountPassword },
    }).subscribe({
      next: () => {
        this.auth.clearLocalSession();
        this.router.navigate(['/landing']);
      },
      error: (error: unknown) => {
        this.accountError = this.errorMessage(error, 'accountDeleteFailed');
        this.accountDeleting = false;
        this.changeDetector.markForCheck();
      },
    });
  }

  resetAddressForm(): void {
    this.editingAddressId = null;
    this.addressForm = this.emptyAddressForm();
  }

  private emptyAddressForm(): AddressForm {
    return {
      label: 'Home',
      recipient_name: '',
      phone: '',
      address_line: '',
      city: '',
      postal_code: '',
      instructions: '',
      is_default: false,
    };
  }

  private errorMessage(error: unknown, fallbackKey: string): string {
    if (typeof error === 'object' && error !== null && 'error' in error) {
      const body = (error as { error?: unknown }).error;
      if (typeof body === 'object' && body !== null && 'detail' in body) {
        const detail = (body as { detail?: unknown }).detail;
        if (typeof detail === 'string') return detail;
      }
      if (typeof body === 'object' && body !== null) {
        const firstValue = Object.values(body).find(value => typeof value === 'string' || Array.isArray(value));
        if (typeof firstValue === 'string') return firstValue;
        if (Array.isArray(firstValue) && typeof firstValue[0] === 'string') return firstValue[0];
      }
    }
    return this.i18n.t(fallbackKey);
  }
}
