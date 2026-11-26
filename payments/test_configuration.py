import io
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.management import call_command, CommandError
from django.test import SimpleTestCase, override_settings
from dotenv import dotenv_values

from backend.environment import load_project_environment, public_origin_host
from .configuration import configuration_status


class PaymentConfigurationTests(SimpleTestCase):
    def test_dotenv_preserves_process_settings_and_literal_secret_characters(self):
        with TemporaryDirectory() as directory, patch.dict(os.environ, {'PAYMENT_EXISTING': 'process'}, clear=True):
            path = Path(directory) / '.env'
            path.write_text('PAYMENT_EXISTING=file\nPAYMENT_SECRET="literal${HOME}#value"\n', encoding='utf-8')
            load_project_environment(path)
            self.assertEqual(os.environ['PAYMENT_EXISTING'], 'process')
            self.assertEqual(os.environ['PAYMENT_SECRET'], 'literal${HOME}#value')

    def test_only_public_https_origin_is_accepted(self):
        self.assertEqual(public_origin_host('https://test.ngrok-free.app/'), 'test.ngrok-free.app')
        for invalid in ['http://test.example', 'https://localhost', 'https://127.0.0.1', 'https://192.168.1.2', 'https://test.example/api/payments/', 'https://user:secret@test.example', 'https://test.example?token=secret', 'https://*.ngrok-free.app']:
            with self.subTest(url=invalid), self.assertRaises(ValueError):
                public_origin_host(invalid)

    def test_readiness_does_not_claim_credentials_verified_or_reveal_them(self):
        secret = 'private-test-key'
        status = configuration_status({'FREEDOMPAY_MERCHANT_ID': '123', 'FREEDOMPAY_SECRET_KEY': secret, 'PAYMENTS_PUBLIC_URL': 'https://test.example'})
        self.assertTrue(status['configured'])
        self.assertFalse(status['credentials_verified'])
        self.assertNotIn(secret, json.dumps(status))

    @override_settings(FREEDOMPAY_MERCHANT_ID='', FREEDOMPAY_SECRET_KEY='', PAYMENTS_PUBLIC_URL='')
    def test_check_command_names_missing_settings_without_network(self):
        output = io.StringIO()
        with patch('payments.freedompay.urlopen') as network:
            call_command('check_payments', '--json', stdout=output)
        network.assert_not_called()
        result = json.loads(output.getvalue())
        self.assertFalse(result['configured'])
        self.assertIn('FREEDOMPAY_SECRET_KEY', result['missing'])

    def test_setup_preserves_other_settings_hides_secret_and_forces_test_mode(self):
        with TemporaryDirectory() as directory, override_settings(BASE_DIR=Path(directory)), patch('sys.stdin.isatty', return_value=True), patch('sys.stdout.isatty', return_value=True):
            path = Path(directory) / '.env'
            path.write_text('CUSTOM_SETTING=preserved\nFREEDOMPAY_TEST_MODE=0\n', encoding='utf-8')
            secret = "test${LITERAL}'secret"
            output = io.StringIO()
            with patch('builtins.input', side_effect=['123', 'https://test.example']), patch('payments.management.commands.setup_test_payments.getpass', return_value=secret):
                call_command('setup_test_payments', stdout=output)
            config = dotenv_values(path, interpolate=False)
            self.assertEqual(config['CUSTOM_SETTING'], 'preserved')
            self.assertEqual(config['FREEDOMPAY_SECRET_KEY'], secret)
            self.assertEqual(config['FREEDOMPAY_TEST_MODE'], '1')
            self.assertNotIn(secret, output.getvalue())

    def test_invalid_setup_does_not_change_existing_file(self):
        with TemporaryDirectory() as directory, override_settings(BASE_DIR=Path(directory)), patch('sys.stdin.isatty', return_value=True), patch('sys.stdout.isatty', return_value=True):
            path = Path(directory) / '.env'
            original = 'CUSTOM_SETTING=preserved\n'
            path.write_text(original, encoding='utf-8')
            with patch('builtins.input', side_effect=['123', 'http://localhost:8000']), patch('payments.management.commands.setup_test_payments.getpass', return_value='test-secret'), self.assertRaises(CommandError):
                call_command('setup_test_payments', stdout=io.StringIO())
            self.assertEqual(path.read_text(encoding='utf-8'), original)

    def test_setup_refuses_noninteractive_secret_input(self):
        with patch('sys.stdin.isatty', return_value=False), patch('payments.management.commands.setup_test_payments.getpass') as prompt, self.assertRaises(CommandError):
            call_command('setup_test_payments', stdout=io.StringIO())
        prompt.assert_not_called()
