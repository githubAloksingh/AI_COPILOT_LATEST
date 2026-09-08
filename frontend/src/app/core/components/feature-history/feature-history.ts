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
    if (!item.documentId) {
      alert('Document ID is not available for this record.');
      return;
    }
    this.api.getDocumentFile(item.documentId).subscribe({
      next: (blob: Blob) => {
        const pdfBlob = new Blob([blob], { type: 'application/pdf' });
        const url = window.URL.createObjectURL(pdfBlob);
        window.open(url, '_blank');
      },
      error: () => {
        alert('Failed to retrieve original PDF file from server.');
      }
    });
  }

  downloadDocument(item: any): void {
    if (!item.documentId) {
      alert('Document ID is not available for this record.');
      return;
    }
    this.api.downloadDocument(item.documentId).subscribe({
      next: (blob: Blob) => {
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = item.documentName || 'document.pdf';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
      },
      error: () => {
        alert('Failed to download original document from server.');
      }
    });
  }

  refresh(): void {
    this.loadHistory();
  }
}
