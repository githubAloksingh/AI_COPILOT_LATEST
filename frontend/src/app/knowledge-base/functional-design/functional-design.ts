import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../core/api';
import { ResponseModal } from '../../core/components/response-modal/response-modal';

@Component({
  selector: 'app-functional-design',
  standalone: true,
  imports: [CommonModule, FormsModule, ResponseModal],
  templateUrl: './functional-design.html',
  styleUrls: ['./functional-design.scss']
})
export class FunctionalDesignComponent implements OnInit {
  inputMode: 'kb' | 'manual' = 'kb';

  // KB selection
  documents: any[] = [];
  selectedDocumentId: number | null = null;
  selectedDocument: any = null;
  loadingDocs = false;

  // Manual Input
  manualTitle = '';
  manualText = '';

  // State
  loading = false;
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
      return !!this.selectedDocumentId;
    }
    return !!(this.manualText && this.manualText.trim());
  }

  getModalMeta() {
    return {
      project: this.selectedDocument?.projectName || undefined,
      documentName: this.selectedDocument ? this.selectedDocument.fileName : (this.manualTitle || 'Functional Specification'),
      version: this.selectedDocument?.version || undefined,
      inputType: this.inputMode === 'kb' ? 'Knowledge Base Document' : 'Direct Text Input'
    };
  }

  generateFunctionalDesign() {
    if (!this.isInputValid()) {
      this.error = 'Please select a document or enter text.';
      this.cdr.markForCheck();
      return;
    }

    this.loading = true;
    this.error = '';
    this.cdr.markForCheck();

    const payload: any = {
      title: this.manualTitle.trim() || (this.selectedDocument ? 'Functional Design for ' + this.selectedDocument.fileName : 'Functional Design Specification'),
      description: this.inputMode === 'manual' ? this.manualText.trim() : 'Generate detailed Functional Design specification, modules, user interactions, and system behavior',
      priority: 'High',
      document_id: this.inputMode === 'kb' && this.selectedDocumentId ? String(this.selectedDocumentId) : null
    };

    this.api.generateFunctionalDesign(payload).subscribe({
      next: (res) => {
        if (res.success && res.data) {
          const aiResponse = res.data;
          this.generatedResult = aiResponse.result || aiResponse;
          this.sources = aiResponse.sources || [];
          this.model = aiResponse.model || 'gemini-3.7-flash';
          this.executionTimeMs = aiResponse.execution_time_ms || 0;
          this.isModalOpen = true;
        } else {
          this.error = res.message || 'Failed to generate Functional Design. Please try again.';
        }
        this.loading = false;
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.error = err.error?.message || 'We could not generate Functional Design. Please verify AI services.';
        this.loading = false;
        this.cdr.markForCheck();
      }
    });
  }

  onAcceptAll(event: any) {
    this.isModalOpen = false;
    this.showToast('Functional Design saved successfully.', 'success');
  }

  onReject() {
    this.isModalOpen = false;
    this.showToast('Functional Design generation dismissed.', 'info');
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
