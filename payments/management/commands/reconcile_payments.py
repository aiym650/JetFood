from django.core.management.base import BaseCommand
from payments.models import PaymentAttempt
from payments.hosted import reconcile
from payments.freedompay import ProviderUnavailable


class Command(BaseCommand):
    help = 'Reconcile up to 100 unresolved hosted attempts. Never creates a charge or releases an unknown reservation.'

    def handle(self, *args, **options):
        for attempt in PaymentAttempt.objects.filter(status__in=['unknown', 'pending']).order_by('id')[:100]:
            try:
                payment = reconcile(attempt)
                self.stdout.write(f'Attempt {attempt.pk}: {payment.status}')
            except ProviderUnavailable:
                self.stderr.write(f'Attempt {attempt.pk}: provider unavailable; preserved for retry')
