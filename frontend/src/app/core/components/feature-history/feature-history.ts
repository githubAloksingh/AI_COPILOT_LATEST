import { Component, Input, OnChanges, SimpleChanges, ChangeDetectorRef, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../api';
import { ExportService } from '../../services/export.service';
import { PdfViewerComponent } from '../pdf-viewer/pdf-viewer';

@Component({
  selector: 'app-feature-history',
  standalone: true,
  imports: [CommonModule, PdfViewerComponent],
  templateUrl: './feature-history.html',
  styleUrls: ['./feature-history.scss']
})
export class FeatureHistoryComponent implements OnChanges {
  @ViewChild(PdfViewerComponent) pdfViewer?: PdfViewerComponent;

  @Input() projectId: number | null = null;
  @Input() documentId: number | null = null;
  @Input() documentName?: string = '';
  @Input() feature: string = '';
  @Input() projectName?: string = '';

  loading = false;
  historyItems: any[] = [];
  projectDocuments: any[] = [];
  errorMessage = '';

  constructor(
    private api: ApiService,
    private exportService: ExportService,
    private cdr: ChangeDetectorRef
  ) {}

  get isUserStory(): boolean {
    const f = (this.feature || '').toLowerCase().replace(/[-_\s]/g, '');
    return f === 'userstory';
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['projectId'] || changes['feature'] || changes['documentId']) {
      this.loadHistory();
    }
  }

  loadHistory(): void {
    if (this.isUserStory) {
      if (!this.projectId || !this.documentId) {
        this.historyItems = [];
        this.loading = false;
        this.errorMessage = '';
        this.cdr.markForCheck();
        return;
      }
    } else if (!this.projectId || !this.feature) {
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
    this.api.getProjectDocuments(this.projectId!).subscribe({
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
    this.api.getHistory(this.projectId!, this.feature, this.documentId).subscribe({
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
      enriched.documentName = this.documentName || enriched.fileName || `Document_${enriched.id || 'record'}`;
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
    if (this.isUserStory || item.feature === 'user_story') {
      this.viewUserStory(item);
      return;
    }

    const docId = item.documentId || item.fileId || item.id;
    if (!docId) {
      alert('Unable to view this document.');
      return;
    }

    const docName = (item.documentName || item.fileName || 'document.pdf').toLowerCase();
    const isZip = docName.endsWith('.zip') || item.fileType === 'ZIP';
    const isCsv = docName.endsWith('.csv') || item.fileType === 'CSV';
    const isPdf = docName.endsWith('.pdf') || item.fileType === 'PDF';

    if (isPdf) {
      this.pdfViewer?.open(docId, item.documentName || item.fileName || 'document.pdf');
      return;
    }

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
        window.location.href = url;
      },
      error: () => {
        alert('Unable to view this document.');
      }
    });
  }

  downloadDocument(item: any): void {
    if (this.isUserStory || item.feature === 'user_story') {
      this.downloadUserStory(item);
      return;
    }

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

  private viewUserStory(item: any): void {
    const renderPdf = (contentStr: string) => {
      const stories = this.parseUserStoryContent(contentStr);
      if (!stories || stories.length === 0) {
        alert('No user story content available to view.');
        return;
      }
      const meta = {
        project: item.projectName || this.projectName,
        documentName: item.documentName || this.documentName || 'BRD',
        version: item.version || '1.0',
        work: 'User Stories'
      };
      const blob = this.exportService.generateUserStoryPdfBlob(stories, meta);
      if (blob) {
        const title = `${meta.project || 'Project'}_User_Stories_v${meta.version}.pdf`;
        this.pdfViewer?.openBlob(blob, title);
      } else {
        alert('Could not generate PDF for viewing.');
      }
    };

    if (item.content) {
      renderPdf(item.content);
    } else if (item.id) {
      this.api.getHistoryContent(item.id).subscribe({
        next: (res) => {
          if (res.success && res.data) {
            item.content = res.data;
            renderPdf(res.data);
          } else {
            alert('Unable to load user story content.');
          }
        },
        error: () => alert('Unable to load user story content.')
      });
    }
  }

  private downloadUserStory(item: any): void {
    const triggerDownload = (contentStr: string) => {
      const stories = this.parseUserStoryContent(contentStr);
      if (!stories || stories.length === 0) {
        alert('No user story content available to download.');
        return;
      }
      const meta = {
        project: item.projectName || this.projectName,
        documentName: item.documentName || this.documentName || 'BRD',
        version: item.version || '1.0',
        work: 'User Stories'
      };
      this.exportService.downloadUserStoryPdf(stories, meta);
    };

    if (item.content) {
      triggerDownload(item.content);
    } else if (item.id) {
      this.api.getHistoryContent(item.id).subscribe({
        next: (res) => {
          if (res.success && res.data) {
            item.content = res.data;
            triggerDownload(res.data);
          } else {
            alert('Unable to load user story content for download.');
          }
        },
        error: () => alert('Unable to load user story content for download.')
      });
    }
  }

  private parseUserStoryContent(contentStr: string): any[] {
    if (!contentStr) return [];
    try {
      if (typeof contentStr === 'object') {
        const obj = contentStr as any;
        if (Array.isArray(obj)) return obj;
        if (Array.isArray(obj.requirements)) return obj.requirements;
        if (Array.isArray(obj.userStories)) return obj.userStories;
        if (Array.isArray(obj.items)) return obj.items;
        return [obj];
      }
      const trimmed = contentStr.trim();
      if (trimmed.startsWith('{') || trimmed.startsWith('[')) {
        const parsed = JSON.parse(trimmed);
        if (Array.isArray(parsed)) return parsed;
        if (Array.isArray(parsed.requirements)) return parsed.requirements;
        if (Array.isArray(parsed.userStories)) return parsed.userStories;
        if (Array.isArray(parsed.items)) return parsed.items;
        return [parsed];
      }
    } catch (e) {
      console.error('Error parsing user story JSON:', e);
    }
    return [];
  }

  refresh(): void {
    this.loadHistory();
  }
}

