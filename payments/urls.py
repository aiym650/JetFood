from django.urls import path

from .views import PaymentListView, confirm_cash_payment, refund_payment

urlpatterns = [
    path('', PaymentListView.as_view(), name='payment-list'),
    path('<int:payment_id>/confirm-cash/', confirm_cash_payment, name='confirm-cash-payment'),
    path('<int:payment_id>/refund/', refund_payment, name='refund-payment'),
]
