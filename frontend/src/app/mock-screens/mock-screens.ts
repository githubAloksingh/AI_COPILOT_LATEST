import { ChangeDetectorRef, Component, OnDestroy, OnInit, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { Subscription, timer } from 'rxjs';
import { exhaustMap } from 'rxjs/operators';
import { ApiService } from '../core/api';
import { MockScreensJobResponse } from '../core/models/mock-screens-job';
import { PdfViewerComponent } from '../core/components/pdf-viewer/pdf-viewer';

@Component({
  selector: 'app-mock-screens',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, PdfViewerComponent],
  templateUrl: './mock-screens.html',
  styleUrl: './mock-screens.scss'
})
export class MockScreens implements OnInit, OnDestroy {
  @ViewChild(PdfViewerComponent) pdfViewer?: PdfViewerComponent;

  projects: any[] = [];
  selectedProjectId: number | null = null;
  loadingProjects = false;

  availableBrds: any[] = [];
  selectedBrdId: number | null = null;
  loadingBrds = false;
  isEstimateDialogOpen = false;
  prompt = '';
  jobId: string | null = null;
  isGenerating = false;
  generationError = '';
  private pollingSubscription?: Subscription;
  private readonly activeSubscriptions = new Subscription();
  private destroyed = false;
  private idempotencyKey: string | null = null;
  private idempotencyFingerprint: string | null = null;

  constructor(private api: ApiService, private cdr: ChangeDetectorRef) {}

  ngOnDestroy(): void {
    this.destroyed = true;
    this.stopPolling();
    this.activeSubscriptions.unsubscribe();
  }

  ngOnInit(): void {
    this.loadingProjects = true;
    this.api.getProjects().subscribe({
      next: (res) => {
        if (res.success) {
          this.projects = res.data || [];
        }
        this.loadingProjects = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.loadingProjects = false;
        this.cdr.markForCheck();
      }
    });
  }

  onProjectChange(projectId: any): void {
    this.selectedProjectId = projectId ? Number(projectId) : null;
    this.selectedBrdId = null;
    this.availableBrds = [];
    this.jobId = null;
    this.generationError = '';

    if (!this.selectedProjectId) {
      this.cdr.markForCheck();
      return;
    }

    this.loadingBrds = true;
    this.api.getProjectDocuments(this.selectedProjectId).subscribe({
      next: (res) => {
        if (res.success) {
          this.availableBrds = (res.data || []).filter((document: any) =>
            document.status === 'COMPLETED' && (
              document.fileType === 'BRD' ||
              document.fileType === 'APPLICATION/PDF' ||
              (document.fileName && document.fileName.toLowerCase().endsWith('.pdf'))
            )
          );
        }
        this.loadingBrds = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.loadingBrds = false;
        this.cdr.markForCheck();
      }
    });
  }

  onBrdChange(brdId: any): void {
    this.selectedBrdId = brdId ? Number(brdId) : null;
    this.jobId = null;
    this.generationError = '';
  }

  openEstimateDialog(): void {
    this.generationError = '';
    if (!this.isValidId(this.selectedProjectId)) {
      this.generationError = 'Select a valid project before generating Mock Screens.';
      return;
    }
    if (!this.isValidId(this.selectedBrdId) || this.loadingBrds) {
      this.generationError = 'Select a valid BRD before generating Mock Screens.';
      return;
    }
    if (!this.prompt.trim()) {
      this.generationError = 'Enter a prompt before generating Mock Screens.';
      return;
    }
    if (!this.isGenerating) this.isEstimateDialogOpen = true;
  }

  cancelEstimate(): void {
    this.isEstimateDialogOpen = false;
  }

  continueToGeneration(): void {
    this.isEstimateDialogOpen = false;
    if (!this.isValidId(this.selectedProjectId)) {
      this.generationError = 'Select a valid project before generating Mock Screens.';
      return;
    }
    if (!this.isValidId(this.selectedBrdId) || this.loadingBrds) {
      this.generationError = 'Select a valid BRD before generating Mock Screens.';
      return;
    }
    const prompt = this.prompt.trim();
    if (!prompt) {
      this.generationError = 'Enter a prompt before generating Mock Screens.';
      return;
    }
    if (this.isGenerating) return;

    this.generationError = '';
    this.jobId = null;
    this.isGenerating = true;
    const fingerprint = JSON.stringify([this.selectedProjectId, this.selectedBrdId, prompt]);
    if (fingerprint !== this.idempotencyFingerprint || !this.idempotencyKey) {
      this.idempotencyFingerprint = fingerprint;
      this.idempotencyKey = crypto.randomUUID();
    }
    const idempotencyKey = this.idempotencyKey;
    const request = {
      projectId: this.selectedProjectId,
      brdId: this.selectedBrdId,
      prompt,
      idempotencyKey
    };

    this.activeSubscriptions.add(this.api.createMockScreensJob(request).subscribe({
      next: (response) => {
        const jobId = response.success ? response.data?.jobId : null;
        if (!jobId) {
          this.failGeneration('Unable to start Mock Screens generation. Please try again.');
          return;
        }
        this.jobId = jobId;
        this.startPolling(jobId);
        this.cdr.markForCheck();
      },
      error: () => this.failGeneration('Unable to start Mock Screens generation. Please try again.')
    }));
    this.cdr.markForCheck();
  }

  private startPolling(jobId: string): void {
    this.stopPolling();
    this.pollingSubscription = timer(0, 2000).pipe(
      exhaustMap(() => this.api.getMockScreensJobStatus(jobId))
    ).subscribe({
      next: (response) => {
        if (!response.success || !response.data) {
          this.failGeneration('Unable to retrieve Mock Screens generation status. Please try again.');
          return;
        }

        if (response.data.status === 'COMPLETED') {
          this.stopPolling();
          this.loadCompletedPdf(response.data);
        } else if (response.data.status === 'FAILED') {
          this.clearIdempotencyKey();
          this.failGeneration('Mock Screens generation failed. Please try again.');
        }
        this.cdr.markForCheck();
      },
      error: () => this.failGeneration('Unable to retrieve Mock Screens generation status. Please try again.')
    });
    this.activeSubscriptions.add(this.pollingSubscription);
  }

  private loadCompletedPdf(job: MockScreensJobResponse): void {
    if (!job.pdfPreviewUrl) {
      this.failGeneration('Mock Screens completed, but the final PDF is unavailable. Please try again.');
      return;
    }

    this.activeSubscriptions.add(this.api.getMockScreensPdf(job.pdfPreviewUrl).subscribe({
      next: async (preview) => {
        if (!(await this.isPdf(preview)) || this.destroyed) {
          if (!this.destroyed) {
            this.failGeneration('The completed Mock Screens PDF could not be opened. Please try again.');
          }
          return;
        }
        const fileName = job.pdfFileName || 'Mock_Screens.pdf';
        this.isGenerating = false;
        this.clearIdempotencyKey();
        this.pdfViewer?.openBlob(preview, fileName, preview, fileName);
        this.cdr.markForCheck();
      },
      error: () => this.failGeneration('Unable to retrieve the completed Mock Screens PDF. Please try again.')
    }));
  }

  private clearIdempotencyKey(): void {
    this.idempotencyKey = null;
    this.idempotencyFingerprint = null;
  }

  private failGeneration(message: string): void {
    this.stopPolling();
    this.isGenerating = false;
    this.generationError = message;
    this.cdr.markForCheck();
  }

  private stopPolling(): void {
    this.pollingSubscription?.unsubscribe();
    this.pollingSubscription = undefined;
  }

  private isValidId(value: number | null): value is number {
    return value !== null && Number.isInteger(value) && value > 0;
  }

  private async isPdf(blob: Blob): Promise<boolean> {
    return blob.size >= 5 && (await blob.slice(0, 5).text()) === '%PDF-';
  }
}