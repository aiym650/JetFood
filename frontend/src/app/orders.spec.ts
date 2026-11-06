import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';

import { Orders } from './orders';

describe('Orders', () => {
  let service: Orders;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient()],
    });
    service = TestBed.inject(Orders);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
