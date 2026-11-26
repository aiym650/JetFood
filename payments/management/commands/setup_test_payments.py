from getpass import getpass
import sys
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from dotenv import set_key
from payments.configuration import configuration_status


class Command(BaseCommand):
    help = 'Enter issued Freedom Pay TEST credentials locally and save to ignored .env. No payment or external account is created.'

    def handle(self, *args, **options):
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            raise CommandError('Run this command in an interactive local terminal; secret input through pipes is disabled.')
        self.stdout.write('Use TEST credentials issued by Freedom Pay. The payment secret will not be displayed.')
        try:
            merchant = input('Test merchant ID: ').strip()
            secret = getpass('Test payment secret (hidden): ').strip()
            public_url = input('Public backend HTTPS origin: ').strip().rstrip('/')
        except (EOFError, KeyboardInterrupt):
            raise CommandError('Setup cancelled; .env was not changed.') from None
        values = {'FREEDOMPAY_MERCHANT_ID': merchant, 'FREEDOMPAY_SECRET_KEY': secret, 'PAYMENTS_PUBLIC_URL': public_url}
        status = configuration_status(values)
        if not status['configured']:
            raise CommandError('Setup was not saved. ' + '; '.join(['Missing: ' + name for name in status['missing']] + status['problems']))
        values['FREEDOMPAY_TEST_MODE'] = '1'
        values['PAYMENTS_RETURN_URL'] = settings.PAYMENTS_RETURN_URL
        path = settings.BASE_DIR / '.env'
        for name, value in values.items():
            set_key(path, name, value, quote_mode='always', encoding='utf-8')
        self.stdout.write(self.style.SUCCESS('Saved local .env in TEST mode. Restart Django. Secrets were not printed.'))
        self.stdout.write(f'Callback: {public_url}/api/payments/result.php')
        self.stdout.write('Next: py manage.py check_payments')
