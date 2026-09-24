import { ChangeDetectorRef, Component, EventEmitter, OnDestroy, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
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
    this.documentName = documentName;
    this.error = '';
    this.loading = false;
    this.visible = true;
    this.cleanupBlobUrl();
    const pdfBlob = new Blob([blob], { type: 'application/pdf' });
    this.previewBlobUrl = URL.createObjectURL(pdfBlob);
    this.previewPdfUrl = this.sanitizer.bypassSecurityTrustResourceUrl(this.previewBlobUrl);
    this.cdr.markForCheck();
  }

  close(): void {
    this.visible = false;
    this.cleanupBlobUrl();
    this.previewPdfUrl = null;
    this.documentName = '';
    this.documentId = null;
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

  private async isPdf(blob: Blob): Promise<boolean> {
    if (blob.size < 5) {
      return false;
    }
    const signature = await blob.slice(0, 5).text();
    return signature === '%PDF-';
  }
}
