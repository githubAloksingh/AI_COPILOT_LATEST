import { Component, OnInit, ChangeDetectorRef, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { ApiService } from '../core/api';
import { ResponseModal } from '../core/components/response-modal/response-modal';

export interface KbProject {
  id: string;
  name: string;
  brdDocuments: any[];
  codebaseDocuments: any[];
}

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

  // Raw Knowledge Base documents
  documents: any[] = [];
  loadingDocs = false;

  // Projects derived from Knowledge Base documents
  projects: KbProject[] = [];
  selectedProjectId: string | null = null;
  selectedProject: KbProject | null = null;

  // Input Type under Option A: 'BRD' | 'Codebase' | 'BRD + Codebase' | null
  selectedInputType: 'BRD' | 'Codebase' | 'BRD + Codebase' | null = null;

  // Available documents for the currently selected project
  availableBrds: any[] = [];
  availableCodebases: any[] = [];

  // Selected BRD and Codebase under Option A
  selectedBrdId: number | null = null;
  selectedBrdDoc: any = null;

  selectedCodebaseId: number | null = null;
  selectedCodebaseDoc: any = null;

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
  promptVersion = 'testcase-v1';
  executionTimeMs = 0;
  modalMeta: { project?: string; inputType?: string; brd?: string; codebase?: string } = {};

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
          this.buildProjects(this.documents);
        } else {
          this.buildProjects([]);
        }
        this.loadingDocs = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.buildProjects([]);
        this.loadingDocs = false;
        this.cdr.markForCheck();
      }
    });
  }

  buildProjects(completedDocs: any[]) {
    const projectMap = new Map<string, { id: string; name: string; brds: any[]; codebases: any[] }>();

    for (const doc of completedDocs) {
      const isCodebase = (doc.fileName && doc.fileName.toLowerCase().endsWith('.zip')) ||
                         (doc.fileType && doc.fileType.toLowerCase().includes('zip'));
      const projName = this.extractProjectName(doc.fileName);
      const projId = projName.toLowerCase().replace(/[^a-z0-9]/g, '-');

      if (!projectMap.has(projId)) {
        projectMap.set(projId, {
          id: projId,
          name: projName,
          brds: [],
          codebases: []
        });
      }

      const proj = projectMap.get(projId)!;
      if (isCodebase) {
        proj.codebases.push(doc);
      } else {
        proj.brds.push(doc);
      }
    }

    const result: KbProject[] = [];
    for (const item of projectMap.values()) {
      result.push({
        id: item.id,
        name: item.name,
        brdDocuments: item.brds,
        codebaseDocuments: item.codebases
      });
    }

    // If multiple projects exist, also prepend "All Knowledge Base Projects"
    if (result.length > 1) {
      const allBrds = completedDocs.filter(d => 
        !(d.fileName && d.fileName.toLowerCase().endsWith('.zip')) && 
        !(d.fileType && d.fileType.toLowerCase().includes('zip'))
      );
      const allCodebases = completedDocs.filter(d => 
        (d.fileName && d.fileName.toLowerCase().endsWith('.zip')) || 
        (d.fileType && d.fileType.toLowerCase().includes('zip'))
      );
      result.unshift({
        id: 'all-kb-projects',
        name: 'All Knowledge Base Projects',
        brdDocuments: allBrds,
        codebaseDocuments: allCodebases
      });
    } else if (result.length === 0) {
      // Fallback default project if no documents yet
      result.push({
        id: 'default-project',
        name: 'Default Project',
        brdDocuments: [],
        codebaseDocuments: []
      });
    }

    this.projects = result;

    // Restore selected project if previously selected
    if (this.selectedProjectId) {
      this.selectedProject = this.projects.find(p => p.id === this.selectedProjectId) || null;
      if (this.selectedProject) {
        this.availableBrds = this.selectedProject.brdDocuments;
        this.availableCodebases = this.selectedProject.codebaseDocuments;
      }
    }
  }

  extractProjectName(fileName: string): string {
    if (!fileName) return 'Default Project';
    const cleanName = fileName.replace(/\.[^/.]+$/, '');

    // Check delimiters: ' - ', '_', ' / ', ':'
    const parts = cleanName.split(/[-_:]/);
    if (parts.length > 1) {
      const candidate = parts[0].trim();
      if (candidate.length > 1 && !/^(brd|doc|document|code|codebase|repo|file|spec|req|test)$/i.test(candidate)) {
        return candidate.charAt(0).toUpperCase() + candidate.slice(1);
      }
    }

    // Match common domain keywords
    const lower = cleanName.toLowerCase();
    if (lower.includes('copilot')) return 'AI Work Copilot';
    if (lower.includes('bank')) return 'Banking Application';
    if (lower.includes('ecom') || lower.includes('store') || lower.includes('shop')) return 'E-Commerce Platform';
    if (lower.includes('hrms') || lower.includes('employee')) return 'HRMS Portal';
    if (lower.includes('payment')) return 'Payment Gateway';

    return 'Default Project';
  }

  setMainOption(option: 'kb' | 'manual') {
    this.mainOption = option;
    this.error = '';
    this.cdr.markForCheck();
  }

  onProjectChange(projectId: any) {
    this.selectedProjectId = projectId || null;
    this.selectedProject = this.projects.find(p => p.id === this.selectedProjectId) || null;

    if (this.selectedProject) {
      this.availableBrds = this.selectedProject.brdDocuments;
      this.availableCodebases = this.selectedProject.codebaseDocuments;
    } else {
      this.availableBrds = [];
      this.availableCodebases = [];
      this.selectedInputType = null;
    }

    // Reset document selections when project changes
    this.selectedBrdId = null;
    this.selectedBrdDoc = null;
    this.selectedCodebaseId = null;
    this.selectedCodebaseDoc = null;
    this.error = '';
    this.cdr.markForCheck();
  }

  onInputTypeChange(type: any) {
    this.selectedInputType = type || null;

    // Reset irrelevant selections based on chosen type
    if (this.selectedInputType === 'BRD') {
      this.selectedCodebaseId = null;
      this.selectedCodebaseDoc = null;
    } else if (this.selectedInputType === 'Codebase') {
      this.selectedBrdId = null;
      this.selectedBrdDoc = null;
    }
    this.error = '';
    this.cdr.markForCheck();
  }

  onBrdSelect(docId: any) {
    this.selectedBrdId = docId ? Number(docId) : null;
    this.selectedBrdDoc = this.availableBrds.find(d => d.id === this.selectedBrdId) || null;
    this.error = '';
    this.cdr.markForCheck();
  }

  removeBrdDoc() {
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

  removeCodebaseDoc() {
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
      // Option B: Manual Input
      return !!(this.manualTitle.trim() && this.manualDescription.trim());
    }
  }

  getValidationMessage(): string | null {
    if (this.mainOption === 'kb') {
      if (!this.selectedProjectId) {
        return 'No project selected.';
      }
      if (!this.selectedInputType) {
        return 'Please select an Input Type (BRD, Codebase, or BRD + Codebase).';
      }
      if (this.selectedInputType === 'BRD' && !this.selectedBrdId) {
        return 'Please select a BRD.';
      }
      if (this.selectedInputType === 'Codebase' && !this.selectedCodebaseId) {
        return 'Please select a codebase.';
      }
      if (this.selectedInputType === 'BRD + Codebase') {
        if (!this.selectedBrdId && !this.selectedCodebaseId) {
          return 'Please select both BRD and Codebase.';
        }
        if (!this.selectedBrdId) {
          return 'Please select a BRD.';
        }
        if (!this.selectedCodebaseId) {
          return 'Please select a codebase.';
        }
      }
    } else {
      if (!this.manualTitle.trim() || !this.manualDescription.trim()) {
        return 'Please enter manual input.';
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

    if (this.mainOption === 'kb') {
      const projName = this.selectedProject?.name || 'Knowledge Base Project';

      if (this.selectedInputType === 'BRD') {
        title = `Test Cases for ${projName} - ${this.selectedBrdDoc?.fileName || 'BRD'}`;
        docId = String(this.selectedBrdId);
        this.modalMeta = {
          project: projName,
          inputType: 'BRD',
          brd: this.selectedBrdDoc?.fileName
        };
      } else if (this.selectedInputType === 'Codebase') {
        title = `Test Cases for ${projName} - ${this.selectedCodebaseDoc?.fileName || 'Codebase'}`;
        zipDocId = String(this.selectedCodebaseId);
        this.modalMeta = {
          project: projName,
          inputType: 'Codebase',
          codebase: this.selectedCodebaseDoc?.fileName
        };
      } else if (this.selectedInputType === 'BRD + Codebase') {
        title = `Test Cases: ${projName} (${this.selectedBrdDoc?.fileName || 'BRD'} & ${this.selectedCodebaseDoc?.fileName || 'Codebase'})`;
        docId = String(this.selectedBrdId);
        zipDocId = String(this.selectedCodebaseId);
        this.modalMeta = {
          project: projName,
          inputType: 'BRD + Codebase',
          brd: this.selectedBrdDoc?.fileName,
          codebase: this.selectedCodebaseDoc?.fileName
        };
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
    if (this.mainOption === 'kb') {
      const projName = this.selectedProject?.name || 'Project';
      if (this.selectedInputType === 'BRD') {
        requirementTitle = `${projName}: ${this.selectedBrdDoc?.fileName || 'BRD'}`;
      } else if (this.selectedInputType === 'Codebase') {
        requirementTitle = `${projName}: ${this.selectedCodebaseDoc?.fileName || 'Codebase'}`;
      } else if (this.selectedInputType === 'BRD + Codebase') {
        requirementTitle = `${projName}: ${this.selectedBrdDoc?.fileName || 'BRD'} & ${this.selectedCodebaseDoc?.fileName || 'Codebase'}`;
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
