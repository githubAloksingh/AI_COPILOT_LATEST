import { Component, OnInit, ChangeDetectorRef, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../core/api';
import { ResponseModal } from '../core/components/response-modal/response-modal';

@Component({
  selector: 'app-release-notes',
  standalone: true,
  imports: [CommonModule, FormsModule, ResponseModal],
  templateUrl: './release-notes.html',
  styleUrl: './release-notes.scss'
})
export class ReleaseNotes implements OnInit {
  @ViewChild('responseModal') responseModal?: ResponseModal;

  // Input Mode: 'manual' OR 'kb'
  inputMode: 'manual' | 'kb' = 'manual';

  // Manual input fields
  version = '1.0.0';
  sprintInformation = '';

  // Knowledge Base selection
  documents: any[] = [];
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
  sources: string[] = [];
  model = 'gemini-3.7-flash';
  promptVersion = 'release-v1';
  executionTimeMs = 0;

  constructor(private api: ApiService, private cdr: ChangeDetectorRef) {}

  ngOnInit() {
    this.loadDocuments();
  }

  loadDocuments() {
    this.loadingDocs = true;
    this.api.getDocuments().subscribe({
      next: (res) => {
        if (res.success) {
          this.documents = (res.data || []).filter((d: any) => d.status === 'COMPLETED');
        }
        this.loadingDocs = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.loadingDocs = false;
        this.cdr.markForCheck();
      }
    });
  }

  setInputMode(mode: 'manual' | 'kb') {
    this.inputMode = mode;
    this.error = '';
    this.cdr.markForCheck();
  }

  onDocumentSelect(docId: any) {
    this.selectedDocumentId = docId ? Number(docId) : null;
    this.selectedDocument = this.documents.find(d => d.id === this.selectedDocumentId) || null;
    if (this.selectedDocument && !this.sprintInformation) {
      this.sprintInformation = 'Generate release notes from ' + this.selectedDocument.fileName;
    }
    this.cdr.markForCheck();
  }

  removeSelectedDocument() {
    this.selectedDocumentId = null;
    this.selectedDocument = null;
    this.cdr.markForCheck();
  }

  isInputValid(): boolean {
    if (this.inputMode === 'kb') {
      return !!this.selectedDocumentId && !!this.version.trim();
    }
    return !!(this.version.trim() && this.sprintInformation.trim());
  }

  generate() {
    if (!this.isInputValid()) {
      this.error = this.inputMode === 'kb' 
        ? 'Please select a document and enter version.'
        : 'Please enter version and sprint information.';
      return;
    }

    this.loading = true;
    this.error = '';
    this.cdr.markForCheck();

    const payload: any = {
      version: this.version || '1.0.0',
      sprintInformation: this.sprintInformation || (this.selectedDocument ? 'Release notes from ' + this.selectedDocument.fileName : 'Release notes'),
      document_id: this.selectedDocumentId ? String(this.selectedDocumentId) : null
    };

    this.api.generateReleaseNotes(payload).subscribe({
      next: (res) => {
        if (res.success && res.data) {
          const aiResponse = res.data;
          this.generatedResult = aiResponse.result || aiResponse;
          // Ensure version is present in data for export
          if (this.generatedResult && !this.generatedResult.version) {
            this.generatedResult.version = this.version;
          }
          this.sources = aiResponse.sources || [];
          this.model = aiResponse.model || 'gemini-3.7-flash';
          this.promptVersion = aiResponse.prompt_version || 'release-v1';
          this.executionTimeMs = aiResponse.execution_time_ms || 0;
          this.isModalOpen = true;
        } else {
          this.error = res.message || 'Release notes generation failed';
        }
        this.loading = false;
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.error = err.error?.message || 'Failed to generate release notes. Please try again.';
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
      executionTimeMs: this.executionTimeMs
    };

    this.api.acceptReleaseNotes(acceptPayload).subscribe({
      next: (res) => {
        this.saving = false;
        if (res.success) {
          if (this.responseModal) {
            this.responseModal.notifySuccess(event.isEdited);
          }
          this.showToast('Release notes accepted successfully. Saved to SQL & Audit History.', 'success');
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
    this.showToast('Data rejected successfully.', 'info');
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
