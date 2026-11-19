import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { Auth } from '../auth';
import { SidebarComponent } from '../shared/sidebar/sidebar';
import { LanguageSwitcher } from '../shared/language-switcher/language-switcher';
import { SupportChat } from '../support-chat/support-chat';

@Component({
  selector: 'app-shell',
  imports: [RouterOutlet, SidebarComponent, LanguageSwitcher, SupportChat],
  templateUrl: './app-shell.html',
  styleUrl: './app-shell.css',
})
export class AppShell {
  sidebarCollapsed = false;

  constructor(private auth: Auth) {}

  get currentUser() {
    return this.auth.getCurrentUser();
  }

  toggleSidebar(): void {
    this.sidebarCollapsed = !this.sidebarCollapsed;
  }

}
