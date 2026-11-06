import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';

import { Reports } from './reports';

describe('Reports', () => {
  let service: Reports;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient()],
    });
    service = TestBed.inject(Reports);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
