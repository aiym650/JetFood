import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { NotificationsComponent } from './notifications';
import { I18nService } from '../i18n/i18n.service';

describe('NotificationsComponent', () => {
  let fixture: ComponentFixture<NotificationsComponent>;
  let component: NotificationsComponent;
  let httpTesting: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [NotificationsComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    TestBed.inject(I18nService).setLanguage('ru');
    fixture = TestBed.createComponent(NotificationsComponent);
    component = fixture.componentInstance;
    httpTesting = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
  });

  afterEach(() => httpTesting.verify());

  it('displays an actionable error when marking a notification as read fails', () => {
    httpTesting.expectOne('http://localhost:8000/api/auth/notifications/').flush([]);

    component.markAsRead(42);
    httpTesting.expectOne('http://localhost:8000/api/auth/notifications/42/').flush(
      { detail: 'Request failed' },
      { status: 500, statusText: 'Server Error' }
    );

    expect(component.error).toContain('Не удалось отметить уведомление');
    expect(component.updating).toBe(false);
  });

  it('does not send a clear request when there are no notifications', () => {
    httpTesting.expectOne('http://localhost:8000/api/auth/notifications/').flush([]);

    component.clearAll();

    expect(component.notifications).toEqual([]);
    httpTesting.expectNone('http://localhost:8000/api/auth/notifications/clear-all/');
  });

  it('renders a delivery status notification with a link to the order', () => {
    httpTesting.expectOne('http://localhost:8000/api/auth/notifications/').flush([{
      id: 17,
      notification_type: 'order_status',
      title: 'Delivery status updated',
      message: 'Order ORD-17 status is now On the way.',
      is_read: false,
      link: '/orders?orderId=17',
      created_at: '2026-11-09T10:00:00Z',
    }]);
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('Delivery status updated');
    expect(fixture.nativeElement.textContent).toContain('On the way');
    expect(fixture.nativeElement.querySelector('a')?.getAttribute('href')).toBe('/orders?orderId=17');
  });
});
