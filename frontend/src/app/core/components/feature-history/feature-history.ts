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
  projectDocuments: any[] = [];
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

    // Fetch project documents first to help resolve any unlinked history items
    this.api.getProjectDocuments(this.projectId).subscribe({
      next: (docRes) => {
        this.projectDocuments = (docRes && docRes.success && docRes.data) ? docRes.data : [];
        this.fetchHistoryRecords();
      },
      error: () => {
        this.projectDocuments = [];
        this.fetchHistoryRecords();
      }
    });
  }

  private fetchHistoryRecords(): void {
    this.api.getHistory(this.projectId!, this.feature).subscribe({
      next: (res) => {
        this.loading = false;
        if (res.success) {
          const rawItems = res.data || [];
          this.historyItems = rawItems.map((item: any) => this.enrichHistoryItem(item));
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

  private enrichHistoryItem(item: any): any {
    const enriched = { ...item };
    
    // Ensure documentName exists
    if (!enriched.documentName) {
      enriched.documentName = enriched.fileName || `Document_${enriched.id || 'record'}`;
    }

    // Try resolving documentId if missing
    if (!enriched.documentId && this.projectDocuments.length > 0) {
      const match = this.findMatchingDocument(enriched);
      if (match) {
        enriched.documentId = match.id;
      } else {
        // Fallback to latest available document for the project if available
        const fallbackDoc = this.projectDocuments[0];
        if (fallbackDoc && fallbackDoc.id) {
          enriched.documentId = fallbackDoc.id;
        }
      }
    }

    return enriched;
  }

  private findMatchingDocument(item: any): any {
    if (!this.projectDocuments || this.projectDocuments.length === 0) return null;

    const itemName = (item.documentName || item.fileName || '').toLowerCase().trim();
    const itemCleanName = itemName.replace(/\.[^/.]+$/, '').replace(/[\s_()\-]/g, '');

    // 1. Exact match on fileName, originalFilename, or title
    for (const doc of this.projectDocuments) {
      const fn = (doc.fileName || '').toLowerCase().trim();
      const orig = (doc.originalFilename || '').toLowerCase().trim();
      const title = (doc.title || '').toLowerCase().trim();
      if (fn === itemName || orig === itemName || title === itemName) {
        return doc;
      }
    }

    // 2. Cleaned name match
    for (const doc of this.projectDocuments) {
      const fn = (doc.fileName || '').toLowerCase().trim();
      const cleanFn = fn.replace(/\.[^/.]+$/, '').replace(/[\s_()\-]/g, '');
      if (cleanFn && cleanFn === itemCleanName) {
        return doc;
      }
    }

    // 3. Substring match
    for (const doc of this.projectDocuments) {
      const fn = (doc.fileName || '').toLowerCase().trim();
      if (fn && (fn.includes(itemName) || itemName.includes(fn))) {
        return doc;
      }
    }

    // 4. File extension / type match
    const isPdf = itemName.endsWith('.pdf') || item.fileType === 'PDF';
    const isZip = itemName.endsWith('.zip') || item.fileType === 'ZIP';
    const isCsv = itemName.endsWith('.csv') || item.fileType === 'CSV';

    for (const doc of this.projectDocuments) {
      const fn = (doc.fileName || '').toLowerCase().trim();
      if (isPdf && fn.endsWith('.pdf')) return doc;
      if (isZip && fn.endsWith('.zip')) return doc;
      if (isCsv && fn.endsWith('.csv')) return doc;
    }

    return null;
  }

  viewDocument(item: any): void {
    const docId = item.documentId || item.fileId || item.id;
    if (!docId) {
      alert('Unable to view this document.');
      return;
    }

    const docName = (item.documentName || item.fileName || 'document.pdf').toLowerCase();
    const isZip = docName.endsWith('.zip') || item.fileType === 'ZIP';
    const isCsv = docName.endsWith('.csv') || item.fileType === 'CSV';
    const isPdf = docName.endsWith('.pdf') || item.fileType === 'PDF';

    this.api.getDocumentFile(docId).subscribe({
      next: (blob: Blob) => {
        let mimeType = blob.type;
        if (!mimeType || mimeType === 'application/octet-stream') {
          if (isPdf) mimeType = 'application/pdf';
          else if (isCsv) mimeType = 'text/csv';
          else if (isZip) mimeType = 'application/zip';
          else mimeType = 'text/plain';
        }

        if (isZip) {
          const url = window.URL.createObjectURL(new Blob([blob], { type: mimeType }));
          const a = document.createElement('a');
          a.href = url;
          a.download = item.documentName || 'codebase.zip';
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          window.URL.revokeObjectURL(url);
          return;
        }

        const viewBlob = new Blob([blob], { type: mimeType });
        const url = window.URL.createObjectURL(viewBlob);
        const win = window.open(url, '_blank');
        if (!win) {
          window.location.href = url;
        }
      },
      error: () => {
        alert('Unable to view this document.');
      }
    });
  }

  downloadDocument(item: any): void {
    const docId = item.documentId || item.fileId || item.id;
    if (!docId) {
      alert('Unable to download this document.');
      return;
    }

    this.api.downloadDocument(docId).subscribe({
      next: (blob: Blob) => {
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = item.documentName || item.fileName || 'document.pdf';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
      },
      error: () => {
        alert('Unable to download this document.');
      }
    });
  }

  refresh(): void {
    this.loadHistory();
  }
}

