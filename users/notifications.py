from .models import Notification


def notify_order_created(order):
    Notification.objects.create(
        user=order.customer,
        notification_type='order_created',
        title='Order received',
        message=f'Your order {order.order_number} has been received.',
        link=f'/orders?orderId={order.id}',
    )


def notify_order_status(order):
    recipients = [order.customer]
    if order.delivery_person_id and order.delivery_person_id != order.customer_id:
        recipients.append(order.delivery_person)
    for recipient in recipients:
        Notification.objects.create(
            user=recipient,
            notification_type='order_status',
            title='Delivery status updated',
            message=f'Order {order.order_number} status is now {order.get_status_display()}.',
            link=f'/orders?orderId={order.id}',
        )


def notify_courier_assignment(order):
    recipients = [order.customer, order.delivery_person]
    for recipient in recipients:
        if recipient:
            Notification.objects.create(
                user=recipient,
                notification_type='order_updated',
                title='Courier assigned',
                message=f'Courier {order.delivery_person.username} was assigned to order {order.order_number}.',
                link=f'/orders?orderId={order.id}',
            )
