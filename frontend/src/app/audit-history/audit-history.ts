import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../core/api';

@Component({
  selector: 'app-audit-history',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './audit-history.html',
  styleUrl: './audit-history.scss'
})
export class AuditHistory implements OnInit {
  logs: any[] = [];
  loading = true;
  userFilter = 'ALL';
  availableUsers = ['User A', 'User B', 'User C', 'Admin'];

  constructor(public api: ApiService, private cdr: ChangeDetectorRef) {}

  ngOnInit() {
    this.loadLogs();
  }

  get currentUser(): string {
    return this.api.getCurrentUser();
  }

  get currentRole(): 'ADMIN' | 'USER' {
    return this.api.getCurrentRole();
  }

  get isAdmin(): boolean {
    return this.currentRole === 'ADMIN';
  }

  loadLogs() {
    this.loading = true;
    const filter = this.isAdmin ? this.userFilter : this.currentUser;
    this.api.getAuditLogs(filter).subscribe({
      next: (res) => {
        if (res.success) {
          this.logs = (res.data || []).map((log: any) => {
            let parsed = null;
            if (log.output) {
              try {
                let str = log.output.trim();
                if (str.startsWith("```json")) str = str.substring(7);
                if (str.startsWith("```")) str = str.substring(3);
                if (str.endsWith("```")) str = str.substring(0, str.length() - 3);
                parsed = JSON.parse(str.trim());
              } catch (e) {
                parsed = null;
              }
            }
            return {
              ...log,
              parsedOutput: parsed,
              isArrayOutput: Array.isArray(parsed)
            };
          });

          // Collect distinct users for admin filter dropdown
          const setUsers = new Set<string>(['User A', 'User B', 'User C', 'Admin']);
          this.logs.forEach(l => {
            if (l.userName) setUsers.add(l.userName);
          });
          this.availableUsers = Array.from(setUsers);
        }
        this.loading = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.loading = false;
        this.cdr.markForCheck();
      }
    });
  }

  formatDate(timestamp: string) {
    if (!timestamp) return '';
    const d = new Date(timestamp);
    return `${d.toLocaleDateString()} ${d.toLocaleTimeString()}`;
  }

  toggleExpand(log: any) {
    log.expanded = !log.expanded;
    this.cdr.markForCheck();
  }
}
