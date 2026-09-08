import { Component, OnInit, ChangeDetectorRef, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { ApiService } from '../core/api';
import { ResponseModal } from '../core/components/response-modal/response-modal';

@Component({
  selector: 'app-defect-triage',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, ResponseModal],
  templateUrl: './defect-triage.html',
  styleUrl: './defect-triage.scss'
})
export class DefectTriage implements OnInit {
  @ViewChild('responseModal') responseModal?: ResponseModal;

  // 2-Step KB Selection: Project -> Document
  projects: any[] = [];
  selectedProjectId: number | null = null;
  selectedProject: any = null;
  loadingProjects = false;

  documents: any[] = [];
  selectedDocId: number | null = null;
  selectedDoc: any = null;
  loadingDocs = false;

  // Contextual inputs / prompt
  defectTitle = '';

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
  promptVersion = 'defect-v2';
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
    this.selectedDocId = null;
    this.selectedDoc = null;
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

  onDocSelect(docId: any) {
    this.selectedDocId = docId ? Number(docId) : null;
    this.selectedDoc = this.documents.find(d => d.id === this.selectedDocId) || null;
    if (this.selectedDoc && !this.defectTitle) {
      this.defectTitle = 'Defect Triage for ' + this.selectedDoc.fileName;
    }
    this.error = '';
    this.cdr.markForCheck();
  }

  removeSelectedDoc() {
    this.selectedDocId = null;
    this.selectedDoc = null;
    this.cdr.markForCheck();
  }

  isInputValid(): boolean {
    return !!(this.selectedProjectId && this.selectedDocId);
  }

  analyze() {
    if (!this.isInputValid()) {
      this.error = 'Please select a Project and Document from Knowledge Base.';
      this.cdr.markForCheck();
      return;
    }

    this.loading = true;
    this.error = '';
    this.cdr.markForCheck();

    const title = this.defectTitle.trim() || ('Defect Triage: ' + (this.selectedDoc?.fileName || 'Document'));

    const payload = {
      title,
      description: `Automated defect triage for ${this.selectedDoc?.fileName || 'knowledge base artifact'}`,
      logs: 'Analyze potential defects, error handlers, and failure modes in the document/codebase.',
      environment: 'Knowledge Base Artifact',
      document_id: this.selectedDocId ? String(this.selectedDocId) : null,
      projectId: this.selectedProjectId,
      projectName: this.selectedProject?.projectName || null,
      documentId: this.selectedDocId,
      documentName: this.selectedDoc?.fileName || null,
      documentVersion: this.selectedDoc?.version || null,
      inputType: 'KNOWLEDGE_BASE'
    };

    this.api.analyzeDefect(payload).subscribe({
      next: (res) => {
        if (res.success && res.data) {
          const aiResponse = res.data;
          this.generatedResult = aiResponse.result || aiResponse;
          this.sources = aiResponse.sources || [];
          this.model = aiResponse.model || 'gemini-3.7-flash';
          this.promptVersion = aiResponse.prompt_version || 'defect-v2';
          this.executionTimeMs = aiResponse.execution_time_ms || 0;
          this.isModalOpen = true;
        } else {
          this.error = res.message || 'Defect analysis failed. Please try again.';
        }
        this.loading = false;
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.loading = false;
        this.error = err.error?.message || 'Failed to analyze defect. Please check service connectivity.';
        this.cdr.markForCheck();
      }
    });
  }

  onAccept(event: { editedData: any; isEdited: boolean }) {
    this.saving = true;
    this.cdr.markForCheck();

    const acceptPayload = {
      title: this.defectTitle.trim() || ('Defect: ' + (this.selectedDoc?.fileName || 'Analysis')),
      description: 'Defect triage from ' + (this.selectedDoc?.fileName || 'knowledge base artifact'),
      logs: event.editedData.evidence || 'Analyze potential defects, error handlers, and failure modes in the document/codebase.',
      environment: 'Knowledge Base',
      stepsToReproduce: event.editedData.suggestedInvestigation || '',
      expectedBehavior: '',
      actualBehavior: '',
      probableRootCause: event.editedData.probableRootCause,
      evidence: event.editedData.evidence,
      suggestedInvestigation: event.editedData.suggestedInvestigation,
      suggestedFix: event.editedData.suggestedFix,
      confidence: event.editedData.confidence || 'HIGH',
      severity: event.editedData.severity || 'MEDIUM',
      priority: event.editedData.priority || 'P2',
      sources: this.sources,
      model: this.model,
      promptVersion: this.promptVersion,
      executionTimeMs: this.executionTimeMs,
      projectId: this.selectedProjectId,
      projectName: this.selectedProject?.projectName || null,
      documentId: this.selectedDocId,
      documentName: this.selectedDoc?.fileName || null,
      documentVersion: this.selectedDoc?.version || null,
      inputType: 'KNOWLEDGE_BASE'
    };

    this.api.acceptDefect(acceptPayload).subscribe({
      next: (res) => {
        this.saving = false;
        if (res.success) {
          if (this.responseModal) {
            this.responseModal.notifySuccess(event.isEdited);
          }
          this.showToast('Defect triage accepted successfully. Saved to database & recorded in Audit History.', 'success');
        } else {
          this.error = res.message || 'Failed to save defect triage.';
        }
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.saving = false;
        this.error = err.error?.message || 'Failed to save defect triage to database.';
        this.showToast('Error saving defect: ' + this.error, 'error');
        this.cdr.markForCheck();
      }
    });
  }

  onReject() {
    this.isModalOpen = false;
    this.showToast('Defect triage dismissed.', 'info');
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
