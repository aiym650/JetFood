import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';

import { Integration } from './integration';

describe('Integration', () => {
  let service: Integration;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient()],
    });
    service = TestBed.inject(Integration);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
