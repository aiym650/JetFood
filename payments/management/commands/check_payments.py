import json
from django.conf import settings
from django.core.management.base import BaseCommand
from payments.configuration import configuration_status


class Command(BaseCommand):
    help = 'Check local payment setup without revealing secrets, contacting the provider or creating a charge.'

    def add_arguments(self, parser):
        parser.add_argument('--json', action='store_true')

    def handle(self, *args, **options):
        result = {**configuration_status(), 'test_mode': settings.FREEDOMPAY_TEST_MODE}
        if options['json']:
            self.stdout.write(json.dumps(result))
            return
        self.stdout.write('Payment mode: ' + ('TEST' if result['test_mode'] else 'LIVE'))
        self.stdout.write('Local configuration: ' + ('READY' if result['configured'] else 'NOT READY'))
        for name in result['missing']:
            self.stdout.write(f'Missing: {name}')
        for problem in result['problems']:
            self.stdout.write(problem)
        self.stdout.write('Provider credentials have NOT been verified; no payment was created.')
        if result['configured']:
            self.stdout.write(f"Callback: {settings.PAYMENTS_PUBLIC_URL.rstrip('/')}/api/payments/result.php")
        else:
            self.stdout.write('After receiving test credentials, run: py manage.py setup_test_payments')
