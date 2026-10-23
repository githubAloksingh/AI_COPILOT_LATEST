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
  showResultModal = false;
  showConfirmModal = false;
  downloadingPdf = false;

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

  // Notification Toast
  toastMessage = '';
  toastType: 'info' | 'success' | 'error' = 'info';

  // Per-Screen View Tabs: 'mockup' | 'wireframe' | 'explanation' | 'interaction'
  activeScreenTabs: { [screenId: number]: 'mockup' | 'wireframe' | 'explanation' | 'interaction' } = {};
  selectedScreenIndex = 0;
  activeGalleryTab: 'gallery' | 'navigation' = 'gallery';

  pipelineStages = [
    { key: 'ANALYZING', label: '1. Analyzing BRD' },
    { key: 'PLANNING', label: '2. Interaction Planning' },
    { key: 'WIREFRAMING', label: '3. Wireframing' },
    { key: 'GENERATING', label: '4. UI Mockups' },
    { key: 'EXPLAINING', label: '5. Screen Specs' },
    { key: 'COMBINING', label: '6. PDF Compilation' },
    { key: 'COMPLETED', label: '7. Ready' }
  ];

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
  // 2. GENERATION CONFIRM & JOB TRIGGER
  // ---------------------------------------------------------------------------

  /** Show the confirmation popup when user clicks Generate */
  onGenerateClick() {
    if (this.selectedProjectId === null || this.selectedDocumentId === null || !this.selectedDocument) {
      this.selectionError = 'Select a project and an eligible BRD before generating mock screens.';
      this.cdr.markForCheck();
      return;
    }
    this.showConfirmModal = true;
    this.cdr.markForCheck();
  }

  /** Dismiss the confirmation popup without generating */
  cancelGenerate() {
    this.showConfirmModal = false;
    this.cdr.markForCheck();
  }

  /** User confirmed — close popup and start generation */
  confirmAndGenerate() {
    this.showConfirmModal = false;
    this.cdr.markForCheck();
    this.startGeneration();
  }

  /**
   * Estimate generation time based on BRD complexity.
   * Scaled to realistic processing duration: ~2 to 5 minutes.
   */
  getEstimatedTime(): string {
    if (!this.selectedDocument) return '3 – 4 minutes';
    const name = (this.selectedDocument.fileName || '').toLowerCase();
    const len = name.length;
    if (len > 60) return '4 – 5 minutes';
    if (len > 30) return '3 – 4 minutes';
    if (len > 15) return '2 – 3 minutes';
    return '1 – 2 minutes';
  }

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
    this.showResultModal = false;
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
        // Do NOT set startingGeneration = false here — keep spinner visible during polling
        if (res.success && res.data && res.data.jobId) {
          this.currentJobId = res.data.jobId;
          this.currentJob.jobId = this.currentJobId;
          this.currentJob.status = res.data.status || 'QUEUED';
          this.startPolling(this.currentJobId);
        } else {
          this.startingGeneration = false;
          this.generationError = res.message || 'Could not queue generation job.';
          this.showToast(this.generationError, 'error');
        }
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.startingGeneration = false;
        this.generationError = this.requestError(err, 'Failed to start mock screen generation.');
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
            this.startingGeneration = false;
            this.showResultModal = true;
            this.showToast(`Mock screens generated successfully!`, 'success');
          } else if (status === 'FAILED') {
            this.stopPolling();
            this.startingGeneration = false;
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

  closeResultModal() {
    this.showResultModal = false;
    this.cdr.markForCheck();
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

  downloadPdf() {
    if (!this.currentJobId) return;

    this.downloadingPdf = true;
    this.cdr.markForCheck();

    const baseName = this.currentJob?.documentName
      ? this.currentJob.documentName.replace(/\.[^/.]+$/, '')
      : 'mock-screens';
    const fileName = `${baseName}_mock_screens.pdf`;

    this.api.downloadMockScreenPdf(this.currentJobId).subscribe({
      next: (blob) => {
        this.downloadingPdf = false;
        const blobUrl = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = blobUrl;
        link.download = fileName;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(blobUrl);
        this.cdr.markForCheck();
      },
      error: () => {
        this.downloadingPdf = false;
        // Fallback: direct download anchor
        const url = this.api.getMockScreenPdfUrl(this.currentJobId!);
        const link = document.createElement('a');
        link.href = url;
        link.download = fileName;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        this.cdr.markForCheck();
      }
    });
  }

  // ---------------------------------------------------------------------------
  // 4. SCREEN GALLERY TABS & PARSED METADATA HELPERS
  // ---------------------------------------------------------------------------
  getScreenTab(screenId: number): 'mockup' | 'wireframe' | 'explanation' | 'interaction' {
    return this.activeScreenTabs[screenId] || 'mockup';
  }

  setScreenTab(screenId: number, tab: 'mockup' | 'wireframe' | 'explanation' | 'interaction') {
    this.activeScreenTabs[screenId] = tab;
    this.cdr.markForCheck();
  }

  getWireframeUrl(screenId: number): string {
    return this.api.getMockScreenWireframeUrl(screenId);
  }

  getImageUrl(screenId: number): string {
    return this.api.getMockScreenImageUrl(screenId);
  }

  getParsedExplanation(screen: any): any {
    if (!screen) return null;
    if (screen._parsedExplanation !== undefined) return screen._parsedExplanation;
    if (screen.explanation && typeof screen.explanation === 'object') {
      screen._parsedExplanation = screen.explanation;
      return screen._parsedExplanation;
    }
    if (screen.explanationJson) {
      try {
        screen._parsedExplanation = typeof screen.explanationJson === 'string'
          ? JSON.parse(screen.explanationJson)
          : screen.explanationJson;
      } catch {
        screen._parsedExplanation = null;
      }
      return screen._parsedExplanation;
    }
    screen._parsedExplanation = null;
    return null;
  }

  getParsedSpec(screen: any): any {
    if (!screen) return null;
    if (screen._parsedSpec !== undefined) return screen._parsedSpec;
    if (screen.specificationJson) {
      try {
        screen._parsedSpec = typeof screen.specificationJson === 'string'
          ? JSON.parse(screen.specificationJson)
          : screen.specificationJson;
      } catch {
        screen._parsedSpec = null;
      }
      return screen._parsedSpec;
    }
    screen._parsedSpec = null;
    return null;
  }

  getParsedInteraction(screen: any): any {
    if (!screen) return null;
    if (screen._parsedInteraction !== undefined) return screen._parsedInteraction;
    const spec = this.getParsedSpec(screen);
    screen._parsedInteraction = spec?.interaction || null;
    return screen._parsedInteraction;
  }

  getParsedGlobalNav(): any {
    if (!this.currentJob) return null;
    if (this.currentJob._parsedGlobalNav !== undefined) return this.currentJob._parsedGlobalNav;
    if (!this.currentJob.interactionModelJson) {
      this.currentJob._parsedGlobalNav = null;
      return null;
    }
    try {
      this.currentJob._parsedGlobalNav = typeof this.currentJob.interactionModelJson === 'string'
        ? JSON.parse(this.currentJob.interactionModelJson)
        : this.currentJob.interactionModelJson;
    } catch {
      this.currentJob._parsedGlobalNav = null;
    }
    return this.currentJob._parsedGlobalNav;
  }

  isStageCompleted(stageKey: string): boolean {
    const current = (this.currentJob?.status || '').toUpperCase();
    const order = ['QUEUED', 'ANALYZING', 'PLANNING', 'WIREFRAMING', 'GENERATING', 'EXPLAINING', 'COMBINING', 'COMPLETED'];
    const currentIdx = order.indexOf(current);
    const stageIdx = order.indexOf(stageKey);
    return currentIdx > stageIdx || current === 'COMPLETED';
  }

  isStageActive(stageKey: string): boolean {
    const current = (this.currentJob?.status || '').toUpperCase();
    return current === stageKey;
  }

  // Helpers
  private requestError(error: any, fallback: string): string {
    return error?.error?.message || error?.message || fallback;
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
