import { ChangeDetectorRef, Component, DestroyRef, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { map } from 'rxjs';
import { ApiListResponse, getApiListResults } from '../shared/api-list';
import { I18nService } from '../i18n/i18n.service';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { timer } from 'rxjs';

interface NotificationRecord {
  id: number;
  notification_type: string;
  title: string;
  message: string;
  is_read: boolean;
  link: string;
  created_at: string;
}

@Component({
  selector: 'app-notifications',
  imports: [CommonModule],
  templateUrl: './notifications.html',
  styleUrl: './notifications.css',
})
export class NotificationsComponent implements OnInit {
  notifications: NotificationRecord[] = [];
  loading = false;
  error = '';
  unreadCount = 0;
  updating = false;

  constructor(
    private http: HttpClient,
    private changeDetector: ChangeDetectorRef,
    private destroyRef: DestroyRef,
    public i18n: I18nService
  ) {
    this.i18n.currentLang$.pipe(takeUntilDestroyed()).subscribe(() => this.changeDetector.markForCheck());
  }

  ngOnInit(): void {
    this.loadNotifications();
    timer(30_000, 30_000)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => {
        if (!this.loading && !this.updating) this.loadNotifications();
      });
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

  notificationTitle(notification: NotificationRecord): string {
    if (this.i18n.getCurrentLang() !== 'kk') return notification.title;

    switch (notification.notification_type) {
      case 'order_created':
        return this.i18n.t('notificationTitles.orderCreated');
      case 'order_status':
        return this.i18n.t('notificationTitles.orderStatus');
      case 'order_updated':
        return this.i18n.t('notificationTitles.courierAssigned');
      case 'order_delivered':
        return this.i18n.t('notificationTitles.reviewReminder');
      case 'system':
        if (notification.title === 'New restaurant review') return this.i18n.t('notificationTitles.newReview');
        if (notification.title === 'Restaurant replied') return this.i18n.t('notificationTitles.restaurantReply');
        break;
    }

    return notification.title;
  }

  notificationMessage(notification: NotificationRecord): string {
    if (this.i18n.getCurrentLang() !== 'kk') return notification.message;

    const orderNumber = notification.message.match(/(?:order|заказ[а-я]*)\s+([A-Z0-9-]+)/i)?.[1];
    switch (notification.notification_type) {
      case 'order_created':
        return orderNumber
          ? this.i18n.t('notificationMessages.orderCreated').replace('{orderNumber}', orderNumber)
          : notification.message;
      case 'order_status': {
        const status = notification.message.match(/status is now (.+)\.$/i)?.[1]?.toLowerCase();
        if (!orderNumber || !status) return notification.message;
        const statusKeys: Record<string, string> = {
          pending: 'pending',
          confirmed: 'confirmed',
          preparing: 'preparing',
          'ready for pickup': 'ready_for_pickup',
          delivering: 'delivering',
          'on the way': 'delivering',
          delivered: 'delivered',
          cancelled: 'cancelled',
        };
        const statusKey = statusKeys[status];
        if (!statusKey) return notification.message;
        const translatedStatus = this.i18n.t(`orderStatuses.${statusKey}`);
        return this.i18n.t('notificationMessages.orderStatus')
          .replace('{orderNumber}', orderNumber)
          .replace('{status}', translatedStatus);
      }
      case 'order_updated': {
        const assignment = notification.message.match(/^Courier (.+) was assigned to order ([A-Z0-9-]+)\.$/i);
        return assignment
          ? this.i18n.t('notificationMessages.courierAssigned')
            .replace('{courier}', assignment[1])
            .replace('{orderNumber}', assignment[2])
          : notification.message;
      }
      case 'order_delivered':
        return orderNumber
          ? this.i18n.t('notificationMessages.reviewReminder').replace('{orderNumber}', orderNumber)
          : notification.message;
      case 'system':
        if (notification.title === 'New restaurant review') {
          const restaurantName = notification.message.match(/^A new review was submitted for (.+)\.$/i)?.[1];
          return restaurantName
            ? this.i18n.t('notificationMessages.newReview').replace('{restaurant}', restaurantName)
            : notification.message;
        }
        if (notification.title === 'Restaurant replied') return this.i18n.t('notificationMessages.restaurantReply');
        break;
    }

    return notification.message;
  }
}
