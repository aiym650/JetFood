import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ExternalIntegrationInput, ExternalIntegrationRecord } from './integration';

import { Integration } from './integration';

describe('Integration', () => {
  let service: Integration;
  let httpTesting: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(Integration);
    httpTesting = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpTesting.verify());

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('maps paginated backend integration data to frontend records', () => {
    let records: ExternalIntegrationRecord[] = [];
    service.getIntegrations().subscribe(value => records = value);
    httpTesting.expectOne('http://localhost:8000/api/integration/').flush({
      count: 1,
      results: [{
        id: 8,
        name: 'Maps',
        integration_type: 'mapping_service',
        status: 'active',
        api_endpoint: 'https://maps.example.test',
        api_key_present: false,
        config: {},
        last_sync: null,
        created_at: '',
        updated_at: '',
      }],
    });

    expect(records[0].id).toBe(8);
    expect(records[0].integration_type).toBe('mapping_service');
  });

  it('posts integration credentials and consumes the safe serializer response', () => {
    const payload: ExternalIntegrationInput = {
      name: 'Payments',
      integration_type: 'payment_gateway',
      api_endpoint: 'https://payments.example.test',
      api_key: 'write-only-secret',
    };
    let response: ExternalIntegrationRecord | undefined;
    service.createIntegration(payload).subscribe(value => response = value);
    const request = httpTesting.expectOne('http://localhost:8000/api/integration/');
    expect(request.request.method).toBe('POST');
    expect(request.request.body.api_key).toBe('write-only-secret');
    request.flush({
      id: 9,
      name: payload.name,
      integration_type: payload.integration_type,
      status: 'active',
      api_endpoint: payload.api_endpoint,
      api_key_present: true,
      config: {},
      last_sync: null,
      created_at: '',
      updated_at: '',
    });

    expect(response?.api_key_present).toBe(true);
    expect('api_key' in (response ?? {})).toBe(false);
  });

  it('uses the backend sync endpoint and reads its response', () => {
    let message = '';
    service.syncIntegration(14).subscribe(result => message = result.message);
    const request = httpTesting.expectOne('http://localhost:8000/api/integration/14/sync/');
    expect(request.request.method).toBe('POST');
    request.flush({ message: 'Sync completed successfully', last_sync: '2026-01-01T10:00:00Z' });

    expect(message).toBe('Sync completed successfully');
  });
});
