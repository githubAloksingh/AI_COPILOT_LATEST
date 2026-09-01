import { Component, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../core/api';

@Component({
  selector: 'app-release-notes',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './release-notes.html',
  styleUrl: './release-notes.scss'
})
export class ReleaseNotes {
  version = '';
  sprintInformation = '';

  loading = false;
  error = '';
  result: any = null;

  constructor(private api: ApiService, private cdr: ChangeDetectorRef) {}

  generate() {
    if (!this.version || !this.sprintInformation) return;

    this.loading = true;
    this.error = '';
    this.result = null;
    this.cdr.markForCheck();

    this.api.generateReleaseNotes({
      version: this.version,
      sprintInformation: this.sprintInformation
    }).subscribe({
      next: (res) => {
        if (res.success) {
          this.result = res.data;
        } else {
          this.error = res.message || 'Generation failed';
        }
        this.loading = false;
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.error = 'Failed to generate release notes. Please try again.';
        this.loading = false;
        this.cdr.markForCheck();
      }
    });
  }

  copy() {
    navigator.clipboard.writeText(JSON.stringify(this.result, null, 2));
    alert('Release notes copied to clipboard');
  }
}
