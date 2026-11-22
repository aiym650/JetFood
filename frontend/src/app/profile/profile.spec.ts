import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpClient } from '@angular/common/http';
import { provideRouter } from '@angular/router';
import { of } from 'rxjs';
import { vi } from 'vitest';

import { Addresses, DeliveryAddress } from '../addresses';
import { Auth } from '../auth';
import { I18nService } from '../i18n/i18n.service';
import { ProfilePage } from './profile';

describe('ProfilePage', () => {
  let fixture: ComponentFixture<ProfilePage>;
  let component: ProfilePage;
  const savedAddress: DeliveryAddress = {
    id: 11,
    label: 'Home',
    recipient_name: 'Customer',
    phone: '+77000000000',
    address_line: '10 Main Street',
    city: 'Almaty',
    postal_code: '050000',
    instructions: '',
    is_default: false,
  };
  const addressesApi = {
    getAddresses: vi.fn(() => of([])),
    createAddress: vi.fn((address: Omit<DeliveryAddress, 'id'>) => of({ ...address, id: 12 })),
    updateAddress: vi.fn((_id: number, address: Omit<DeliveryAddress, 'id'>) => of({ ...address, id: 11 })),
    deleteAddress: vi.fn(() => of(undefined)),
  };
  const profileApi = {
    get: vi.fn((_url: string) => of({
      id: 7,
      username: 'customer',
      email: 'customer@example.com',
      role: 'customer',
      phone: '',
      address: '',
    })),
    patch: vi.fn((_url: string, profile: { username: string; email: string; phone: string; address: string }) =>
      of({ ...profile, id: 7, role: 'customer' })),
    post: vi.fn((_url: string, _body: { old_password: string; new_password: string }) => of({})),
    delete: vi.fn((_url: string, _options: unknown) => of({})),
  };

  beforeEach(async () => {
    addressesApi.getAddresses.mockClear();
    addressesApi.createAddress.mockClear();
    addressesApi.updateAddress.mockClear();
    addressesApi.deleteAddress.mockClear();
    profileApi.get.mockClear();
    profileApi.patch.mockClear();
    profileApi.post.mockClear();
    profileApi.delete.mockClear();
    await TestBed.configureTestingModule({
      imports: [ProfilePage],
      providers: [
        provideRouter([]),
        {
          provide: Auth,
          useValue: {
            getCurrentUser: () => ({ id: 7, username: 'customer', email: 'customer@example.com', role: 'customer' }),
            updateCurrentUser: vi.fn(),
            clearLocalSession: vi.fn(),
          },
        },
        { provide: Addresses, useValue: addressesApi },
        {
          provide: HttpClient,
          useValue: profileApi,
        },
      ],
    }).compileComponents();

    TestBed.inject(I18nService).setLanguage('en');
    fixture = TestBed.createComponent(ProfilePage);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('loads the profile and account settings', () => {
    expect(component.profile.username).toBe('customer');
    expect(fixture.nativeElement.textContent).toContain('Delivery addresses');
    expect(fixture.nativeElement.textContent).toContain('Change password');
  });

  it('keeps profile fields read-only until editing and restores values on cancel', () => {
    const username = fixture.nativeElement.querySelector('[name="username"]') as HTMLInputElement;
    expect(username.readOnly).toBe(true);

    component.startProfileEdit();
    fixture.detectChanges();
    expect(username.readOnly).toBe(false);

    component.profile.username = 'temporary';
    component.cancelProfileEdit();
    expect(component.profile.username).toBe('customer');
    expect(component.profileEditing).toBe(false);
  });

  it('saves profile changes through the existing profile endpoint', () => {
    component.profile = {
      username: 'updated-customer',
      email: 'updated@example.com',
      phone: '+77000000000',
      address: '10 Main Street',
    };

    component.saveProfile();

    expect(profileApi.patch).toHaveBeenCalledWith(
      'http://localhost:8000/api/auth/profile/',
      component.profile,
    );
    expect(component.profileEditing).toBe(false);
    expect(component.profileMessage).toBe('Profile saved.');
  });

  it('creates and edits saved addresses through the existing address service', () => {
    component.openAddressForm();
    expect(component.addressFormOpen).toBe(true);
    const addressToCreate: Omit<DeliveryAddress, 'id'> = {
      label: savedAddress.label,
      recipient_name: savedAddress.recipient_name,
      phone: savedAddress.phone,
      address_line: savedAddress.address_line,
      city: savedAddress.city,
      postal_code: savedAddress.postal_code,
      instructions: savedAddress.instructions,
      is_default: savedAddress.is_default,
    };
    component.addressForm = { ...addressToCreate };
    const newAddress = { ...component.addressForm };
    component.saveAddress();
    expect(addressesApi.createAddress).toHaveBeenCalledWith(newAddress);
    expect(component.addressFormOpen).toBe(false);

    component.editAddress(savedAddress);
    expect(component.editingAddressId).toBe(savedAddress.id);
    expect(component.addressFormOpen).toBe(true);
    component.addressForm.instructions = 'Call on arrival';
    const editedAddress = { ...component.addressForm };
    component.saveAddress();
    expect(addressesApi.updateAddress).toHaveBeenCalledWith(savedAddress.id, editedAddress);
    expect(component.addressFormOpen).toBe(false);
  });

  it('rejects mismatched password confirmation before making a request', () => {
    component.passwordForm = {
      old_password: 'old-password',
      new_password: 'new-password',
      confirm_password: 'different-password',
    };

    component.changePassword();

    expect(component.passwordError).toBe('Passwords do not match');
    expect(component.passwordSaving).toBe(false);
    expect(profileApi.post).not.toHaveBeenCalled();
  });

  it('changes the password through the existing endpoint and clears the form on success', () => {
    component.passwordForm = {
      old_password: 'old-password',
      new_password: 'new-password',
      confirm_password: 'new-password',
    };

    component.changePassword();

    expect(profileApi.post).toHaveBeenCalledWith(
      'http://localhost:8000/api/auth/change-password/',
      { old_password: 'old-password', new_password: 'new-password' },
    );
    expect(component.passwordForm.old_password).toBe('');
    expect(component.passwordMessage).toBe('Password changed successfully.');
  });

  it('keeps the existing default-address update action', () => {
    component.setDefaultAddress(savedAddress);

    expect(addressesApi.updateAddress).toHaveBeenCalledWith(savedAddress.id, {
      label: savedAddress.label,
      recipient_name: savedAddress.recipient_name,
      phone: savedAddress.phone,
      address_line: savedAddress.address_line,
      city: savedAddress.city,
      postal_code: savedAddress.postal_code,
      instructions: savedAddress.instructions,
      is_default: true,
    });
  });
});
