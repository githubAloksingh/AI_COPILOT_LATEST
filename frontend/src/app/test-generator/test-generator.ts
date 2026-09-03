import { Component, OnInit, ChangeDetectorRef, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { ApiService } from '../core/api';
import { ResponseModal } from '../core/components/response-modal/response-modal';

@Component({
  selector: 'app-test-generator',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, ResponseModal],
  templateUrl: './test-generator.html',
  styleUrl: './test-generator.scss'
})
export class TestGenerator implements OnInit {
  @ViewChild('responseModal') responseModal?: ResponseModal;

  // Selected input mode: 'brd' | 'zip' | 'both' | 'manual'
  inputMode: 'brd' | 'zip' | 'both' | 'manual' = 'brd';

  // Knowledge Base Documents
  documents: any[] = [];
  brdDocuments: any[] = [];
  zipDocuments: any[] = [];
  loadingDocs = false;

  // Selected Knowledge Base documents
  selectedBrdId: number | null = null;
  selectedBrdDoc: any = null;

  selectedZipId: number | null = null;
  selectedZipDoc: any = null;

  // Manual Input fields
  manualTitle = '';
  manualDescription = '';
  manualAcceptanceCriteria = '';

  // Test Coverage Types
  testTypes = {
    functional: true,
    edgeCases: true,
    security: false,
    performance: false
  };

  // UI State
  loading = false;
  saving = false;
  error = '';
  toastMessage = '';
  toastType: 'success' | 'info' | 'error' = 'info';

  // Generated Result for Modal
  isModalOpen = false;
  generatedResult: any[] = [];
  sources: string[] = [];
  model = 'gemini-3.7-flash';
  promptVersion = 'testcase-v1';
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
          this.brdDocuments = this.documents.filter(d => !d.fileName.toLowerCase().endsWith('.zip'));
          this.zipDocuments = this.documents.filter(d => 
            d.fileName.toLowerCase().endsWith('.zip') || (d.fileType && d.fileType.toLowerCase().includes('zip'))
          );
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

  setInputMode(mode: 'brd' | 'zip' | 'both' | 'manual') {
    this.inputMode = mode;
    this.error = '';
    this.cdr.markForCheck();
  }

  onBrdSelect(docId: any) {
    this.selectedBrdId = docId ? Number(docId) : null;
    this.selectedBrdDoc = this.documents.find(d => d.id === this.selectedBrdId) || null;
    this.error = '';
    this.cdr.markForCheck();
  }

  removeBrdDoc() {
    this.selectedBrdId = null;
    this.selectedBrdDoc = null;
    this.cdr.markForCheck();
  }

  onZipSelect(docId: any) {
    this.selectedZipId = docId ? Number(docId) : null;
    this.selectedZipDoc = this.documents.find(d => d.id === this.selectedZipId) || null;
    this.error = '';
    this.cdr.markForCheck();
  }

  removeZipDoc() {
    this.selectedZipId = null;
    this.selectedZipDoc = null;
    this.cdr.markForCheck();
  }

  hasCoverageType(): boolean {
    return Object.values(this.testTypes).some(Boolean);
  }

  isInputValid(): boolean {
    if (!this.hasCoverageType()) return false;

    if (this.inputMode === 'brd') {
      return !!this.selectedBrdId;
    } else if (this.inputMode === 'zip') {
      return !!this.selectedZipId;
    } else if (this.inputMode === 'both') {
      return !!this.selectedBrdId && !!this.selectedZipId;
    } else if (this.inputMode === 'manual') {
      return !!(this.manualTitle.trim() && this.manualDescription.trim());
    }
    return false;
  }

  generate() {
    if (!this.isInputValid()) {
      if (!this.hasCoverageType()) {
        this.error = 'Please select at least one test coverage type.';
      } else if (this.inputMode === 'brd' && !this.selectedBrdId) {
        this.error = 'Please select a BRD document from Knowledge Base.';
      } else if (this.inputMode === 'zip' && !this.selectedZipId) {
        this.error = 'Please select a Project ZIP archive from Knowledge Base.';
      } else if (this.inputMode === 'both') {
        if (!this.selectedBrdId && !this.selectedZipId) {
          this.error = 'Please select both a BRD document and a Project ZIP archive from Knowledge Base.';
        } else if (!this.selectedBrdId) {
          this.error = 'Please select a BRD document from Knowledge Base.';
        } else if (!this.selectedZipId) {
          this.error = 'Please select a Project ZIP archive from Knowledge Base.';
        }
      } else if (this.inputMode === 'manual') {
        this.error = 'Please provide both Requirement Title and Problem / Requirement Description.';
      }
      this.cdr.markForCheck();
      return;
    }

    this.loading = true;
    this.error = '';
    this.cdr.markForCheck();

    const selectedTypes: string[] = [];
    if (this.testTypes.functional) selectedTypes.push('Functional Tests');
    if (this.testTypes.edgeCases) selectedTypes.push('Edge & Boundary Cases');
    if (this.testTypes.security) selectedTypes.push('Security & Validation');
    if (this.testTypes.performance) selectedTypes.push('Performance & Load');

    let title = 'Test Cases';
    let acceptanceCriteria = '';
    let docId: string | null = null;
    let zipDocId: string | null = null;

    if (this.inputMode === 'brd') {
      title = this.selectedBrdDoc ? `Test Cases for ${this.selectedBrdDoc.fileName}` : 'BRD Test Cases';
      docId = String(this.selectedBrdId);
    } else if (this.inputMode === 'zip') {
      title = this.selectedZipDoc ? `Test Cases for ${this.selectedZipDoc.fileName}` : 'Project ZIP Test Cases';
      zipDocId = String(this.selectedZipId);
    } else if (this.inputMode === 'both') {
      title = `Test Cases: ${this.selectedBrdDoc?.fileName || 'BRD'} & ${this.selectedZipDoc?.fileName || 'Project ZIP'}`;
      docId = String(this.selectedBrdId);
      zipDocId = String(this.selectedZipId);
    } else if (this.inputMode === 'manual') {
      title = `${this.manualTitle}\n${this.manualDescription}`.trim();
      acceptanceCriteria = this.manualAcceptanceCriteria.trim();
    }

    const payload: any = {
      requirement: title,
      acceptanceCriteria: acceptanceCriteria,
      testTypes: selectedTypes,
      document_id: docId,
      zip_document_id: zipDocId
    };

    this.api.generateTestCases(payload).subscribe({
      next: (res) => {
        if (res.success && res.data) {
          const aiResponse = res.data;
          this.generatedResult = aiResponse.result || aiResponse;
          this.sources = aiResponse.sources || [];
          this.model = aiResponse.model || 'gemini-3.7-flash';
          this.promptVersion = aiResponse.prompt_version || 'testcase-v1';
          this.executionTimeMs = aiResponse.execution_time_ms || 0;
          this.isModalOpen = true;
        } else {
          this.error = res.message || 'Test case generation failed';
        }
        this.loading = false;
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.error = err.error?.message || err.message || 'Failed to generate test cases. Please try again.';
        this.loading = false;
        this.cdr.markForCheck();
      }
    });
  }

  onAccept(event: { editedData: any; isEdited: boolean }) {
    this.saving = true;
    this.cdr.markForCheck();

    const items = Array.isArray(event.editedData) ? event.editedData : (event.editedData.items || []);

    let requirementTitle = 'Generated Test Cases';
    if (this.inputMode === 'brd' && this.selectedBrdDoc) {
      requirementTitle = `BRD: ${this.selectedBrdDoc.fileName}`;
    } else if (this.inputMode === 'zip' && this.selectedZipDoc) {
      requirementTitle = `Project ZIP: ${this.selectedZipDoc.fileName}`;
    } else if (this.inputMode === 'both') {
      requirementTitle = `BRD: ${this.selectedBrdDoc?.fileName || 'BRD'} & ZIP: ${this.selectedZipDoc?.fileName || 'Project'}`;
    } else if (this.inputMode === 'manual') {
      requirementTitle = this.manualTitle.trim() || 'Manual Requirement';
    }

    const acceptPayload = {
      requirement: requirementTitle,
      testCases: items,
      sources: this.sources,
      model: this.model,
      promptVersion: this.promptVersion,
      executionTimeMs: this.executionTimeMs
    };

    this.api.acceptTestCases(acceptPayload).subscribe({
      next: (res) => {
        this.saving = false;
        if (res.success) {
          if (this.responseModal) {
            this.responseModal.notifySuccess(event.isEdited);
          }
          this.showToast('Test cases accepted successfully. Saved to SQL & Audit History.', 'success');
        } else {
          this.error = res.message || 'Failed to save test cases.';
        }
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.saving = false;
        this.error = err.error?.message || 'Failed to save test cases to database.';
        this.showToast('Error saving test cases: ' + this.error, 'error');
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
