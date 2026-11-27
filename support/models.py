from django.conf import settings
from django.db import models


class SupportCase(models.Model):
    ai_busy_until = models.DateTimeField(null=True, blank=True, editable=False)
    language = models.CharField(max_length=2, choices=[('ru', 'Русский'), ('kk', 'Қазақша'), ('en', 'English')], default='en')
    operator_requested = models.BooleanField(default=False)
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In progress'),
        ('waiting_for_customer', 'Waiting for customer'),
        ('resolved', 'Resolved'),
    ]

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='support_cases',
    )
    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='support_cases',
    )
    order_number = models.CharField(max_length=50)
    issue_description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    resolution = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at', '-id']

    def __str__(self):
        return f'Support case #{self.pk} for order {self.order_number}'


class SupportMessage(models.Model):
    source = models.CharField(max_length=16, blank=True, default='', choices=[('ai', 'AI provider'), ('catalog', 'JetFood catalog'), ('facts', 'Verified JetFood data')])
    request_id = models.CharField(max_length=100, null=True, blank=True)
    SENDER_CHOICES = [
        ('customer', 'Customer'),
        ('assistant', 'Assistant'),
        ('staff', 'Support staff'),
    ]

    support_case = models.ForeignKey(
        SupportCase,
        on_delete=models.CASCADE,
        related_name='messages',
    )
    sender = models.CharField(max_length=20, choices=SENDER_CHOICES)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'id']
        constraints = [models.UniqueConstraint(fields=['support_case', 'request_id'], name='support_message_request_unique')]

    def __str__(self):
        return f'{self.sender} message for support case {self.support_case_id}'


class FAQ(models.Model):
    slug = models.SlugField(unique=True)
    is_active = models.BooleanField(default=True)
    question_ru = models.CharField(max_length=300)
    answer_ru = models.TextField()
    question_kk = models.CharField(max_length=300)
    answer_kk = models.TextField()
    question_en = models.CharField(max_length=300)
    answer_en = models.TextField()

    def __str__(self):
        return self.question_en
