import { Component } from '@angular/core';
import { Router, RouterOutlet } from '@angular/router';
import { Auth } from '../auth';
import { SidebarComponent } from '../shared/sidebar/sidebar';
import { SearchBar } from '../shared/search/search-bar/search-bar';
import { LanguageSwitcher } from '../shared/language-switcher/language-switcher';

@Component({
  selector: 'app-shell',
  imports: [RouterOutlet, SidebarComponent, SearchBar, LanguageSwitcher],
  templateUrl: './app-shell.html',
  styleUrl: './app-shell.css',
})
export class AppShell {
  sidebarCollapsed = false;

  constructor(private auth: Auth, private router: Router) {}

  get currentUser() {
    return this.auth.getCurrentUser();
  }

  toggleSidebar(): void {
    this.sidebarCollapsed = !this.sidebarCollapsed;
  }

  selectSearchResult(result: { type: string; item: { id: number } }): void {
    if (result.type === 'order') {
      this.router.navigate(['/orders'], { queryParams: { orderId: result.item.id } });
    } else if (result.type === 'user' && this.currentUser?.role === 'admin') {
      this.router.navigate(['/admin'], { queryParams: { userId: result.item.id } });
    } else {
      const search = result.type === 'menu' && 'name' in result.item
        ? (result.item as { name: string }).name
        : '';
      this.router.navigate(['/dashboard'], { queryParams: search ? { search } : {} });
    }
  }
}
