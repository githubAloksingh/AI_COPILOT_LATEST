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
  selectedInputType: 'BRD' | 'Codebase' | 'BRD + Codebase' = 'BRD';
  availableCodebases: any[] = [];
  selectedBrdId: number | null = null;
  selectedBrdDocument: any = null;
  selectedCodebaseId: number | null = null;
  selectedCodebaseDocument: any = null;

  // State
  loading = false;
  saving = false;
  error = '';
  toastMessage = '';
  toastType: 'success' | 'info' | 'error' = 'info';

  // Generated Result for Modal
  isModalOpen = false;
  generatedResult: any = null;
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
    this.selectedBrdId = null;
    this.selectedBrdDocument = null;
    this.selectedCodebaseId = null;
    this.selectedCodebaseDocument = null;
    this.availableBrds = [];
    this.availableCodebases = [];
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
            this.availableCodebases = allDocs.filter((d: any) =>
              d.status === 'COMPLETED' && (
                d.fileType === 'CODEBASE' ||
                d.fileType === 'ZIP' ||
                (d.fileName && d.fileName.toLowerCase().endsWith('.zip'))
              )
            );
            this.selectedDocument = null;
            this.selectedDocumentId = null;
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
    const sourceDocuments = this.selectedInputType === 'Codebase' ? this.availableCodebases : this.availableBrds;
    this.selectedDocument = sourceDocuments.find(d => d.id === this.selectedDocumentId) || null;
    if (this.selectedInputType === 'Codebase') {
      this.selectedCodebaseId = this.selectedDocumentId;
      this.selectedCodebaseDocument = this.selectedDocument;
    } else {
      this.selectedBrdId = this.selectedDocumentId;
      this.selectedBrdDocument = this.selectedDocument;
    }
    if (this.selectedDocument && !this.sprintInformation) {
      this.sprintInformation = 'Release notes for ' + this.selectedDocument.fileName;
    }
    this.cdr.markForCheck();
  }

  onArtifactSelect(docId: any) {
    this.onBrdSelect(docId);
  }

  onBrdArtifactSelect(docId: any) {
    this.selectedBrdId = docId ? Number(docId) : null;
    this.selectedBrdDocument = this.availableBrds.find(d => d.id === this.selectedBrdId) || null;
    this.selectedDocumentId = this.selectedBrdId;
    this.selectedDocument = this.selectedBrdDocument;
    this.cdr.markForCheck();
  }

  onCodebaseArtifactSelect(docId: any) {
    this.selectedCodebaseId = docId ? Number(docId) : null;
    this.selectedCodebaseDocument = this.availableCodebases.find(d => d.id === this.selectedCodebaseId) || null;
    this.cdr.markForCheck();
  }

  onArtifactTypeChange() {
    this.selectedDocumentId = null;
    this.selectedDocument = null;
    this.selectedBrdId = null;
    this.selectedBrdDocument = null;
    this.selectedCodebaseId = null;
    this.selectedCodebaseDocument = null;
    this.sprintInformation = '';
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
      if (this.selectedInputType === 'BRD + Codebase') {
        return !!(this.selectedProjectId && this.selectedBrdId && this.selectedCodebaseId && this.version.trim());
      }
      return !!(this.selectedProjectId && this.selectedDocumentId && this.version.trim());
    }
    return !!(this.version.trim() && this.sprintInformation.trim());
  }

  getModalMeta() {
    return {
      project: this.selectedProject?.projectName || undefined,
      documentName: this.selectedDocument ? this.selectedDocument.fileName : ('Release Notes v' + this.version),
      brd: this.selectedInputType !== 'Codebase' ? (this.selectedBrdDocument?.fileName || this.selectedDocument?.fileName) : undefined,
      codebase: this.selectedInputType !== 'BRD' ? (this.selectedCodebaseDocument?.fileName || this.selectedDocument?.fileName) : undefined,
      version: this.selectedBrdDocument?.version || this.selectedDocument?.version || this.version || undefined,
      inputType: this.inputMode === 'kb' ? this.selectedInputType : 'Manual Input'
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
      ? `Release Notes for version ${this.version} based on ${this.selectedInputType === 'BRD + Codebase'
        ? `${this.selectedBrdDocument?.fileName} and ${this.selectedCodebaseDocument?.fileName}`
        : this.selectedDocument?.fileName || this.selectedInputType}`
      : this.sprintInformation.trim();

    const payload: any = {
      version: this.version || '1.0.0',
      sprintInformation: sprintDetails,
      document_id: (this.selectedBrdId || this.selectedDocumentId) ? String(this.selectedBrdId || this.selectedDocumentId) : null,
      zip_document_id: this.selectedCodebaseId ? String(this.selectedCodebaseId) : null,
      projectId: this.selectedProjectId,
      projectName: this.selectedProject?.projectName || null,
      documentId: this.selectedDocumentId,
      documentName: this.selectedInputType === 'BRD + Codebase'
        ? `${this.selectedBrdDocument?.fileName} + ${this.selectedCodebaseDocument?.fileName}`
        : this.selectedDocument?.fileName || null,
      documentVersion: this.selectedBrdDocument?.version || this.selectedDocument?.version || null,
      inputType: this.inputMode === 'kb' ? this.selectedInputType : 'MANUAL'
    };

    this.api.generateReleaseNotes(payload).subscribe({
      next: (res) => {
        if (res.success && res.data) {
          const aiResponse = res.data;
          this.generatedResult = aiResponse.result || aiResponse;
          if (this.generatedResult && !this.generatedResult.version) {
            this.generatedResult.version = this.version;
          }
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
      model: this.model,
      promptVersion: this.promptVersion,
      executionTimeMs: this.executionTimeMs,
      projectId: this.selectedProjectId,
      projectName: this.selectedProject?.projectName || null,
      documentId: this.selectedDocumentId,
      documentName: this.selectedDocument?.fileName || null,
      documentVersion: this.selectedDocument?.version || null,
      inputType: this.inputMode === 'kb' ? this.selectedInputType : 'MANUAL'
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
        this.error = err.error?.error?.message || err.error?.message || 'Failed to save release notes to database.';
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
