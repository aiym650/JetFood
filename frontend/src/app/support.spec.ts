import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { Support } from './support';

describe('Support API', () => {
  let http: HttpTestingController;
  let service: Support;
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    http = TestBed.inject(HttpTestingController);
    service = TestBed.inject(Support);
  });
  afterEach(() => http.verify());

  it('preserves a supplied request ID when retrying a message', () => {
    for (let attempt = 0; attempt < 2; attempt++) {
      service.sendMessage(7, 'How can I apply a promo?', 'stable-message-id').subscribe();
      const request = http.expectOne('http://localhost:8000/api/support/cases/7/messages/');
      expect(request.request.method).toBe('POST');
      expect(request.request.body).toEqual({
        body: 'How can I apply a promo?',
        request_id: 'stable-message-id',
      });
      request.flush({});
    }
  });

  it('loads a saved conversation directly instead of depending on the first history page', () => {
    service.getCase(31).subscribe();
    const request = http.expectOne('http://localhost:8000/api/support/cases/31/');
    expect(request.request.method).toBe('GET');
    request.flush({});
  });
});
