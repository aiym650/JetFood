from django.urls import path

from .views import SupportCaseListCreateView, support_case_message, support_case_detail, retry_reply, faq

urlpatterns = [
    path('faq/', faq, name='support-faq'),
    path('cases/<int:case_id>/', support_case_detail, name='support-case-detail'),
    path('cases/<int:case_id>/retry/', retry_reply, name='support-retry'),
    path('cases/', SupportCaseListCreateView.as_view(), name='support-case-list'),
    path('cases/<int:case_id>/messages/', support_case_message, name='support-case-messages'),
]
