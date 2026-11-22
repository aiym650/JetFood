from django.test import SimpleTestCase


class CheckoutCorsTests(SimpleTestCase):
    def preflight(self, origin):
        return self.client.options(
            '/api/orders/',
            HTTP_ORIGIN=origin,
            HTTP_ACCESS_CONTROL_REQUEST_METHOD='POST',
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS='authorization,content-type,idempotency-key',
        )

    def test_browser_can_submit_idempotent_checkout_from_both_frontend_origins(self):
        for origin in ['http://localhost:4200', 'http://127.0.0.1:4200']:
            with self.subTest(origin=origin):
                response = self.preflight(origin)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.headers['Access-Control-Allow-Origin'], origin)
                allowed_headers = {value.strip().lower() for value in response.headers['Access-Control-Allow-Headers'].split(',')}
                self.assertTrue({'authorization', 'content-type', 'idempotency-key'} <= allowed_headers)
                self.assertIn('POST', response.headers['Access-Control-Allow-Methods'])

    def test_checkout_still_rejects_untrusted_origins(self):
        response = self.preflight('https://untrusted.example')
        self.assertNotIn('Access-Control-Allow-Origin', response.headers)
