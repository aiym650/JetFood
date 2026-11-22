import { Component } from '@angular/core';
import { RouterLink, RouterOutlet } from '@angular/router';
import { Auth } from '../auth';
import { SidebarComponent } from '../shared/sidebar/sidebar';
import { LanguageSwitcher } from '../shared/language-switcher/language-switcher';
import { SupportChat } from '../support-chat/support-chat';
import { I18nService } from '../i18n/i18n.service';

@Component({
  selector: 'app-shell',
  imports: [RouterOutlet, RouterLink, SidebarComponent, LanguageSwitcher, SupportChat],
  templateUrl: './app-shell.html',
  styleUrl: './app-shell.css',
})
export class AppShell {
  sidebarCollapsed = false;

  constructor(private auth: Auth, public i18n: I18nService) {}

  get currentUser() {
    return this.auth.getCurrentUser();
  }

  toggleSidebar(): void {
    this.sidebarCollapsed = !this.sidebarCollapsed;
  }

}
