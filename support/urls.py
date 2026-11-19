from django.urls import path

from .views import SupportCaseListCreateView, support_case_message

urlpatterns = [
    path('cases/', SupportCaseListCreateView.as_view(), name='support-case-list'),
    path('cases/<int:case_id>/messages/', support_case_message, name='support-case-messages'),
]
