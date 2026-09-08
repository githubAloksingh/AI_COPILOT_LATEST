import { Component, OnInit, ChangeDetectorRef, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { ApiService } from '../../core/api';
import { ResponseModal } from '../../core/components/response-modal/response-modal';
import { FeatureHistoryComponent } from '../../core/components/feature-history/feature-history';

@Component({
  selector: 'app-user-story',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, ResponseModal, FeatureHistoryComponent],
  templateUrl: './user-story.html',
  styleUrls: ['./user-story.scss']
})
export class UserStoryComponent implements OnInit {
  @ViewChild('responseModal') responseModal?: ResponseModal;

  inputMode: 'kb' | 'manual' = 'kb';

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
  sources: any[] = [];
  model = 'gemini-3.7-flash';
  promptVersion = 'requirement-v2';
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
            // Filter completed BRD/PDF documents
            this.availableBrds = allDocs.filter((d: any) =>
              d.status === 'COMPLETED' && (
                d.fileType === 'BRD' ||
                (d.fileName && !d.fileName.toLowerCase().endsWith('.zip'))
              )
            );
            if (this.availableBrds.length > 0) {
              this.selectedDocument = this.availableBrds[0];
              this.selectedDocumentId = this.availableBrds[0].id;
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
    }
  }

  setInputMode(mode: 'kb' | 'manual') {
    this.inputMode = mode;
    this.error = '';
    this.cdr.markForCheck();
  }

  onBrdSelect(docId: any) {
    this.selectedDocumentId = docId ? Number(docId) : null;
    this.selectedDocument = this.availableBrds.find(d => d.id === this.selectedDocumentId) || null;
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
      documentName: this.selectedDocument ? this.selectedDocument.fileName : (this.manualTitle || 'User Story Requirement'),
      version: this.selectedDocument?.version || undefined,
      inputType: this.inputMode === 'kb' ? 'Knowledge Base Document' : 'Direct Text Input'
    };
  }

  generateUserStory() {
    if (!this.isInputValid()) {
      this.error = this.inputMode === 'kb'
        ? 'Please select a Project and Document from Knowledge Base.'
        : 'Please enter requirement details for User Story generation.';
      this.cdr.markForCheck();
      return;
    }

    this.loading = true;
    this.error = '';
    this.cdr.markForCheck();

    const desc = this.inputMode === 'kb'
      ? (this.customPrompt.trim() || 'Generate comprehensive user stories with detailed acceptance criteria, edge cases, and persona definitions.')
      : this.manualText.trim();

    const payload: any = {
      title: this.manualTitle.trim() || (this.selectedDocument ? 'User Stories for ' + this.selectedDocument.fileName : 'User Story Specification'),
      description: desc,
      priority: 'Medium',
      document_id: this.inputMode === 'kb' && this.selectedDocumentId ? String(this.selectedDocumentId) : null,
      projectId: this.selectedProjectId,
      projectName: this.selectedProject?.projectName || null,
      documentId: this.selectedDocumentId,
      documentName: this.selectedDocument?.fileName || null,
      documentVersion: this.selectedDocument?.version || null,
      inputType: this.inputMode === 'kb' ? 'KNOWLEDGE_BASE' : 'MANUAL'
    };

    this.api.generateUserStory(payload).subscribe({
      next: (res) => {
        if (res.success && res.data) {
          const aiResponse = res.data;
          this.generatedResult = aiResponse.result || aiResponse;
          this.sources = aiResponse.sources || [];
          this.model = aiResponse.model || 'gemini-3.7-flash';
          this.promptVersion = aiResponse.prompt_version || 'requirement-v2';
          this.executionTimeMs = aiResponse.execution_time_ms || 0;
          this.isModalOpen = true;
        } else {
          this.error = res.message || 'Failed to generate User Story. Please try again.';
        }
        this.loading = false;
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.error = err.error?.message || 'We could not generate User Stories. Please verify AI services.';
        this.loading = false;
        this.cdr.markForCheck();
      }
    });
  }

  onAcceptAll(event: { requirements: any[]; isEdited: boolean }) {
    this.saving = true;
    this.cdr.markForCheck();

    const docName = this.selectedDocument?.fileName || (this.manualTitle || 'User Story');

    const bulkPayload = {
      brdName: docName,
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
        priority: req.priority || 'Medium',
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
          this.showToast('User stories saved to database and recorded in Audit History.', 'success');
        } else {
          this.error = res.message || 'Failed to save user stories.';
        }
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.saving = false;
        this.error = err.error?.message || 'Failed to save user stories to database.';
        this.showToast('Error saving user stories: ' + this.error, 'error');
        this.cdr.markForCheck();
      }
    });
  }

  onAccept(event: { editedData: any; isEdited: boolean; selectedIndex?: number }) {
    this.onAcceptAll({ requirements: [event.editedData], isEdited: event.isEdited });
  }

  onReject() {
    this.isModalOpen = false;
    this.showToast('User story generation dismissed.', 'info');
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
