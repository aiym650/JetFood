from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from users.models import Notification
from ...models import ReviewReminder


class Command(BaseCommand):
    help = "Send review reminders for delivered orders."

    def handle(self, *args, **options):
        sent = 0
        reminders = ReviewReminder.objects.filter(sent_at__isnull=True, due_at__lte=timezone.now()).select_related("order", "order__customer")
        for reminder in reminders:
            with transaction.atomic():
                reminder = ReviewReminder.objects.select_for_update().get(pk=reminder.pk)
                if reminder.sent_at or hasattr(reminder.order, "review"):
                    reminder.sent_at = timezone.now()
                    reminder.save(update_fields=["sent_at"])
                    continue
                order = reminder.order
                Notification.objects.create(
                    user=order.customer,
                    notification_type="order_delivered",
                    title="Оцените ваш заказ",
                    message=f'Поделитесь впечатлением о заказе {order.order_number}.',
                    link=f"/orders?orderId={order.id}",
                )
                if order.customer.email:
                    send_mail(
                        "Оцените ваш заказ",
                        f"Поделитесь впечатлением о заказе {order.order_number}.",
                        None,
                        [order.customer.email],
                        fail_silently=True,
                    )
                reminder.sent_at = timezone.now()
                reminder.save(update_fields=["sent_at"])
                sent += 1
        self.stdout.write(self.style.SUCCESS(f"Sent {sent} review reminders"))
