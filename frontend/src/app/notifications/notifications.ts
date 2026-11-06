import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { map } from 'rxjs';
import { ApiListResponse, getApiListResults } from '../shared/api-list';
import { I18nService } from '../i18n/i18n.service';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

@Component({
  selector: 'app-notifications',
  imports: [CommonModule],
  templateUrl: './notifications.html',
  styleUrl: './notifications.css',
})
export class NotificationsComponent implements OnInit {
  notifications: any[] = [];
  loading = false;
  error = '';
  unreadCount = 0;
  updating = false;

  constructor(
    private http: HttpClient,
    private changeDetector: ChangeDetectorRef,
    public i18n: I18nService
  ) {
    this.i18n.currentLang$.pipe(takeUntilDestroyed()).subscribe(() => this.changeDetector.markForCheck());
  }

  ngOnInit(): void {
    this.loadNotifications();
  }

  loadNotifications(): void {
    this.loading = true;
    this.error = '';
    this.http.get<ApiListResponse<any>>('http://localhost:8000/api/auth/notifications/').pipe(
      map(getApiListResults)
    ).subscribe({
      next: (data: any) => {
        this.notifications = data;
        this.unreadCount = this.notifications.filter((n: any) => !n.is_read).length;
        this.loading = false;
        this.changeDetector.markForCheck();
      },
      error: () => {
        this.error = this.i18n.t('notificationsLoadFailed');
        this.loading = false;
        this.changeDetector.markForCheck();
      }
    });
  }

  markAsRead(notificationId: number): void {
    this.updating = true;
    this.error = '';
    this.http.put(`http://localhost:8000/api/auth/notifications/${notificationId}/`, {}).subscribe({
      next: () => {
        this.updating = false;
        this.loadNotifications();
        this.changeDetector.markForCheck();
      },
      error: () => {
        this.error = this.i18n.t('markNotificationFailed');
        this.updating = false;
        this.changeDetector.markForCheck();
      }
    });
  }

  markAllAsRead(): void {
    this.updating = true;
    this.error = '';
    this.http.post('http://localhost:8000/api/auth/notifications/mark-all-read/', {}).subscribe({
      next: () => {
        this.updating = false;
        this.loadNotifications();
        this.changeDetector.markForCheck();
      },
      error: () => {
        this.error = this.i18n.t('markNotificationsFailed');
        this.updating = false;
        this.changeDetector.markForCheck();
      }
    });
  }

  clearAll(): void {
    if (this.notifications.length > 0 && confirm(this.i18n.t('confirmClearNotifications'))) {
      this.updating = true;
      this.error = '';
      this.http.delete('http://localhost:8000/api/auth/notifications/clear-all/').subscribe({
        next: () => {
          this.updating = false;
          this.loadNotifications();
          this.changeDetector.markForCheck();
        },
        error: () => {
          this.error = this.i18n.t('clearNotificationsFailed');
          this.updating = false;
          this.changeDetector.markForCheck();
        }
      });
    }
  }
}
