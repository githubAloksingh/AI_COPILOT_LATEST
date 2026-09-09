import { Component, OnInit, ChangeDetectorRef, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { ApiService } from '../core/api';
import { ResponseModal } from '../core/components/response-modal/response-modal';
import { FeatureHistoryComponent } from '../core/components/feature-history/feature-history';

@Component({
  selector: 'app-release-notes',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, ResponseModal, FeatureHistoryComponent],
  templateUrl: './release-notes.html',
  styleUrl: './release-notes.scss'
})
export class ReleaseNotes implements OnInit {
  @ViewChild('responseModal') responseModal?: ResponseModal;

  // Input Mode: 'manual' OR 'kb'
  inputMode: 'manual' | 'kb' = 'kb';

  // Manual input fields
  version = '1.0.0';
  sprintInformation = '';

  // 2-Step KB Selection: Project -> Document
  projects: any[] = [];
  selectedProjectId: number | null = null;
  selectedProject: any = null;
  loadingProjects = false;

  documents: any[] = [];
  availableBrds: any[] = [];
  selectedDocumentId: number | null = null;
  selectedDocument: any = null;
  loadingDocs = false;

  // State
  loading = false;
  saving = false;
  error = '';
  toastMessage = '';
  toastType: 'success' | 'info' | 'error' = 'info';

  // Generated Result for Modal
  isModalOpen = false;
  generatedResult: any = null;
  sources: any[] = [];
  model = 'gemini-3.7-flash';
  promptVersion = 'release-v2';
  executionTimeMs = 0;

  constructor(private api: ApiService, private cdr: ChangeDetectorRef) {}

  ngOnInit() {
    this.loadProjects();
  }

  loadProjects() {
    this.loadingProjects = true;
    this.cdr.markForCheck();
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

  onProjectChange(projectId: any) {
    this.selectedProjectId = projectId ? Number(projectId) : null;
    this.selectedProject = this.projects.find(p => p.id === this.selectedProjectId) || null;
    this.selectedDocumentId = null;
    this.selectedDocument = null;
    this.availableBrds = [];
    this.documents = [];
    this.error = '';

    if (this.selectedProjectId) {
      this.loadingDocs = true;
      this.cdr.markForCheck();
      this.api.getProjectDocuments(this.selectedProjectId).subscribe({
        next: (res) => {
          if (res.success) {
            const allDocs = res.data || [];
            this.documents = allDocs;
            this.availableBrds = allDocs.filter((d: any) =>
              d.status === 'COMPLETED' && (
                d.fileType === 'BRD' ||
                (d.fileName && !d.fileName.toLowerCase().endsWith('.zip'))
              )
            );
            if (this.availableBrds.length > 0) {
              this.selectedDocument = this.availableBrds[0];
              this.selectedDocumentId = this.availableBrds[0].id;
              if (!this.sprintInformation) {
                this.sprintInformation = 'Release notes for ' + this.selectedDocument.fileName;
              }
            } else {
              this.selectedDocument = null;
              this.selectedDocumentId = null;
            }
          }
          this.loadingDocs = false;
          this.cdr.markForCheck();
        },
        error: () => {
          this.loadingDocs = false;
          this.cdr.markForCheck();
        }
      });
    } else {
      this.cdr.markForCheck();
    }
  }

  onBrdSelect(docId: any) {
    this.selectedDocumentId = docId ? Number(docId) : null;
    this.selectedDocument = this.availableBrds.find(d => d.id === this.selectedDocumentId) || null;
    if (this.selectedDocument && !this.sprintInformation) {
      this.sprintInformation = 'Release notes for ' + this.selectedDocument.fileName;
    }
    this.cdr.markForCheck();
  }

  setInputMode(mode: 'manual' | 'kb') {
    this.inputMode = mode;
    this.error = '';
    this.cdr.markForCheck();
  }

  removeSelectedDocument() {
    this.selectedDocumentId = null;
    this.selectedDocument = null;
    this.cdr.markForCheck();
  }

  isInputValid(): boolean {
    if (this.inputMode === 'kb') {
      return !!(this.selectedProjectId && this.selectedDocumentId && this.version.trim());
    }
    return !!(this.version.trim() && this.sprintInformation.trim());
  }

  getModalMeta() {
    return {
      project: this.selectedProject?.projectName || undefined,
      documentName: this.selectedDocument ? this.selectedDocument.fileName : ('Release Notes v' + this.version),
      brd: this.selectedDocument ? this.selectedDocument.fileName : undefined,
      version: this.selectedDocument?.version || this.version || undefined,
      inputType: this.inputMode === 'kb' ? 'Knowledge Base Document' : 'Manual Input'
    };
  }

  generate() {
    if (!this.isInputValid()) {
      this.error = this.inputMode === 'kb' 
        ? 'Please select a Project, Document, and enter Release Version.'
        : 'Please enter version and sprint information.';
      this.cdr.markForCheck();
      return;
    }

    this.loading = true;
    this.error = '';
    this.cdr.markForCheck();

    const sprintDetails = this.inputMode === 'kb'
      ? `Release Notes for version ${this.version} based on ${this.selectedDocument?.fileName || 'BRD'}`
      : this.sprintInformation.trim();

    const payload: any = {
      version: this.version || '1.0.0',
      sprintInformation: sprintDetails,
      document_id: this.selectedDocumentId ? String(this.selectedDocumentId) : null,
      projectId: this.selectedProjectId,
      projectName: this.selectedProject?.projectName || null,
      documentId: this.selectedDocumentId,
      documentName: this.selectedDocument?.fileName || null,
      documentVersion: this.selectedDocument?.version || null,
      inputType: this.inputMode === 'kb' ? 'KNOWLEDGE_BASE' : 'MANUAL'
    };

    this.api.generateReleaseNotes(payload).subscribe({
      next: (res) => {
        if (res.success && res.data) {
          const aiResponse = res.data;
          this.generatedResult = aiResponse.result || aiResponse;
          if (this.generatedResult && !this.generatedResult.version) {
            this.generatedResult.version = this.version;
          }
          this.sources = aiResponse.source_details || aiResponse.sources || [];
          this.model = aiResponse.model || 'gemini-3.7-flash';
          this.promptVersion = aiResponse.prompt_version || 'release-v2';
          this.executionTimeMs = aiResponse.execution_time_ms || 0;
          this.isModalOpen = true;
        } else {
          this.error = res.message || 'Release notes generation failed';
        }
        this.loading = false;
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.error = err.error?.message || 'Failed to generate release notes. Please check AI service.';
        this.loading = false;
        this.cdr.markForCheck();
      }
    });
  }

  onAccept(event: { editedData: any; isEdited: boolean }) {
    this.saving = true;
    this.cdr.markForCheck();

    const acceptPayload = {
      version: event.editedData.version || this.version,
      sprintInformation: this.sprintInformation || (this.selectedDocument ? 'Imported from ' + this.selectedDocument.fileName : ''),
      summary: event.editedData.summary,
      newFeatures: event.editedData.newFeatures || [],
      improvements: event.editedData.improvements || [],
      bugFixes: event.editedData.bugFixes || [],
      breakingChanges: event.editedData.breakingChanges || [],
      knownIssues: event.editedData.knownIssues || [],
      technicalNotes: event.editedData.technicalNotes || '',
      sources: this.sources,
      model: this.model,
      promptVersion: this.promptVersion,
      executionTimeMs: this.executionTimeMs,
      projectId: this.selectedProjectId,
      projectName: this.selectedProject?.projectName || null,
      documentId: this.selectedDocumentId,
      documentName: this.selectedDocument?.fileName || null,
      documentVersion: this.selectedDocument?.version || null,
      inputType: this.inputMode === 'kb' ? 'KNOWLEDGE_BASE' : 'MANUAL'
    };

    this.api.acceptReleaseNotes(acceptPayload).subscribe({
      next: (res) => {
        this.saving = false;
        if (res.success) {
          if (this.responseModal) {
            this.responseModal.notifySuccess(event.isEdited);
          }
          this.showToast('Release notes accepted successfully. Saved to database & recorded in Audit History.', 'success');
        } else {
          this.error = res.message || 'Failed to save release notes.';
        }
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.saving = false;
        this.error = err.error?.message || 'Failed to save release notes to database.';
        this.showToast('Error saving release notes: ' + this.error, 'error');
        this.cdr.markForCheck();
      }
    });
  }

  onReject() {
    this.isModalOpen = false;
    this.showToast('Release notes dismissed.', 'info');
    this.cdr.markForCheck();
  }

  showToast(msg: string, type: 'success' | 'info' | 'error' = 'info') {
    this.toastMessage = msg;
    this.toastType = type;
    setTimeout(() => {
      this.toastMessage = '';
      this.cdr.markForCheck();
    }, 4000);
  }
}
