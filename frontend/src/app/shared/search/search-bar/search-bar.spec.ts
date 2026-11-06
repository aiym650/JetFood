import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { vi } from 'vitest';

import { SearchBar } from './search-bar';
import { SearchService } from '../search';

describe('SearchBar', () => {
  let fixture: ComponentFixture<SearchBar>;
  let component: SearchBar;
  let searchAll: ReturnType<typeof vi.fn>;

  beforeEach(async () => {
    searchAll = vi.fn().mockReturnValue(of({ orders: [], users: [], menu_items: [] }));
    await TestBed.configureTestingModule({
      imports: [SearchBar],
      providers: [{ provide: SearchService, useValue: { searchAll } }],
    }).compileComponents();
    fixture = TestBed.createComponent(SearchBar);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('does not send searches shorter than two characters', () => {
    component.query = 'a';
    component.onSearch();
    expect(searchAll).not.toHaveBeenCalled();
  });

  it('shows results from orders, users, and menu items', () => {
    searchAll.mockReturnValue(of({
      orders: [{ id: 1, order_number: 'ORD-1', status: 'pending', total_amount: 900 }],
      users: [{ id: 2, username: 'customer', role: 'customer', email: 'customer@example.com' }],
      menu_items: [{ id: 3, name: 'Pizza', category: 'Pizza', price: 900, description: '' }],
    }));
    component.query = 'pizza';
    component.onSearch();
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('ORD-1');
    expect(fixture.nativeElement.textContent).toContain('customer');
    expect(fixture.nativeElement.textContent).toContain('Pizza');
  });
});
