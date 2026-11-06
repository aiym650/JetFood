import { ChangeDetectorRef, Component, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { SearchService } from '../search';
import { I18nService } from '../../../i18n/i18n.service';

interface SearchResults {
  orders: Array<{ id: number; order_number: string; status: string; total_amount: number }>;
  users: Array<{ id: number; username: string; role: string; email: string }>;
  menu_items: Array<{ id: number; name: string; description: string; category: string; price: number }>;
}

@Component({
  selector: 'app-search-bar',
  imports: [CommonModule, FormsModule],
  templateUrl: './search-bar.html',
  styleUrl: './search-bar.css',
})
export class SearchBar {
  query = '';
  results: SearchResults | null = null;
  loading = false;
  error = '';
  showResults = false;

  @Output() resultSelected = new EventEmitter<any>();

  constructor(
    private searchService: SearchService,
    private changeDetector: ChangeDetectorRef,
    public i18n: I18nService
  ) {}

  onSearch(): void {
    const query = this.query.trim();
    if (query.length < 2) {
      this.results = null;
      this.showResults = false;
      return;
    }

    this.loading = true;
    this.error = '';
    this.searchService.searchAll(query).subscribe({
      next: (data) => {
        this.results = data;
        this.loading = false;
        this.showResults = true;
        this.changeDetector.markForCheck();
      },
      error: () => {
        this.loading = false;
        this.error = this.i18n.t('searchFailed');
        this.showResults = true;
        this.changeDetector.markForCheck();
      }
    });
  }

  selectResult(type: string, item: any): void {
    this.resultSelected.emit({ type, item });
    this.showResults = false;
    this.query = '';
  }

  closeResults(): void {
    this.showResults = false;
  }

  statusLabel(status: string): string {
    const key = `orderStatuses.${status}`;
    const label = this.i18n.t(key);
    return label === key ? status : label;
  }

  roleLabel(role: string): string {
    const key = `roles.${role}`;
    const label = this.i18n.t(key);
    return label === key ? role : label;
  }

  catalogLabel(value: string): string {
    return this.i18n.catalogLabel(value);
  }
}
