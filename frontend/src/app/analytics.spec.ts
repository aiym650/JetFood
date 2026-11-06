import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';

import { Analytics } from './analytics';

describe('Analytics', () => {
  let service: Analytics;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient()],
    });
    service = TestBed.inject(Analytics);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
