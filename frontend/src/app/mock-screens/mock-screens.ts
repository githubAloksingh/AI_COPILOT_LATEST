import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { ApiService } from '../core/api';

@Component({
  selector: 'app-mock-screens',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './mock-screens.html',
  styleUrls: ['./mock-screens.scss']
})
export class MockScreens implements OnInit, OnDestroy {
  activeView: 'kb' | 'progress' | 'result' = 'kb';

  projects: any[] = [];
  selectedProjectId: number | null = null;
  selectedProject: any = null;
  loadingProjects = false;
  projectsError: string | null = null;

  brdDocuments: any[] = [];
  loadingDocs = false;
  documentsError: string | null = null;
  selectedDocumentId: number | null = null;
  selectedDocument: any = null;
  selectionError: string | null = null;
  startingGeneration = false;

  // Active Job State
  currentJobId: string | null = null;
  currentJob: any = null;
  pollingInterval: any = null;
  generationError: string | null = null;

  // Selected Screen for Zoom / Modal Lightbox
  selectedScreenForPreview: any = null;
  selectedScreenIndex: number = 0;
  showPlanModal = false;

  // Notification Toast
  toastMessage = '';
  toastType: 'info' | 'success' | 'error' = 'info';

  constructor(private api: ApiService, private cdr: ChangeDetectorRef) {}

  ngOnInit() {
    this.loadProjects();
  }

  ngOnDestroy() {
    this.stopPolling();
  }

  // ---------------------------------------------------------------------------
  // 1. PROJECT-SCOPED BRD SELECTION
  // ---------------------------------------------------------------------------
  loadProjects() {
    this.loadingProjects = true;
    this.projectsError = null;
    this.cdr.markForCheck();

    this.api.getProjects().subscribe({
      next: (res) => {
        if (res.success) {
          this.projects = res.data || [];
        } else {
          this.projects = [];
          this.projectsError = res.message || 'Projects could not be loaded.';
        }
        this.loadingProjects = false;
        this.cdr.markForCheck();
      },
      error: (error) => {
        this.projects = [];
        this.projectsError = this.requestError(error, 'Projects could not be loaded.');
        this.loadingProjects = false;
        this.cdr.markForCheck();
      }
    });
  }

  onProjectChange(projectId: number | string | null) {
    this.selectedProjectId = projectId === null || projectId === '' ? null : Number(projectId);
    this.selectedProject = this.projects.find(project => Number(project.id) === this.selectedProjectId) || null;
    this.selectedDocumentId = null;
    this.selectedDocument = null;
    this.brdDocuments = [];
    this.documentsError = null;
    this.selectionError = null;
    this.generationError = null;

    if (!this.selectedProjectId) {
      this.loadingDocs = false;
      this.cdr.markForCheck();
      return;
    }

    this.loadProjectDocuments();
  }

  loadProjectDocuments() {
    if (this.selectedProjectId === null) return;

    const requestedProjectId = this.selectedProjectId;
    this.loadingDocs = true;
    this.documentsError = null;
    this.cdr.markForCheck();

    this.api.getProjectDocuments(this.selectedProjectId).subscribe({
      next: (res) => {
        if (this.selectedProjectId !== requestedProjectId) return;
        if (res.success) {
          this.brdDocuments = (res.data || []).filter((document: any) => this.isEligibleBrd(document));
        } else {
          this.brdDocuments = [];
          this.documentsError = res.message || 'Project documents could not be loaded.';
        }
        this.loadingDocs = false;
        this.cdr.markForCheck();
      },
      error: (error) => {
        if (this.selectedProjectId !== requestedProjectId) return;
        this.brdDocuments = [];
        this.documentsError = this.requestError(error, 'Project documents could not be loaded.');
        this.loadingDocs = false;
        this.cdr.markForCheck();
      }
    });
  }

  isEligibleBrd(document: any): boolean {
    if (!document || String(document.status || '').toUpperCase() !== 'COMPLETED') return false;

    const name = String(document.fileName || '').trim().toLowerCase();
    const type = String(document.fileType || '').trim().toLowerCase();
    if (name.endsWith('.zip') || type.includes('zip') || type.includes('codebase')) return false;

    return type.includes('brd') || type.includes('pdf') || name.endsWith('.pdf');
  }

  onBrdChange(documentId: number | string | null) {
    this.selectedDocumentId = documentId === null || documentId === '' ? null : Number(documentId);
    this.selectedDocument = this.brdDocuments.find(document => Number(document.id) === this.selectedDocumentId) || null;
    this.selectionError = null;
  }

  // ---------------------------------------------------------------------------
  // 2. GENERATION JOB TRIGGER & POLLING
  // ---------------------------------------------------------------------------
  startGeneration() {
    if (this.selectedProjectId === null || this.selectedDocumentId === null || !this.selectedDocument) {
      this.selectionError = 'Select a project and an eligible BRD before generating mock screens.';
      this.cdr.markForCheck();
      return;
    }

    if (this.startingGeneration) return;
    const doc = this.selectedDocument;
    const documentId = this.selectedDocumentId;
    this.generationError = null;
    this.currentJobId = null;
    this.startingGeneration = true;
    this.activeView = 'progress';
    this.currentJob = {
      jobId: 'INITIALIZING...',
      documentId,
      documentName: doc.fileName,
      projectName: this.selectedProject?.projectName || 'Selected project',
      status: 'QUEUED',
      totalScreens: 0,
      completedScreens: 0,
      screens: []
    };
    this.cdr.markForCheck();

    this.api.generateMockScreens(documentId).subscribe({
      next: (res) => {
        this.startingGeneration = false;
        if (res.success && res.data && res.data.jobId) {
          this.currentJobId = res.data.jobId;
          this.currentJob.jobId = this.currentJobId;
          this.currentJob.status = res.data.status || 'QUEUED';
          this.startPolling(this.currentJobId);
        } else {
          this.generationError = res.message || 'Could not queue generation job.';
          this.activeView = 'kb';
          this.showToast(this.generationError, 'error');
        }
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.startingGeneration = false;
        this.generationError = this.requestError(err, 'Failed to start mock screen generation.');
        this.activeView = 'kb';
        this.showToast(this.generationError, 'error');
        this.cdr.markForCheck();
      }
    });
  }

  startPolling(jobId: string) {
    this.stopPolling();
    this.pollJobStatus(jobId);
    this.pollingInterval = setInterval(() => {
      this.pollJobStatus(jobId);
    }, 2000);
  }

  pollJobStatus(jobId: string) {
    this.api.getMockScreenJob(jobId).subscribe({
      next: (res) => {
        if (res.success && res.data) {
          this.currentJob = res.data;
          const status = (this.currentJob.status || '').toUpperCase();

          if (status === 'COMPLETED' || status === 'PARTIAL_SUCCESS') {
            this.stopPolling();
            this.activeView = 'result';
            this.showToast(`Mock screens generated successfully! (${this.currentJob.completedScreens} screens)`, 'success');
          } else if (status === 'FAILED') {
            this.stopPolling();
            this.generationError = this.currentJob.error || 'Generation failed. Please try again.';
            this.showToast(this.generationError, 'error');
          }
        }
        this.cdr.markForCheck();
      },
      error: () => {
        // Continue polling silently unless consecutive network error
      }
    });
  }

  stopPolling() {
    if (this.pollingInterval) {
      clearInterval(this.pollingInterval);
      this.pollingInterval = null;
    }
  }

  // ---------------------------------------------------------------------------
  // 3. RETRY SINGLE SCREEN
  // ---------------------------------------------------------------------------
  retryScreen(screen: any, event?: Event) {
    if (event) event.stopPropagation();
    screen.status = 'GENERATING';
    this.cdr.markForCheck();

    this.api.retryMockScreen(screen.id).subscribe({
      next: (res) => {
        if (res.success && res.data) {
          screen.status = res.data.status;
          screen.imageUrl = res.data.imageUrl;
          screen.errorMessage = null;
          this.showToast(`Screen ${screen.sequence} re-rendered successfully`, 'success');
          // Refresh overall job status
          if (this.currentJobId) {
            this.pollJobStatus(this.currentJobId);
          }
        }
        this.cdr.markForCheck();
      },
      error: (err) => {
        screen.status = 'FAILED';
        screen.errorMessage = err.error?.message || 'Retry failed';
        this.showToast(`Retry failed for Screen ${screen.sequence}`, 'error');
        this.cdr.markForCheck();
      }
    });
  }

  // ---------------------------------------------------------------------------
  // 4. SCREEN PREVIEW / LIGHTBOX
  // ---------------------------------------------------------------------------
  openScreenPreview(screen: any, index: number) {
    this.selectedScreenForPreview = screen;
    this.selectedScreenIndex = index;
    this.cdr.markForCheck();
  }

  closeScreenPreview() {
    this.selectedScreenForPreview = null;
    this.cdr.markForCheck();
  }

  prevScreen() {
    if (!this.currentJob || !this.currentJob.screens) return;
    if (this.selectedScreenIndex > 0) {
      this.selectedScreenIndex--;
      this.selectedScreenForPreview = this.currentJob.screens[this.selectedScreenIndex];
      this.cdr.markForCheck();
    }
  }

  nextScreen() {
    if (!this.currentJob || !this.currentJob.screens) return;
    if (this.selectedScreenIndex < this.currentJob.screens.length - 1) {
      this.selectedScreenIndex++;
      this.selectedScreenForPreview = this.currentJob.screens[this.selectedScreenIndex];
      this.cdr.markForCheck();
    }
  }

  downloadPdf() {
    if (this.currentJobId) {
      const url = this.api.getMockScreenPdfUrl(this.currentJobId);
      window.open(url, '_blank');
    }
  }

  // Helpers
  private requestError(error: any, fallback: string): string {
    return error?.error?.message || error?.message || fallback;
  }

  getScreenImageUrl(screen: any): string {
    if (screen.imageUrl) {
      return this.api.baseUrl.replace(/\/api$/, '') + screen.imageUrl;
    }
    return '';
  }

  getParsedSpec(screen: any): any {
    if (!screen || !screen.specificationJson) return null;
    try {
      return JSON.parse(screen.specificationJson);
    } catch {
      return null;
    }
  }

  showToast(message: string, type: 'info' | 'success' | 'error') {
    this.toastMessage = message;
    this.toastType = type;
    this.cdr.markForCheck();
    setTimeout(() => {
      this.toastMessage = '';
      this.cdr.markForCheck();
    }, 4500);
  }
}
