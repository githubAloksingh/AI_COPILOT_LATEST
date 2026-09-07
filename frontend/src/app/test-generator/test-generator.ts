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

  // Top-level input option: 'kb' (Option A) | 'manual' (Option B)
  mainOption: 'kb' | 'manual' = 'kb';

  // Projects from Knowledge Base (MySQL / H2)
  projects: any[] = [];
  selectedProjectId: number | null = null;
  selectedProject: any = null;
  loadingProjects = false;
  loadingDocs = false;

  // Input Type under Option A: 'BRD' | 'Codebase' | 'BRD + Codebase' | null
  selectedInputType: 'BRD' | 'Codebase' | 'BRD + Codebase' | null = 'BRD';

  // Available documents for the currently selected project
  availableBrds: any[] = [];
  availableCodebases: any[] = [];

  // Selected BRD and Codebase under Option A
  selectedBrdId: number | null = null;
  selectedBrdDoc: any = null;

  selectedCodebaseId: number | null = null;
  selectedCodebaseDoc: any = null;

  // Optional custom instructions/questions
  customTestInstructions = '';

  // Option B: Manual Input fields
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
  promptVersion = 'testcase-v2';
  executionTimeMs = 0;
  modalMeta: { project?: string; inputType?: string; brd?: string; codebase?: string } = {};

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

  isZip(doc: any): boolean {
    if (!doc) return false;
    const name = (doc.fileName || '').toLowerCase();
    const type = (doc.fileType || '').toLowerCase();
    return name.endsWith('.zip') || type.includes('zip');
  }

  onProjectChange(projectId: any) {
    this.selectedProjectId = projectId ? Number(projectId) : null;
    this.selectedProject = this.projects.find(p => p.id === this.selectedProjectId) || null;
    this.selectedBrdId = null;
    this.selectedBrdDoc = null;
    this.selectedCodebaseId = null;
    this.selectedCodebaseDoc = null;
    this.availableBrds = [];
    this.availableCodebases = [];
    this.error = '';

    if (this.selectedProjectId) {
      this.loadingDocs = true;
      this.cdr.markForCheck();
      this.api.getProjectDocuments(this.selectedProjectId).subscribe({
        next: (res) => {
          if (res.success) {
            const completedDocs = (res.data || []).filter((d: any) => d.status === 'COMPLETED');
            this.availableBrds = completedDocs.filter((d: any) => !this.isZip(d));
            this.availableCodebases = completedDocs.filter((d: any) => this.isZip(d));
            
            // Auto-select first available if single
            if (this.availableBrds.length === 1 && this.selectedInputType === 'BRD') {
              this.onBrdSelect(this.availableBrds[0].id);
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

  setMainOption(option: 'kb' | 'manual') {
    this.mainOption = option;
    this.error = '';
    this.cdr.markForCheck();
  }

  onInputTypeChange(type: any) {
    this.selectedInputType = type;
    this.error = '';
    this.cdr.markForCheck();
  }

  removeBrdDoc() {
    this.removeSelectedBrd();
  }

  removeCodebaseDoc() {
    this.removeSelectedCodebase();
  }

  onBrdSelect(docId: any) {
    this.selectedBrdId = docId ? Number(docId) : null;
    this.selectedBrdDoc = this.availableBrds.find(d => d.id === this.selectedBrdId) || null;
    this.error = '';
    this.cdr.markForCheck();
  }

  removeSelectedBrd() {
    this.selectedBrdId = null;
    this.selectedBrdDoc = null;
    this.cdr.markForCheck();
  }

  onCodebaseSelect(docId: any) {
    this.selectedCodebaseId = docId ? Number(docId) : null;
    this.selectedCodebaseDoc = this.availableCodebases.find(d => d.id === this.selectedCodebaseId) || null;
    this.error = '';
    this.cdr.markForCheck();
  }

  removeSelectedCodebase() {
    this.selectedCodebaseId = null;
    this.selectedCodebaseDoc = null;
    this.cdr.markForCheck();
  }

  hasCoverageType(): boolean {
    return Object.values(this.testTypes).some(Boolean);
  }

  isInputValid(): boolean {
    if (!this.hasCoverageType()) return false;

    if (this.mainOption === 'kb') {
      if (!this.selectedProjectId) return false;
      if (!this.selectedInputType) return false;

      if (this.selectedInputType === 'BRD') {
        return !!this.selectedBrdId;
      } else if (this.selectedInputType === 'Codebase') {
        return !!this.selectedCodebaseId;
      } else if (this.selectedInputType === 'BRD + Codebase') {
        return !!this.selectedBrdId && !!this.selectedCodebaseId;
      }
      return false;
    } else {
      return !!(this.manualTitle.trim() && this.manualDescription.trim());
    }
  }

  getValidationMessage(): string | null {
    if (this.mainOption === 'kb') {
      if (!this.selectedProjectId) {
        return 'Please select a Project from Knowledge Base.';
      }
      if (!this.selectedInputType) {
        return 'Please select an Input Type (BRD, Codebase, or BRD + Codebase).';
      }
      if (this.selectedInputType === 'BRD' && !this.selectedBrdId) {
        return 'Please select a BRD document.';
      }
      if (this.selectedInputType === 'Codebase' && !this.selectedCodebaseId) {
        return 'Please select a Codebase ZIP archive.';
      }
      if (this.selectedInputType === 'BRD + Codebase') {
        if (!this.selectedBrdId && !this.selectedCodebaseId) {
          return 'Please select both BRD and Codebase.';
        }
        if (!this.selectedBrdId) {
          return 'Please select a BRD document.';
        }
        if (!this.selectedCodebaseId) {
          return 'Please select a Codebase ZIP.';
        }
      }
    } else {
      if (!this.manualTitle.trim() || !this.manualDescription.trim()) {
        return 'Please enter requirement title and details.';
      }
    }

    if (!this.hasCoverageType()) {
      return 'Please select at least one test coverage type.';
    }

    return null;
  }

  generate() {
    const validationError = this.getValidationMessage();
    if (validationError) {
      this.error = validationError;
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
    let docName: string | null = null;
    let docVer: string | null = null;

    if (this.mainOption === 'kb') {
      const projName = this.selectedProject?.projectName || 'Project';

      if (this.selectedInputType === 'BRD') {
        title = `Test Cases for ${projName} - ${this.selectedBrdDoc?.fileName || 'BRD'}`;
        docId = String(this.selectedBrdId);
        docName = this.selectedBrdDoc?.fileName;
        docVer = this.selectedBrdDoc?.version;
        this.modalMeta = {
          project: projName,
          inputType: 'BRD',
          brd: this.selectedBrdDoc?.fileName
        };
      } else if (this.selectedInputType === 'Codebase') {
        title = `Test Cases for ${projName} - ${this.selectedCodebaseDoc?.fileName || 'Codebase'}`;
        zipDocId = String(this.selectedCodebaseId);
        docName = this.selectedCodebaseDoc?.fileName;
        docVer = this.selectedCodebaseDoc?.version;
        this.modalMeta = {
          project: projName,
          inputType: 'Codebase',
          codebase: this.selectedCodebaseDoc?.fileName
        };
      } else if (this.selectedInputType === 'BRD + Codebase') {
        title = `Test Cases: ${projName} (${this.selectedBrdDoc?.fileName || 'BRD'} & ${this.selectedCodebaseDoc?.fileName || 'Codebase'})`;
        docId = String(this.selectedBrdId);
        zipDocId = String(this.selectedCodebaseId);
        docName = `${this.selectedBrdDoc?.fileName} + ${this.selectedCodebaseDoc?.fileName}`;
        docVer = this.selectedBrdDoc?.version;
        this.modalMeta = {
          project: projName,
          inputType: 'BRD + Codebase',
          brd: this.selectedBrdDoc?.fileName,
          codebase: this.selectedCodebaseDoc?.fileName
        };
      }

      if (this.customTestInstructions.trim()) {
        acceptanceCriteria = this.customTestInstructions.trim();
      }
    } else {
      title = `${this.manualTitle}\n${this.manualDescription}`.trim();
      acceptanceCriteria = this.manualAcceptanceCriteria.trim();
      this.modalMeta = {
        project: 'Manual Input',
        inputType: 'Manual Specification',
        brd: this.manualTitle.trim() || undefined
      };
    }

    const payload: any = {
      requirement: title,
      acceptanceCriteria: acceptanceCriteria,
      testTypes: selectedTypes,
      document_id: docId,
      zip_document_id: zipDocId,
      projectId: this.selectedProjectId,
      projectName: this.selectedProject?.projectName || null,
      documentId: docId ? Number(docId) : (zipDocId ? Number(zipDocId) : null),
      documentName: docName,
      documentVersion: docVer,
      inputType: this.mainOption === 'kb' ? this.selectedInputType : 'MANUAL'
    };

    this.api.generateTestCases(payload).subscribe({
      next: (res) => {
        if (res.success && res.data) {
          const aiResponse = res.data;
          this.generatedResult = aiResponse.result || aiResponse;
          this.sources = aiResponse.sources || [];
          this.model = aiResponse.model || 'gemini-3.7-flash';
          this.promptVersion = aiResponse.prompt_version || 'testcase-v2';
          this.executionTimeMs = aiResponse.execution_time_ms || 0;
          this.isModalOpen = true;
        } else {
          this.error = res.message || 'Test case generation failed. Please try again.';
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
    let docId: number | null = null;
    let docName: string | null = null;
    let docVer: string | null = null;

    if (this.mainOption === 'kb') {
      const projName = this.selectedProject?.projectName || 'Project';
      if (this.selectedInputType === 'BRD') {
        requirementTitle = `${projName}: ${this.selectedBrdDoc?.fileName || 'BRD'}`;
        docId = this.selectedBrdId;
        docName = this.selectedBrdDoc?.fileName;
        docVer = this.selectedBrdDoc?.version;
      } else if (this.selectedInputType === 'Codebase') {
        requirementTitle = `${projName}: ${this.selectedCodebaseDoc?.fileName || 'Codebase'}`;
        docId = this.selectedCodebaseId;
        docName = this.selectedCodebaseDoc?.fileName;
        docVer = this.selectedCodebaseDoc?.version;
      } else if (this.selectedInputType === 'BRD + Codebase') {
        requirementTitle = `${projName}: ${this.selectedBrdDoc?.fileName || 'BRD'} & ${this.selectedCodebaseDoc?.fileName || 'Codebase'}`;
        docId = this.selectedBrdId;
        docName = `${this.selectedBrdDoc?.fileName} + ${this.selectedCodebaseDoc?.fileName}`;
        docVer = this.selectedBrdDoc?.version;
      }
    } else {
      requirementTitle = this.manualTitle.trim() || 'Manual Requirement';
    }

    const acceptPayload = {
      requirement: requirementTitle,
      testCases: items,
      sources: this.sources,
      model: this.model,
      promptVersion: this.promptVersion,
      executionTimeMs: this.executionTimeMs,
      projectId: this.selectedProjectId,
      projectName: this.selectedProject?.projectName || null,
      documentId: docId,
      documentName: docName,
      documentVersion: docVer,
      inputType: this.mainOption === 'kb' ? this.selectedInputType : 'MANUAL'
    };

    this.api.acceptTestCases(acceptPayload).subscribe({
      next: (res) => {
        this.saving = false;
        if (res.success) {
          if (this.responseModal) {
            this.responseModal.notifySuccess(event.isEdited);
          }
          this.showToast('Test cases accepted successfully. Saved to database & recorded in Audit History.', 'success');
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
    this.showToast('Data rejected.', 'info');
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
