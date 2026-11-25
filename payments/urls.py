from django.urls import path

from .views import (
    PaymentListView,
    confirm_cash_payment,
    pay_order,
    payment_receipt,
    refund_payment,
)

from . import hosted

urlpatterns = [
    path("config/", hosted.configuration),
    path("result.php", hosted.result_notify),
    path("<int:order_id>/checkout/", hosted.checkout),
    path("<int:order_id>/verify/", hosted.verify),
    path('', PaymentListView.as_view(), name='payment-list'),
    path('<int:order_id>/pay/', pay_order, name='pay-order'),
    path('<int:payment_id>/receipt/', payment_receipt, name='payment-receipt'),
    path('<int:payment_id>/confirm-cash/', confirm_cash_payment, name='confirm-cash-payment'),
    path('<int:payment_id>/refund/', refund_payment, name='refund-payment'),
]
