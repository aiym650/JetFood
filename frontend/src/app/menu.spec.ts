import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { Menu } from './menu';

describe('Menu', () => {
  let service: Menu;
  let httpTesting: HttpTestingController;

  beforeEach(() => {
    localStorage.setItem('token', 'menu-test-token');
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(Menu);
    httpTesting = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpTesting.verify();
    localStorage.removeItem('token');
  });

  it('loads the API-paginated menu with the active token', () => {
    let items: unknown;
    service.getItems().subscribe(result => items = result);

    const request = httpTesting.expectOne('http://localhost:8000/api/orders/menu/');
    expect(request.request.headers.get('Authorization')).toBe('Token menu-test-token');
    request.flush({
      count: 1,
      results: [{
        id: 1,
        name: 'Пицца Маргарита',
        description: 'Томаты, моцарелла, базилик',
        price: '890.00',
        image_url: '',
        category: 'Пицца',
        rating: '4.8',
      }],
    });

    expect(items).toEqual([expect.objectContaining({ id: 1, price: '890.00' })]);
  });
});
