import { Component, Input, OnChanges, SimpleChanges, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../api';

@Component({
  selector: 'app-feature-history',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './feature-history.html',
  styleUrls: ['./feature-history.scss']
})
export class FeatureHistoryComponent implements OnChanges {
  @Input() projectId: number | null = null;
  @Input() feature: string = '';
  @Input() projectName?: string = '';

  loading = false;
  historyItems: any[] = [];
  errorMessage = '';

  constructor(
    private api: ApiService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['projectId'] || changes['feature']) {
      this.loadHistory();
    }
  }

  loadHistory(): void {
    if (!this.projectId || !this.feature) {
      this.historyItems = [];
      this.loading = false;
      this.errorMessage = '';
      this.cdr.markForCheck();
      return;
    }

    this.loading = true;
    this.errorMessage = '';
    this.cdr.markForCheck();

    this.api.getHistory(this.projectId, this.feature).subscribe({
      next: (res) => {
        this.loading = false;
        if (res.success) {
          this.historyItems = res.data || [];
        } else {
          this.historyItems = [];
          this.errorMessage = res.message || 'Failed to load history';
        }
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.loading = false;
        this.historyItems = [];
        this.errorMessage = err.error?.message || 'Error loading history records';
        this.cdr.markForCheck();
      }
    });
  }

  viewDocument(item: any): void {
    if (item.canView && item.viewUrl) {
      window.open(item.viewUrl, '_blank');
    }
  }

  downloadDocument(item: any): void {
    if (item.downloadUrl) {
      const link = document.createElement('a');
      link.href = item.downloadUrl;
      link.setAttribute('download', item.documentName || 'download');
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  }

  refresh(): void {
    this.loadHistory();
  }
}
