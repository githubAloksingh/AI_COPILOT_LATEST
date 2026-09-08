import { Component, OnInit, ChangeDetectorRef, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { ApiService } from '../core/api';
import { ResponseModal } from '../core/components/response-modal/response-modal';

@Component({
  selector: 'app-requirement-assistant',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, ResponseModal],
  templateUrl: './requirement-assistant.html',
  styleUrl: './requirement-assistant.scss'
})
export class RequirementAssistant implements OnInit {
  @ViewChild('responseModal') responseModal?: ResponseModal;

  // Input Mode: 'manual' OR 'kb'
  inputMode: 'manual' | 'kb' = 'kb';

  // Manual Input fields
  title = '';
  description = '';

  // Knowledge Base 2-Step Selection: Project -> Document
  projects: any[] = [];
  selectedProjectId: number | null = null;
  selectedProject: any = null;
  loadingProjects = false;

  documents: any[] = [];
  availableBrds: any[] = [];
  selectedDocumentId: number | null = null;
  selectedDocument: any = null;
  loadingDocs = false;

  customQuery = '';

  // State
  loading = false;
  saving = false;
  error = '';
  toastMessage = '';
  toastType: 'success' | 'info' | 'error' = 'info';

  // Generated Result
  isModalOpen = false;
  generatedResult: any = null;
  sources: any[] = [];
  model = 'gemini-3.7-flash';
  promptVersion = 'requirement-v2';
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
              if (!this.title) {
                this.title = 'Requirements from ' + this.selectedDocument.fileName;
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
    if (this.selectedDocument && !this.title) {
      this.title = 'Requirements from ' + this.selectedDocument.fileName;
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
      return !!(this.selectedProjectId && this.selectedDocumentId);
    }
    return !!(this.title.trim() && this.description.trim());
  }

  getModalMeta() {
    return {
      project: this.selectedProject?.projectName || undefined,
      documentName: this.selectedDocument ? this.selectedDocument.fileName : (this.title || 'Requirement Specification'),
      brd: this.selectedDocument ? this.selectedDocument.fileName : undefined,
      version: this.selectedDocument?.version || undefined,
      inputType: this.inputMode === 'kb' ? 'Knowledge Base Document' : 'Manual Input'
    };
  }

  generate() {
    if (!this.isInputValid()) {
      this.error = this.inputMode === 'kb' 
        ? 'Please select a Project and Document from Knowledge Base.'
        : 'Please enter both Title and Requirement details.';
      return;
    }

    this.loading = true;
    this.error = '';
    this.cdr.markForCheck();

    const desc = this.inputMode === 'kb'
      ? (this.customQuery.trim() || 'Synthesize comprehensive business requirements, user personas, acceptance criteria, and edge cases from document.')
      : this.description.trim();

    const payload: any = {
      title: this.title.trim() || (this.selectedDocument ? 'Requirements from ' + this.selectedDocument.fileName : 'Requirement'),
      description: desc,
      document_id: this.selectedDocumentId ? String(this.selectedDocumentId) : null,
      projectId: this.selectedProjectId,
      projectName: this.selectedProject?.projectName || null,
      documentId: this.selectedDocumentId,
      documentName: this.selectedDocument?.fileName || null,
      documentVersion: this.selectedDocument?.version || null,
      inputType: this.inputMode === 'kb' ? 'KNOWLEDGE_BASE' : 'MANUAL'
    };

    this.api.generateRequirement(payload).subscribe({
      next: (res) => {
        if (res.success && res.data) {
          const aiResponse = res.data;
          this.generatedResult = aiResponse.result || aiResponse;
          this.sources = aiResponse.source_details || aiResponse.sources || [];
          this.model = aiResponse.model || 'gemini-3.7-flash';
          this.promptVersion = aiResponse.prompt_version || 'requirement-v2';
          this.executionTimeMs = aiResponse.execution_time_ms || 0;
          this.isModalOpen = true;
        } else {
          this.error = res.message || 'Generation failed. Please try again.';
        }
        this.loading = false;
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.error = err.error?.message || 'We could not generate the response. Please check services and try again.';
        this.loading = false;
        this.cdr.markForCheck();
      }
    });
  }

  /** Bulk accept — saves all N requirements as separate DB rows with project and document linkage */
  onAcceptAll(event: { requirements: any[]; isEdited: boolean }) {
    this.saving = true;
    this.cdr.markForCheck();

    const brdName = this.selectedDocument?.fileName
      || (this.inputMode === 'manual' ? (this.title || 'Manual Input') : 'Unknown Document');

    const bulkPayload = {
      brdName: brdName,
      projectId: this.selectedProjectId,
      projectName: this.selectedProject?.projectName || null,
      documentId: this.selectedDocumentId,
      documentName: this.selectedDocument?.fileName || null,
      documentVersion: this.selectedDocument?.version || null,
      inputType: this.inputMode === 'kb' ? 'KNOWLEDGE_BASE' : 'MANUAL',
      model: this.model,
      promptVersion: this.promptVersion,
      executionTimeMs: this.executionTimeMs,
      sources: this.sources,
      items: (event.requirements || []).map((req: any) => ({
        requirementId: req.requirementId || null,
        title: req.title || '',
        summary: req.summary || '',
        userStory: req.userStory || '',
        acceptanceCriteria: req.acceptanceCriteria || [],
        assumptions: req.assumptions || [],
        dependencies: req.dependencies || [],
        edgeCases: req.edgeCases || []
      }))
    };

    this.api.acceptAllRequirements(bulkPayload).subscribe({
      next: (res) => {
        this.saving = false;
        if (res.success) {
          if (this.responseModal) {
            this.responseModal.notifySuccess(event.isEdited);
          }
          const count = bulkPayload.items.length;
          this.showToast(`${count} requirement${count > 1 ? 's' : ''} saved successfully to database! Recorded in Audit History.`, 'success');
        } else {
          this.error = res.message || 'Failed to save requirements.';
        }
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.saving = false;
        this.error = err.error?.message || 'Failed to save requirements to database.';
        this.showToast('Error saving requirements: ' + this.error, 'error');
        this.cdr.markForCheck();
      }
    });
  }

  onAccept(event: { editedData: any; isEdited: boolean; selectedIndex?: number }) {
    const req = event.editedData;
    this.onAcceptAll({ requirements: [req], isEdited: event.isEdited });
  }

  onReject() {
    this.isModalOpen = false;
    this.showToast('Generation rejected.', 'info');
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
