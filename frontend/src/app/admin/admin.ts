import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { ActivatedRoute } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { map } from 'rxjs';
import { ApiListResponse, getApiListResults } from '../shared/api-list';
import { I18nService } from '../i18n/i18n.service';

@Component({
  selector: 'app-admin',
  imports: [CommonModule, FormsModule],
  templateUrl: './admin.html',
  styleUrl: './admin.css',
})
export class AdminComponent implements OnInit {
  users: any[] = [];
  selectedUser: any = null;
  showUserModal = false;
  loading = false;
  error = '';

  newUser = {
    username: '',
    email: '',
    password: '',
    role: 'customer',
    phone: ''
  };

  roles = ['admin', 'manager', 'analyst', 'delivery', 'customer'];

  constructor(
    private http: HttpClient,
    private route: ActivatedRoute,
    private changeDetector: ChangeDetectorRef,
    public i18n: I18nService
  ) {
    this.i18n.currentLang$
      .pipe(takeUntilDestroyed())
      .subscribe(() => this.changeDetector.markForCheck());
  }

  ngOnInit(): void {
    this.loadUsers();
  }

  loadUsers(): void {
    this.loading = true;
    this.http.get<ApiListResponse<any>>('http://localhost:8000/api/auth/users/').pipe(
      map(getApiListResults)
    ).subscribe({
      next: (data: any) => {
        this.users = data;
        this.loading = false;
        const userId = Number(this.route.snapshot.queryParamMap.get('userId'));
        const user = this.users.find((item) => item.id === userId);
        if (user) {
          this.openUserModal(user);
        }
        this.changeDetector.markForCheck();
      },
      error: () => {
        this.error = this.i18n.t('usersLoadFailed');
        this.loading = false;
        this.changeDetector.markForCheck();
      }
    });
  }

  openUserModal(user?: any): void {
    if (user) {
      this.selectedUser = { ...user };
    } else {
      this.selectedUser = { ...this.newUser };
    }
    this.showUserModal = true;
  }

  closeUserModal(): void {
    this.showUserModal = false;
    this.selectedUser = null;
  }

  saveUser(): void {
    if (this.selectedUser.id) {
      this.updateUser();
    } else {
      this.createUser();
    }
  }

  createUser(): void {
    this.http.post('http://localhost:8000/api/auth/users/create/', this.selectedUser).subscribe({
      next: () => {
        this.closeUserModal();
        this.loadUsers();
        this.changeDetector.markForCheck();
      },
      error: () => {
        this.error = this.i18n.t('userCreateFailed');
        this.changeDetector.markForCheck();
      }
    });
  }

  updateUser(): void {
    const { role, ...userData } = this.selectedUser;
    this.http.put(`http://localhost:8000/api/auth/users/${this.selectedUser.id}/`, userData).subscribe({
      next: () => {
        this.http.post(`http://localhost:8000/api/auth/users/${this.selectedUser.id}/role/`, { role }).subscribe({
          next: () => {
            this.closeUserModal();
            this.loadUsers();
          },
          error: () => {
            this.error = this.i18n.t('roleUpdateFailed');
            this.changeDetector.markForCheck();
          }
        });
      },
      error: () => {
        this.error = this.i18n.t('userUpdateFailed');
        this.changeDetector.markForCheck();
      }
    });
  }

  deleteUser(userId: number): void {
    if (confirm(this.i18n.t('confirmDeleteUser'))) {
      this.http.delete(`http://localhost:8000/api/auth/users/${userId}/`).subscribe({
        next: () => {
          this.loadUsers();
          this.changeDetector.markForCheck();
        },
        error: () => {
          this.error = this.i18n.t('userDeleteFailed');
          this.changeDetector.markForCheck();
        }
      });
    }
  }

  updateUserRole(userId: number, newRole: string): void {
    this.http.post(`http://localhost:8000/api/auth/users/${userId}/role/`, { role: newRole }).subscribe({
      next: () => {
        this.loadUsers();
        this.changeDetector.markForCheck();
      },
      error: () => {
        this.error = this.i18n.t('roleUpdateFailed');
        this.changeDetector.markForCheck();
      }
    });
  }
}
