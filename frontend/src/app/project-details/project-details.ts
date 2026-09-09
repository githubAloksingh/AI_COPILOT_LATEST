import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { ApiService } from '../core/api';

@Component({
  selector: 'app-project-details',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './project-details.html',
  styleUrls: ['./project-details.scss']
})
export class ProjectDetails implements OnInit, OnDestroy {
  private readonly maxUploadBytes = 1024 * 1024 * 1024;
  projectId: number = 0;
  project: any = null;
  documents: any[] = [];
  loading = true;
  loadingDocs = true;
  uploading = false;
  error = '';
  docError = '';
  private pollInterval: any = null;

  // Upload Document Modal State
  showUploadModal = false;
  uploadForm = {
    title: '',
    type: 'BRD',
    file: null as File | null,
    version: 'v1'
  };
  uploadFormError = '';
  submittingUpload = false;

  // BRD PDF Viewer Modal State (Original Uploaded Binary)
  showPreviewModal = false;
  selectedDocName = '';
  selectedDocId: number | null = null;
  previewPdfUrl: SafeResourceUrl | null = null;
  previewBlobUrl: string | null = null;
  loadingPreview = false;
  previewError = '';

  // Document Chunks Modal State
  showChunksModal = false;
  chunksDocName = '';
  chunksList: any[] = [];
  loadingChunks = false;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private api: ApiService,
    private cdr: ChangeDetectorRef,
    private sanitizer: DomSanitizer
  ) {}

  ngOnInit() {
    this.route.params.subscribe(params => {
      if (params['id']) {
        this.projectId = +params['id'];
        this.loadProjectDetails();
        this.loadDocuments();
      }
    });
  }

  ngOnDestroy() {
    this.stopPolling();
    this.cleanupPreviewBlobUrl();
  }

  loadProjectDetails() {
    this.loading = true;
    this.error = '';
    this.api.getProject(this.projectId).subscribe({
      next: (res) => {
        if (res.success) {
          this.project = res.data;
        } else {
          this.error = res.message || 'Failed to load project details';
        }
        this.loading = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.error = 'Failed to load project details';
        this.loading = false;
        this.cdr.markForCheck();
      }
    });
  }

  loadDocuments(silent = false) {
    if (!silent) {
      this.loadingDocs = true;
      this.cdr.markForCheck();
    }
    this.docError = '';
    this.api.getProjectDocuments(this.projectId).subscribe({
      next: (res) => {
        if (res.success) {
          this.documents = res.data || [];
          this.checkPollingNeeded();
        } else {
          this.docError = res.message || 'Failed to load documents';
        }
        this.loadingDocs = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.docError = 'Failed to load project documents';
        this.loadingDocs = false;
        this.stopPolling();
        this.cdr.markForCheck();
      }
    });
  }

  private checkPollingNeeded() {
    const hasActiveProcessing = this.documents.some(
      doc => doc.status === 'PROCESSING' || doc.status === 'UPLOADING'
    );

    if (hasActiveProcessing) {
      if (!this.pollInterval) {
        this.pollInterval = setInterval(() => {
          this.loadDocuments(true);
        }, 2000);
      }
    } else {
      this.stopPolling();
    }
  }

  private stopPolling() {
    if (this.pollInterval) {
      clearInterval(this.pollInterval);
      this.pollInterval = null;
    }
  }

  openUploadModal() {
    this.uploadForm = {
      title: '',
      type: 'BRD',
      file: null,
      version: 'v1'
    };
    this.uploadFormError = '';
    this.submittingUpload = false;
    this.showUploadModal = true;
    this.cdr.markForCheck();
  }

  closeUploadModal() {
    this.showUploadModal = false;
    this.uploadFormError = '';
    this.submittingUpload = false;
    this.cdr.markForCheck();
  }

  onFileSelected(event: any) {
    const file: File = event.target.files[0];
    if (file) {
      this.uploadForm.file = file;
      if (!this.uploadForm.title.trim()) {
        this.uploadForm.title = file.name;
      }
      if (file.name.toLowerCase().endsWith('.zip')) {
        this.uploadForm.type = 'ZIP';
      } else {
        this.uploadForm.type = 'BRD';
      }
      this.cdr.markForCheck();
    }
  }

  submitUpload() {
    if (!this.uploadForm.title || !this.uploadForm.title.trim()) {
      this.uploadFormError = 'Title is required.';
      return;
    }
    if (!this.uploadForm.type || !this.uploadForm.type.trim()) {
      this.uploadFormError = 'Type is required.';
      return;
    }
    if (!this.uploadForm.file) {
      this.uploadFormError = 'File is required. Please select a file.';
      return;
    }
    if (this.uploadForm.file.size > this.maxUploadBytes) {
      this.uploadFormError = 'Files must be 1 GB or smaller.';
      return;
    }
    if (!this.uploadForm.version || !this.uploadForm.version.trim()) {
      this.uploadFormError = 'Version is required.';
      return;
    }

    this.submittingUpload = true;
    this.uploadFormError = '';
    this.cdr.markForCheck();

    this.api.uploadProjectDocument(
      this.projectId,
      this.uploadForm.file,
      this.uploadForm.title.trim(),
      this.uploadForm.type.trim(),
      this.api.getCurrentUser(),
      this.uploadForm.version.trim()
    ).subscribe({
      next: (res) => {
        if (res.success) {
          this.closeUploadModal();
          this.loadDocuments(true);
        } else {
          this.uploadFormError = res.message || 'Upload failed';
        }
        this.submittingUpload = false;
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.uploadFormError = err.error?.message || 'Failed to upload document. Please check file size and format.';
        this.submittingUpload = false;
        this.cdr.markForCheck();
      }
    });
  }

  downloadDocument(doc: any) {
    if (!doc || !doc.id) return;
    this.api.downloadDocument(doc.id).subscribe({
      next: (blob) => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = doc.fileName || 'document';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
      },
      error: (err) => {
        alert(err.error?.message || 'Failed to download original document. The file may not be available on server.');
      }
    });
  }

  deleteDocument(id: number) {
    if (confirm('Are you sure you want to delete this document?')) {
      this.api.deleteDocument(id).subscribe({
        next: () => {
          this.loadDocuments();
        }
      });
    }
  }

  isBrd(fileName: string): boolean {
    if (!fileName) return false;
    return !fileName.toLowerCase().endsWith('.zip');
  }

  getDocumentType(fileName: string): string {
    if (!fileName) return 'Unknown';
    if (fileName.toLowerCase().endsWith('.zip')) {
      return 'Project ZIP';
    }
    return 'BRD';
  }

  openPreview(doc: any) {
    if (!doc || !doc.id) return;
    if (!this.isBrd(doc.fileName)) return;

    this.selectedDocName = doc.fileName;
    this.selectedDocId = doc.id;
    this.previewError = '';
    this.loadingPreview = true;
    this.showPreviewModal = true;
    this.cleanupPreviewBlobUrl();
    this.previewPdfUrl = null;
    this.cdr.markForCheck();

    this.api.getDocumentFile(doc.id).subscribe({
      next: (blob: Blob) => {
        // Create a blob URL of type application/pdf with original uploaded binary
        const pdfBlob = new Blob([blob], { type: 'application/pdf' });
        this.previewBlobUrl = URL.createObjectURL(pdfBlob);
        this.previewPdfUrl = this.sanitizer.bypassSecurityTrustResourceUrl(this.previewBlobUrl);
        this.loadingPreview = false;
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.loadingPreview = false;
        this.previewError = 'Unable to retrieve original PDF file from server. The original uploaded binary could not be found.';
        this.cdr.markForCheck();
      }
    });
  }

  closePreview() {
    this.showPreviewModal = false;
    this.cleanupPreviewBlobUrl();
    this.previewPdfUrl = null;
    this.selectedDocName = '';
    this.selectedDocId = null;
    this.previewError = '';
  }

  private cleanupPreviewBlobUrl() {
    if (this.previewBlobUrl) {
      URL.revokeObjectURL(this.previewBlobUrl);
      this.previewBlobUrl = null;
    }
  }

  openPdfInNewTab() {
    if (this.previewBlobUrl) {
      window.open(this.previewBlobUrl, '_blank');
    } else if (this.selectedDocId) {
      this.api.getDocumentFile(this.selectedDocId).subscribe({
        next: (blob: Blob) => {
          const pdfBlob = new Blob([blob], { type: 'application/pdf' });
          const url = URL.createObjectURL(pdfBlob);
          window.open(url, '_blank');
        }
      });
    }
  }

  openChunksModal(doc: any) {
    this.chunksDocName = doc.fileName;
    this.chunksList = [];
    this.loadingChunks = true;
    this.showChunksModal = true;
    this.cdr.markForCheck();

    this.api.getDocumentChunks(doc.id).subscribe({
      next: (res) => {
        if (res.success) {
          this.chunksList = res.data || [];
        }
        this.loadingChunks = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.loadingChunks = false;
        this.cdr.markForCheck();
      }
    });
  }

  closeChunksModal() {
    this.showChunksModal = false;
    this.chunksDocName = '';
    this.chunksList = [];
  }

  formatBytes(bytes: number, decimals = 2) {
    if (!+bytes) return '0 Bytes';
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
  }
}
