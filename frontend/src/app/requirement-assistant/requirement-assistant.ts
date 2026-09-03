import { Component, OnInit, ChangeDetectorRef, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../core/api';
import { ResponseModal } from '../core/components/response-modal/response-modal';

@Component({
  selector: 'app-requirement-assistant',
  standalone: true,
  imports: [CommonModule, FormsModule, ResponseModal],
  templateUrl: './requirement-assistant.html',
  styleUrl: './requirement-assistant.scss'
})
export class RequirementAssistant implements OnInit {
  @ViewChild('responseModal') responseModal?: ResponseModal;

  // Input Mode: 'manual' OR 'kb'
  inputMode: 'manual' | 'kb' = 'manual';

  // Manual Input fields
  title = '';
  description = '';
  priority = 'Medium';

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

  // Generated Result
  isModalOpen = false;
  generatedResult: any = null;
  sources: string[] = [];
  model = 'gemini-3.7-flash';
  promptVersion = 'requirement-v2';
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
    if (this.selectedDocument && !this.title) {
      this.title = 'Requirements from ' + this.selectedDocument.fileName;
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
      return !!this.selectedDocumentId;
    }
    return !!(this.title.trim() && this.description.trim());
  }

  generate() {
    if (!this.isInputValid()) {
      this.error = this.inputMode === 'kb' 
        ? 'Please select a document from Knowledge Base.'
        : 'Please enter both Title and Requirement details.';
      return;
    }

    this.loading = true;
    this.error = '';
    this.cdr.markForCheck();

    const payload: any = {
      title: this.title || (this.selectedDocument ? 'Requirements from ' + this.selectedDocument.fileName : 'Requirement'),
      description: this.description || '',
      priority: this.priority,
      document_id: this.selectedDocumentId ? String(this.selectedDocumentId) : null
    };

    this.api.generateRequirement(payload).subscribe({
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
          this.error = res.message || 'Generation failed. Please try again.';
        }
        this.loading = false;
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.error = err.error?.message || 'We couldn\'t generate the response. Please check services and try again.';
        this.loading = false;
        this.cdr.markForCheck();
      }
    });
  }

  /** Bulk accept — called when user clicks "Accept All N Requirements" */
  onAcceptAll(event: { requirements: any[]; isEdited: boolean }) {
    this.saving = true;
    this.cdr.markForCheck();

    const brdName = this.selectedDocument?.fileName
      || this.selectedDocument?.filename
      || (this.inputMode === 'manual' ? 'Manual Input' : 'Unknown BRD');

    const bulkPayload = {
      brdName: brdName,
      model: this.model,
      promptVersion: this.promptVersion,
      executionTimeMs: this.executionTimeMs,
      sources: this.sources,
      items: (event.requirements || []).map((req: any) => ({
        requirementId: req.requirementId || null,
        title: req.title || '',
        summary: req.summary || '',
        userStory: req.userStory || '',
        priority: req.priority || this.priority || 'Medium',
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
          this.showToast(`${count} requirement${count > 1 ? 's' : ''} saved successfully from "${brdName}". Recorded in Audit History.`, 'success');
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

  /** Legacy single-accept — kept for backward compatibility */
  onAccept(event: { editedData: any; isEdited: boolean; selectedIndex?: number }) {
    const req = event.editedData;
    this.onAcceptAll({ requirements: [req], isEdited: event.isEdited });
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
