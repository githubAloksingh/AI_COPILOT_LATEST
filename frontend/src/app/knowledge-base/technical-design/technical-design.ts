import { Component, OnInit, ChangeDetectorRef, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { ApiService } from '../../core/api';
import { ResponseModal } from '../../core/components/response-modal/response-modal';

@Component({
  selector: 'app-technical-design',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, ResponseModal],
  templateUrl: './technical-design.html',
  styleUrls: ['./technical-design.scss']
})
export class TechnicalDesignComponent implements OnInit {
  @ViewChild('responseModal') responseModal?: ResponseModal;

  inputMode: 'kb' | 'manual' = 'kb';

  // 2-Step KB Selection: Project -> Document
  projects: any[] = [];
  selectedProjectId: number | null = null;
  selectedProject: any = null;
  loadingProjects = false;

  documents: any[] = [];
  selectedDocumentId: number | null = null;
  selectedDocument: any = null;
  loadingDocs = false;

  customPrompt = '';

  // Manual Input
  manualTitle = '';
  manualText = '';

  // State
  loading = false;
  saving = false;
  error = '';
  toastMessage = '';
  toastType: 'success' | 'info' | 'error' = 'info';

  // Generated Response Modal State
  isModalOpen = false;
  generatedResult: any = null;
  sources: string[] = [];
  model = 'gemini-3.7-flash';
  executionTimeMs = 0;

  constructor(
    private api: ApiService,
    private cdr: ChangeDetectorRef
  ) {}

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
    this.documents = [];
    this.error = '';

    if (this.selectedProjectId) {
      this.loadingDocs = true;
      this.cdr.markForCheck();
      this.api.getProjectDocuments(this.selectedProjectId).subscribe({
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
    } else {
      this.cdr.markForCheck();
    }
  }

  setInputMode(mode: 'kb' | 'manual') {
    this.inputMode = mode;
    this.error = '';
    this.cdr.markForCheck();
  }

  onDocumentSelect(docId: any) {
    this.selectedDocumentId = docId ? Number(docId) : null;
    this.selectedDocument = this.documents.find(d => d.id === this.selectedDocumentId) || null;
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
    return !!(this.manualText && this.manualText.trim());
  }

  getModalMeta() {
    return {
      project: this.selectedProject?.projectName || undefined,
      documentName: this.selectedDocument ? this.selectedDocument.fileName : (this.manualTitle || 'Technical Specification'),
      version: this.selectedDocument?.version || undefined,
      inputType: this.inputMode === 'kb' ? 'Knowledge Base Document' : 'Direct Text Input'
    };
  }

  generateTechnicalDesign() {
    if (!this.isInputValid()) {
      this.error = this.inputMode === 'kb'
        ? 'Please select a Project and Document from Knowledge Base.'
        : 'Please enter requirement details for Technical Design.';
      this.cdr.markForCheck();
      return;
    }

    this.loading = true;
    this.error = '';
    this.cdr.markForCheck();

    const desc = this.inputMode === 'kb'
      ? (this.customPrompt.trim() || 'Generate technical architecture design, database schemas, API contracts, and component integrations.')
      : this.manualText.trim();

    const payload: any = {
      title: this.manualTitle.trim() || (this.selectedDocument ? 'Technical Design for ' + this.selectedDocument.fileName : 'Technical Architecture Specification'),
      description: desc,
      priority: 'High',
      document_id: this.inputMode === 'kb' && this.selectedDocumentId ? String(this.selectedDocumentId) : null,
      projectId: this.selectedProjectId,
      projectName: this.selectedProject?.projectName || null,
      documentId: this.selectedDocumentId,
      documentName: this.selectedDocument?.fileName || null,
      documentVersion: this.selectedDocument?.version || null,
      inputType: this.inputMode === 'kb' ? 'KNOWLEDGE_BASE' : 'MANUAL'
    };

    this.api.generateTechnicalDesign(payload).subscribe({
      next: (res) => {
        if (res.success && res.data) {
          const aiResponse = res.data;
          this.generatedResult = aiResponse.result || aiResponse;
          this.sources = aiResponse.sources || [];
          this.model = aiResponse.model || 'gemini-3.7-flash';
          this.executionTimeMs = aiResponse.execution_time_ms || 0;
          this.isModalOpen = true;
        } else {
          this.error = res.message || 'Failed to generate Technical Design. Please try again.';
        }
        this.loading = false;
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.error = err.error?.message || 'We could not generate Technical Design. Please verify AI services.';
        this.loading = false;
        this.cdr.markForCheck();
      }
    });
  }

  onAcceptAll(event: { requirements: any[]; isEdited: boolean }) {
    this.saving = true;
    this.cdr.markForCheck();

    const docName = this.selectedDocument?.fileName || (this.manualTitle || 'Technical Design');

    const bulkPayload = {
      brdName: docName,
      projectId: this.selectedProjectId,
      projectName: this.selectedProject?.projectName || null,
      documentId: this.selectedDocumentId,
      documentName: this.selectedDocument?.fileName || null,
      documentVersion: this.selectedDocument?.version || null,
      inputType: this.inputMode === 'kb' ? 'KNOWLEDGE_BASE' : 'MANUAL',
      model: this.model,
      promptVersion: 'technical-v2',
      executionTimeMs: this.executionTimeMs,
      sources: this.sources,
      items: (event.requirements || []).map((req: any) => ({
        requirementId: req.requirementId || null,
        title: req.title || '',
        summary: req.summary || '',
        userStory: req.userStory || '',
        priority: req.priority || 'High',
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
          this.showToast('Technical Design saved to database and recorded in Audit History.', 'success');
        } else {
          this.error = res.message || 'Failed to save technical design.';
        }
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.saving = false;
        this.error = err.error?.message || 'Failed to save technical design to database.';
        this.showToast('Error saving: ' + this.error, 'error');
        this.cdr.markForCheck();
      }
    });
  }

  onAccept(event: { editedData: any; isEdited: boolean; selectedIndex?: number }) {
    this.onAcceptAll({ requirements: [event.editedData], isEdited: event.isEdited });
  }

  onReject() {
    this.isModalOpen = false;
    this.showToast('Technical Design generation dismissed.', 'info');
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
