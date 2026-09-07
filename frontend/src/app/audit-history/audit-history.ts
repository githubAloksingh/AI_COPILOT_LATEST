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
  projectFilter = 'ALL';
  availableUsers: string[] = [];
  availableProjects: string[] = [];

  constructor(public api: ApiService, private cdr: ChangeDetectorRef) {}

  ngOnInit() {
    this.loadUsers();
    this.loadProjects();
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

  loadUsers() {
    this.api.getUsers().subscribe({
      next: (res) => {
        if (res.success && res.data) {
          this.availableUsers = res.data.map((u: any) => u.username || u.name);
        }
        this.cdr.markForCheck();
      }
    });
  }

  loadProjects() {
    this.api.getProjects().subscribe({
      next: (res) => {
        if (res.success && res.data) {
          this.availableProjects = res.data.map((p: any) => p.projectName);
        }
        this.cdr.markForCheck();
      }
    });
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

          // Also collect any project names present in logs
          const setProjects = new Set<string>(this.availableProjects);
          this.logs.forEach(l => {
            if (l.projectName) setProjects.add(l.projectName);
          });
          this.availableProjects = Array.from(setProjects);

          // If availableUsers wasn't populated yet, collect from logs
          if (this.availableUsers.length === 0) {
            const setUsers = new Set<string>();
            this.logs.forEach(l => {
              if (l.userName) setUsers.add(l.userName);
            });
            this.availableUsers = Array.from(setUsers);
          }
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

  get filteredLogs(): any[] {
    if (this.projectFilter === 'ALL') {
      return this.logs;
    }
    return this.logs.filter(l => l.projectName === this.projectFilter);
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

  /** Statuses that represent a completed, usable result rather than an execution error. */
  isSuccessfulLog(log: any): boolean {
    return ['SUCCESS', 'ACCEPTED', 'COMPLETED'].includes(log?.status);
  }
}
