import { ChangeDetectorRef, Component, EventEmitter, OnDestroy, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DomSanitizer, SafeHtml, SafeResourceUrl } from '@angular/platform-browser';
import * as XLSX from 'xlsx-js-style';
import { ApiService } from '../../api';

@Component({
  selector: 'app-pdf-viewer',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './pdf-viewer.html',
  styleUrls: ['./pdf-viewer.scss']
})
export class PdfViewerComponent implements OnDestroy {
  @Output() closed = new EventEmitter<void>();

  visible = false;
  documentName = '';
  documentId: number | null = null;
  previewPdfUrl: SafeResourceUrl | null = null;
  previewBlobUrl: string | null = null;
  spreadsheetHtml: SafeHtml | null = null;
  csvText: string | null = null;
  downloadBlob: Blob | null = null;
  loading = false;
  error = '';

  constructor(
    private api: ApiService,
    private cdr: ChangeDetectorRef,
    private sanitizer: DomSanitizer
  ) {}

  open(documentId: number, documentName: string): void {
    this.documentId = documentId;
    this.documentName = documentName;
    this.error = '';
    this.loading = true;
    this.visible = true;
    this.cleanupBlobUrl();
    this.previewPdfUrl = null;
    this.cdr.markForCheck();

    this.api.getDocumentFile(documentId).subscribe({
      next: async (blob: Blob) => {
        if (!(await this.isPdf(blob))) {
          this.loading = false;
          this.error = 'The uploaded file is not a readable PDF. Please upload the original PDF again.';
          this.cdr.markForCheck();
          return;
        }

        const contentType = (blob?.type || '').toLowerCase();
        const mimeType = contentType.includes('pdf') ? 'application/pdf' : 'application/pdf';
        const pdfBlob = new Blob([blob], { type: mimeType });
        this.previewBlobUrl = URL.createObjectURL(pdfBlob);
        this.previewPdfUrl = this.sanitizer.bypassSecurityTrustResourceUrl(this.previewBlobUrl);
        this.loading = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.loading = false;
        this.error = 'Unable to retrieve the original file from the server.';
        this.cdr.markForCheck();
      }
    });
  }

  openBlob(blob: Blob, documentName: string): void {
    this.documentId = null;
    this.documentName = this.normalizeFilename(documentName, 'pdf');
    this.downloadBlob = blob;
    this.error = '';
    this.loading = false;
    this.visible = true;
    this.cleanupBlobUrl();
    this.spreadsheetHtml = null;
    const pdfBlob = new Blob([blob], { type: 'application/pdf' });
    this.previewBlobUrl = URL.createObjectURL(pdfBlob);
    this.previewPdfUrl = this.sanitizer.bypassSecurityTrustResourceUrl(this.previewBlobUrl);
    this.cdr.markForCheck();
  }

  openSpreadsheetBlob(blob: Blob, documentName: string): void {
    this.documentId = null;
    this.documentName = this.normalizeFilename(documentName, 'xlsx');
    this.downloadBlob = blob;
    this.error = '';
    this.loading = true;
    this.visible = true;
    this.cleanupBlobUrl();
    this.previewPdfUrl = null;
    this.spreadsheetHtml = null;
    this.csvText = null;

    blob.arrayBuffer().then((buffer) => {
      const workbook = XLSX.read(buffer, { type: 'array', cellDates: true });
      const firstSheet = workbook.Sheets[workbook.SheetNames[0]];
      const html = XLSX.utils.sheet_to_html(firstSheet, { id: 'excel-preview-sheet' });
      this.spreadsheetHtml = this.sanitizer.bypassSecurityTrustHtml(html);
      this.loading = false;
      this.cdr.markForCheck();
    }).catch(() => {
      this.loading = false;
      this.error = 'Unable to generate spreadsheet preview.';
      this.cdr.markForCheck();
    });
  }

  openCsvBlob(blob: Blob, documentName: string): void {
    this.documentId = null;
    this.documentName = this.normalizeFilename(documentName, 'csv');
    this.downloadBlob = blob;
    this.error = '';
    this.loading = true;
    this.visible = true;
    this.cleanupBlobUrl();
    this.previewPdfUrl = null;
    this.spreadsheetHtml = null;
    this.csvText = null;

    blob.text().then((text) => {
      this.csvText = text;
      this.loading = false;
      this.cdr.markForCheck();
    }).catch(() => {
      this.loading = false;
      this.error = 'Unable to generate CSV preview.';
      this.cdr.markForCheck();
    });
  }

  downloadCurrentDocument(): void {
    const fileType = this.downloadBlob?.type?.includes('sheet')
      ? 'xlsx'
      : this.downloadBlob?.type?.includes('csv')
        ? 'csv'
        : 'pdf';
    const fileName = this.normalizeFilename(
      this.documentName || (this.documentId ? `document-${this.documentId}` : 'document.xlsx'),
      fileType as 'pdf' | 'xlsx' | 'csv'
    );

    const triggerDownload = (blob: Blob) => {
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = fileName;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    };

    if (this.documentId) {
      this.api.downloadDocument(this.documentId).subscribe({
        next: (blob: Blob) => triggerDownload(blob),
        error: () => {
          alert('Unable to download this document.');
        }
      });
      return;
    }

    if (this.downloadBlob) {
      triggerDownload(this.downloadBlob);
      return;
    }

    if (this.previewBlobUrl) {
      fetch(this.previewBlobUrl)
        .then(response => response.blob())
        .then(blob => triggerDownload(blob))
        .catch(() => alert('Unable to download this document.'));
    }
  }

  close(): void {
    this.visible = false;
    this.cleanupBlobUrl();
    this.previewPdfUrl = null;
    this.spreadsheetHtml = null;
    this.csvText = null;
    this.documentName = '';
    this.documentId = null;
    this.downloadBlob = null;
    this.error = '';
    this.closed.emit();
  }

  openInNewTab(): void {
    if (this.previewBlobUrl) {
      window.open(this.previewBlobUrl, '_blank');
    } else if (this.documentId) {
      this.api.getDocumentFile(this.documentId).subscribe({
        next: (blob: Blob) => {
          const pdfBlob = new Blob([blob], { type: 'application/pdf' });
          const url = URL.createObjectURL(pdfBlob);
          window.open(url, '_blank');
        }
      });
    }
  }

  download(): void {
    if (this.previewBlobUrl) {
      this.triggerDownload(this.previewBlobUrl);
      return;
    }

    if (this.documentId) {
      this.api.getDocumentFile(this.documentId).subscribe({
        next: (blob: Blob) => {
          const url = URL.createObjectURL(new Blob([blob], { type: 'application/pdf' }));
          this.triggerDownload(url);
          URL.revokeObjectURL(url);
        }
      });
    }
  }

  ngOnDestroy(): void {
    this.cleanupBlobUrl();
  }

  private cleanupBlobUrl(): void {
    if (this.previewBlobUrl) {
      URL.revokeObjectURL(this.previewBlobUrl);
      this.previewBlobUrl = null;
    }
  }

  private triggerDownload(url: string): void {
    const link = document.createElement('a');
    link.href = url;
    link.download = this.documentName || 'document.pdf';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  private normalizeFilename(fileName: string, type: 'pdf' | 'xlsx' | 'csv'): string {
    const cleaned = (fileName || '').trim();
    if (!cleaned) {
      return type === 'xlsx' ? 'document.xlsx' : type === 'csv' ? 'document.csv' : 'document.pdf';
    }

    const lower = cleaned.toLowerCase();
    if (type === 'xlsx' && !lower.endsWith('.xlsx')) {
      return `${cleaned}.xlsx`;
    }
    if (type === 'csv' && !lower.endsWith('.csv')) {
      return `${cleaned}.csv`;
    }
    if (type === 'pdf' && !lower.endsWith('.pdf')) {
      return `${cleaned}.pdf`;
    }

    return cleaned;
  }

  private async isPdf(blob: Blob): Promise<boolean> {
    if (blob.size < 5) {
      return false;
    }
    const signature = await blob.slice(0, 5).text();
    return signature === '%PDF-';
  }
}
