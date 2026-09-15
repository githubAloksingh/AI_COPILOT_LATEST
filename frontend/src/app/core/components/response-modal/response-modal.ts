import { Component, Input, Output, EventEmitter, OnInit, ChangeDetectorRef, OnChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ExportService } from '../../services/export.service';

@Component({
  selector: 'app-response-modal',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './response-modal.html',
  styleUrl: './response-modal.scss'
})
export class ResponseModal implements OnInit, OnChanges {
  @Input() isOpen = false;
  @Input() type: 'requirement' | 'testcase' | 'defect' | 'releasenote' | 'userstory' | 'functionaldesign' | 'technicaldesign' = 'requirement';
  @Input() title = 'Generated AI Response';
  @Input() data: any = null;
  @Input() model = 'gemini-3.7-flash';
  @Input() promptVersion = '';
  @Input() executionTimeMs = 0;
  @Input() saving = false;
  @Input() meta?: { project?: string; inputType?: string; brd?: string; codebase?: string; documentName?: string; version?: string };

  @Output() close = new EventEmitter<void>();
  /** For requirement type: emits all requirements (bulk) */
  @Output() acceptAll = new EventEmitter<{ requirements: any[]; isEdited: boolean }>();
  /** For non-requirement types: emits single edited data */
  @Output() accept = new EventEmitter<{ editedData: any; isEdited: boolean; selectedIndex?: number }>();
  @Output() reject = new EventEmitter<void>();

  // ── View Mode ──────────────────────────────────────────────────────────────
  mode: 'VIEW' | 'EDIT_ALL' = 'VIEW';
  showConfirmPopup = false;
  showSuccessPopup = false;
  successMessage = '';
  isEdited = false;

  /** Selected tab index for VIEW mode browsing */
  selectedReqIndex = 0;

  // ── Edit Mode ──────────────────────────────────────────────────────────────
  /** Deep copy of all requirements for editing (used in EDIT_ALL mode) */
  editableRequirements: any[] = [];

  /** Track which panels are collapsed in edit mode */
  collapsedPanels: boolean[] = [];

  /** For non-requirement types */
  editableData: any = {};

  readonly releaseNoteLists = [
    { key: 'newFeatures', label: 'New Features', color: '#10b981' },
    { key: 'improvements', label: 'Improvements', color: '#3b82f6' },
    { key: 'bugFixes', label: 'Bug Fixes', color: '#f59e0b' },
    { key: 'breakingChanges', label: 'Breaking Changes', color: '#ef4444' },
    { key: 'knownIssues', label: 'Known Issues', color: '#8b5cf6' }
  ];

  // ── Per-Requirement Inline Edit ───────────────────────────────────────────
  /** Index of requirement currently being inline-edited (-1 = none) */
  editingIndex = -1;
  /** Deep copy of the requirement being edited (scratch copy) */
  perReqEditable: any = null;

  editingSectionTarget: any = null;
  editingSectionKey: string | number = '';
  sectionDraft = '';
  isNewCriterion = false;
  criterionValidationError = '';

  // ── Toast ──────────────────────────────────────────────────────────────────
  toastMessage = '';
  toastType: 'success' | 'error' | 'info' = 'info';

  constructor(private exportService: ExportService, private cdr: ChangeDetectorRef) {}

  ngOnInit() {
    this.initEditableCopy();
  }

  ngOnChanges() {
    this.initEditableCopy();
  }

  initEditableCopy() {
    if (this.data) {
      this.editableData = JSON.parse(JSON.stringify(this.data));
      const list = this.requirementList;
      this.editableRequirements = JSON.parse(JSON.stringify(list));
      this.collapsedPanels = list.map(() => false);
    }
  }

  // ── Requirement Helpers ────────────────────────────────────────────────────
  get requirementList(): any[] {
    if (!this.data) return [];
    if (Array.isArray(this.data)) return this.data;
    if (Array.isArray(this.data.requirements) && this.data.requirements.length > 0) {
      return this.data.requirements;
    }
    if (Array.isArray(this.data.userStories) && this.data.userStories.length > 0) {
      return this.data.userStories;
    }
    if (Array.isArray(this.data.items) && this.data.items.length > 0) {
      return this.data.items;
    }
    if (Array.isArray(this.data.result) && this.data.result.length > 0) {
      return this.data.result;
    }
    return [this.data];
  }

  get currentRequirement(): any {
    const list = this.requirementList;
    if (list.length === 0) return null;
    const idx = Math.min(Math.max(0, this.selectedReqIndex), list.length - 1);
    return list[idx];
  }

  selectRequirement(index: number) {
    // Cancel any unsaved new list item across ALL sections before switching tabs
    if (this.isNewCriterion) {
      this.cancelActiveListEdit();
    }
    this.selectedReqIndex = index;
    this.cdr.markForCheck();
  }

  // ── Per-Requirement Edit ───────────────────────────────────────────────────
  editReq(index: number) {
    this.editingIndex = index;
    // Work on the live list so saved edits persist when switching tabs
    const list = this.requirementList;
    this.perReqEditable = JSON.parse(JSON.stringify(list[index]));
    this.cdr.markForCheck();
  }

  saveReq(index: number) {
    if (this.perReqEditable === null) return;
    // Patch the value back into the original data object
    const list = this.requirementList;
    Object.assign(list[index], this.perReqEditable);
    this.editingIndex = -1;
    this.perReqEditable = null;
    this.isEdited = true;
    this.cdr.markForCheck();
  }

  cancelReq() {
    this.editingIndex = -1;
    this.perReqEditable = null;
    this.cdr.markForCheck();
  }

  editSection(target: any, key: string | number) {
    if (!target || target[key] === undefined) return;
    this.editingSectionTarget = target;
    this.editingSectionKey = key;
    const value = target[key];
    this.sectionDraft = Array.isArray(value)
      ? value.join('\n')
      : (value && typeof value === 'object' ? this.getItemText(value) : String(value ?? ''));
    this.criterionValidationError = '';
    this.cdr.markForCheck();
  }

  isEditingSection(target: any, key: string | number): boolean {
    return this.editingSectionTarget === target && this.editingSectionKey === key;
  }

  saveSection() {
    if (!this.editingSectionTarget || this.editingSectionKey === '') return;
    const currentValue = this.editingSectionTarget[this.editingSectionKey];
    if (typeof currentValue === 'number') {
      const num = Number(this.sectionDraft);
      this.editingSectionTarget[this.editingSectionKey] = isNaN(num) ? this.sectionDraft : num;
    } else if (Array.isArray(currentValue)) {
      this.editingSectionTarget[this.editingSectionKey] = this.sectionDraft.split('\n').map(value => value.trim()).filter(Boolean);
    } else if (currentValue && typeof currentValue === 'object') {
      this.editingSectionTarget[this.editingSectionKey] = { ...currentValue, text: this.sectionDraft };
    } else {
      this.editingSectionTarget[this.editingSectionKey] = this.sectionDraft;
    }
    this.isEdited = true;
    this.editingSectionTarget = null;
    this.editingSectionKey = '';
    this.sectionDraft = '';
    this.criterionValidationError = '';
    this.cdr.markForCheck();
  }

  cancelSection() {
    this.editingSectionTarget = null;
    this.editingSectionKey = '';
    this.sectionDraft = '';
    this.criterionValidationError = '';
    this.cdr.markForCheck();
  }

  addReleaseNoteItem(fieldKey: string) {
    if (!this.data) this.data = {};
    if (!Array.isArray(this.data[fieldKey])) this.data[fieldKey] = [];
    const newIndex = this.data[fieldKey].length;
    this.data[fieldKey].push('');
    this.editingSectionTarget = this.data[fieldKey];
    this.editingSectionKey = newIndex;
    this.sectionDraft = '';
    this.isEdited = true;
    this.cdr.markForCheck();
  }

  // ── Generic List CRUD — works for acceptanceCriteria, businessRules, assumptions, dependencies, edgeCases ──

  /** Cancel any active unsaved list item without needing the field key */
  cancelActiveListEdit() {
    if (this.isNewCriterion && Array.isArray(this.editingSectionTarget) && typeof this.editingSectionKey === 'number') {
      const arr = this.editingSectionTarget as any[];
      if (this.editingSectionKey >= 0 && this.editingSectionKey < arr.length) {
        arr.splice(this.editingSectionKey, 1);
      }
    }
    this.isNewCriterion = false;
    this.criterionValidationError = '';
    this.editingSectionTarget = null;
    this.editingSectionKey = '';
    this.sectionDraft = '';
    this.cdr.markForCheck();
  }

  /** Add a new empty item to any list field on req and immediately enter edit mode */
  addNewListItem(req: any, fieldKey: string) {
    if (!req) return;
    if (!Array.isArray(req[fieldKey])) {
      req[fieldKey] = [];
    }
    // Discard any other unsaved new item before opening a new editor
    if (this.isNewCriterion) {
      this.cancelActiveListEdit();
    }
    const newIndex = req[fieldKey].length;
    req[fieldKey].push({ text: '', grounding: 'DERIVED', source: [] });
    this.isNewCriterion = true;
    this.criterionValidationError = '';
    this.editingSectionTarget = req[fieldKey];
    this.editingSectionKey = newIndex;
    this.sectionDraft = '';
    this.isEdited = true;
    this.cdr.markForCheck();

    setTimeout(() => {
      const el = document.getElementById(`list-editor-${fieldKey}-${newIndex}`) as HTMLTextAreaElement;
      if (el) {
        el.focus();
        el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
    }, 50);
  }

  /** Enter edit mode for an existing list item */
  editExistingListItem(req: any, fieldKey: string, index: number) {
    const arr = req?.[fieldKey];
    if (!Array.isArray(arr) || index < 0 || index >= arr.length) return;
    // Discard any unsaved new item before switching to another editor
    if (this.isNewCriterion) {
      this.cancelActiveListEdit();
    }
    this.isNewCriterion = false;
    this.criterionValidationError = '';
    this.editingSectionTarget = arr;
    this.editingSectionKey = index;
    this.sectionDraft = this.getItemText(arr[index]);
    this.cdr.markForCheck();

    setTimeout(() => {
      const el = document.getElementById(`list-editor-${fieldKey}-${index}`) as HTMLTextAreaElement;
      if (el) {
        el.focus();
        el.select();
      }
    }, 50);
  }

  /** Save the currently edited list item — validates non-empty */
  saveListItem(req: any, fieldKey: string, index: number) {
    const text = (this.sectionDraft || '').trim();
    if (!text) {
      this.criterionValidationError = fieldKey === 'acceptanceCriteria'
        ? 'Acceptance criterion cannot be empty.'
        : 'This field cannot be empty.';
      this.cdr.markForCheck();
      return;
    }
    const arr = req?.[fieldKey];
    if (Array.isArray(arr) && index >= 0 && index < arr.length) {
      const current = arr[index];
      arr[index] = (current && typeof current === 'object')
        ? { ...current, text }
        : { text, grounding: 'DERIVED', source: [] };
    }
    this.isEdited = true;
    this.isNewCriterion = false;
    this.criterionValidationError = '';
    this.editingSectionTarget = null;
    this.editingSectionKey = '';
    this.sectionDraft = '';
    this.cdr.markForCheck();
  }

  /** Cancel editing — removes the item if it was a newly added unsaved item */
  cancelListItem(req: any, fieldKey: string, index: number) {
    if (this.isNewCriterion) {
      const arr = req?.[fieldKey];
      if (Array.isArray(arr) && index >= 0 && index < arr.length) {
        arr.splice(index, 1);
      }
    }
    this.isNewCriterion = false;
    this.criterionValidationError = '';
    this.editingSectionTarget = null;
    this.editingSectionKey = '';
    this.sectionDraft = '';
    this.cdr.markForCheck();
  }

  /** Delete an existing list item — adjusts editor pointer if needed */
  deleteListItem(req: any, fieldKey: string, index: number) {
    const arr = req?.[fieldKey];
    if (!Array.isArray(arr) || index < 0 || index >= arr.length) return;

    if (this.editingSectionTarget === arr && this.editingSectionKey === index) {
      // Deleting the currently-edited item — close the editor
      this.isNewCriterion = false;
      this.criterionValidationError = '';
      this.editingSectionTarget = null;
      this.editingSectionKey = '';
      this.sectionDraft = '';
    } else if (this.editingSectionTarget === arr && typeof this.editingSectionKey === 'number' && this.editingSectionKey > index) {
      // Deleting an item above the currently-edited item — shift the pointer down
      this.editingSectionKey = Number(this.editingSectionKey) - 1;
    }

    arr.splice(index, 1);
    this.isEdited = true;
    this.cdr.markForCheck();
  }

  // ── Acceptance Criteria: backward-compat wrappers (keep HTML bindings working) ──
  addNewAcceptanceCriterion(req: any)              { this.addNewListItem(req, 'acceptanceCriteria'); }
  editExistingCriterion(req: any, i: number)       { this.editExistingListItem(req, 'acceptanceCriteria', i); }
  saveCriterion(req: any, i: number)               { this.saveListItem(req, 'acceptanceCriteria', i); }
  cancelCriterion(req: any, i: number)             { this.cancelListItem(req, 'acceptanceCriteria', i); }
  deleteCriterion(req: any, i: number)             { this.deleteListItem(req, 'acceptanceCriteria', i); }

  // ── Functional Design List & Table Helpers ───────────────────────────────
  addNewMainFlowStep(fd: any) {
    if (!fd) return;
    if (!Array.isArray(fd.mainFlow)) fd.mainFlow = [];
    const nextStep = fd.mainFlow.length + 1;
    const newStep = {
      step: nextStep,
      actor: 'User',
      action: 'Enter user action',
      systemResponse: 'Enter system response'
    };
    fd.mainFlow.push(newStep);
    this.isEdited = true;
    this.editSection(newStep, 'action');
    this.cdr.markForCheck();
  }

  deleteMainFlowStep(fd: any, index: number) {
    if (!fd || !Array.isArray(fd.mainFlow)) return;
    if (index >= 0 && index < fd.mainFlow.length) {
      if (this.editingSectionTarget === fd.mainFlow[index]) {
        this.cancelSection();
      }
      fd.mainFlow.splice(index, 1);
      fd.mainFlow.forEach((s: any, idx: number) => {
        if (s && typeof s === 'object') s.step = idx + 1;
      });
      this.isEdited = true;
      this.cdr.markForCheck();
    }
  }

  addNewActor(fd: any) {
    if (!fd) return;
    if (!Array.isArray(fd.actors)) fd.actors = [];
    const newActor = { name: 'New Actor', description: 'Actor description', grounding: 'EXPLICIT' };
    fd.actors.push(newActor);
    this.isEdited = true;
    this.editSection(newActor, 'name');
    this.cdr.markForCheck();
  }

  deleteActor(fd: any, index: number) {
    if (!fd || !Array.isArray(fd.actors)) return;
    if (index >= 0 && index < fd.actors.length) {
      if (this.editingSectionTarget === fd.actors[index]) this.cancelSection();
      fd.actors.splice(index, 1);
      this.isEdited = true;
      this.cdr.markForCheck();
    }
  }

  addNewValidation(fd: any) {
    if (!fd) return;
    if (!Array.isArray(fd.validations)) fd.validations = [];
    const newVal = { field: 'Field Name', rule: 'Validation rule description', grounding: 'EXPLICIT' };
    fd.validations.push(newVal);
    this.isEdited = true;
    this.editSection(newVal, 'rule');
    this.cdr.markForCheck();
  }

  deleteValidation(fd: any, index: number) {
    if (!fd || !Array.isArray(fd.validations)) return;
    if (index >= 0 && index < fd.validations.length) {
      if (this.editingSectionTarget === fd.validations[index]) this.cancelSection();
      fd.validations.splice(index, 1);
      this.isEdited = true;
      this.cdr.markForCheck();
    }
  }

  addNewErrorHandling(fd: any) {
    if (!fd) return;
    if (!Array.isArray(fd.errorHandling)) fd.errorHandling = [];
    const newEh = { scenario: 'Error Scenario', expectedBehavior: 'Expected error handling behavior' };
    fd.errorHandling.push(newEh);
    this.isEdited = true;
    this.editSection(newEh, 'scenario');
    this.cdr.markForCheck();
  }

  deleteErrorHandling(fd: any, index: number) {
    if (!fd || !Array.isArray(fd.errorHandling)) return;
    if (index >= 0 && index < fd.errorHandling.length) {
      if (this.editingSectionTarget === fd.errorHandling[index]) this.cancelSection();
      fd.errorHandling.splice(index, 1);
      this.isEdited = true;
      this.cdr.markForCheck();
    }
  }

  addNewInput(fd: any) {
    if (!fd) return;
    if (!Array.isArray(fd.inputs)) fd.inputs = [];
    const newInp = { name: 'Input Field', description: 'Description', required: true, format: 'String' };
    fd.inputs.push(newInp);
    this.isEdited = true;
    this.editSection(newInp, 'name');
    this.cdr.markForCheck();
  }

  deleteInput(fd: any, index: number) {
    if (!fd || !Array.isArray(fd.inputs)) return;
    if (index >= 0 && index < fd.inputs.length) {
      if (this.editingSectionTarget === fd.inputs[index]) this.cancelSection();
      fd.inputs.splice(index, 1);
      this.isEdited = true;
      this.cdr.markForCheck();
    }
  }

  addNewOutput(fd: any) {
    if (!fd) return;
    if (!Array.isArray(fd.outputs)) fd.outputs = [];
    const newOut = { description: 'Output description', grounding: 'EXPLICIT' };
    fd.outputs.push(newOut);
    this.isEdited = true;
    this.editSection(newOut, 'description');
    this.cdr.markForCheck();
  }

  deleteOutput(fd: any, index: number) {
    if (!fd || !Array.isArray(fd.outputs)) return;
    if (index >= 0 && index < fd.outputs.length) {
      if (this.editingSectionTarget === fd.outputs[index]) this.cancelSection();
      fd.outputs.splice(index, 1);
      this.isEdited = true;
      this.cdr.markForCheck();
    }
  }

  addNewAlternateFlow(fd: any) {
    if (!fd) return;
    if (!Array.isArray(fd.alternateFlows)) fd.alternateFlows = [];
    const newAf = { name: 'Alternate Flow Name', steps: ['Step 1 description'] };
    fd.alternateFlows.push(newAf);
    this.isEdited = true;
    this.editSection(newAf, 'name');
    this.cdr.markForCheck();
  }

  deleteAlternateFlow(fd: any, index: number) {
    if (!fd || !Array.isArray(fd.alternateFlows)) return;
    if (index >= 0 && index < fd.alternateFlows.length) {
      if (this.editingSectionTarget === fd.alternateFlows[index]) this.cancelSection();
      fd.alternateFlows.splice(index, 1);
      this.isEdited = true;
      this.cdr.markForCheck();
    }
  }

  // ── Technical Design List & Table Helpers ────────────────────────────────
  addNewApi(td: any) {
    if (!td) return;
    if (!Array.isArray(td.apis)) td.apis = [];
    const newApi = {
      name: 'New API Endpoint',
      method: 'POST',
      endpoint: '/api/resource',
      purpose: 'API purpose description',
      statusCodes: ['200 OK', '400 Bad Request'],
      request: '{\n  "field": "string"\n}',
      response: '{\n  "success": true\n}',
      validationRules: ['Field must not be empty'],
      errorScenarios: ['Invalid input -> 400 Bad Request']
    };
    td.apis.push(newApi);
    this.isEdited = true;
    this.editSection(newApi, 'name');
    this.cdr.markForCheck();
  }

  deleteApi(td: any, index: number) {
    if (!td || !Array.isArray(td.apis)) return;
    if (index >= 0 && index < td.apis.length) {
      if (this.editingSectionTarget === td.apis[index]) this.cancelSection();
      td.apis.splice(index, 1);
      this.isEdited = true;
      this.cdr.markForCheck();
    }
  }

  addNewArchitectureStep(td: any) {
    if (!td) return;
    if (!Array.isArray(td.architectureFlow)) td.architectureFlow = [];
    const nextStep = td.architectureFlow.length + 1;
    const newStep = { step: nextStep, component: 'Component', action: 'Technical action description' };
    td.architectureFlow.push(newStep);
    this.isEdited = true;
    this.editSection(newStep, 'action');
    this.cdr.markForCheck();
  }

  deleteArchitectureStep(td: any, index: number) {
    if (!td || !Array.isArray(td.architectureFlow)) return;
    if (index >= 0 && index < td.architectureFlow.length) {
      if (this.editingSectionTarget === td.architectureFlow[index]) this.cancelSection();
      td.architectureFlow.splice(index, 1);
      td.architectureFlow.forEach((s: any, idx: number) => {
        if (s && typeof s === 'object') s.step = idx + 1;
      });
      this.isEdited = true;
      this.cdr.markForCheck();
    }
  }

  addNewDataModelEntity(td: any) {
    if (!td) return;
    if (!Array.isArray(td.dataModel)) td.dataModel = [];
    const newEntity = {
      entity: 'NewEntity',
      databaseChangesSummary: 'New table',
      fields: [
        { name: 'id', type: 'BIGINT', required: true, primaryKey: true, description: 'Primary key' },
        { name: 'name', type: 'VARCHAR(255)', required: true, description: 'Entity name' }
      ],
      relationships: ['None'],
      persistenceBehavior: 'JPA entity'
    };
    td.dataModel.push(newEntity);
    this.isEdited = true;
    this.editSection(newEntity, 'entity');
    this.cdr.markForCheck();
  }

  deleteDataModelEntity(td: any, index: number) {
    if (!td || !Array.isArray(td.dataModel)) return;
    if (index >= 0 && index < td.dataModel.length) {
      if (this.editingSectionTarget === td.dataModel[index]) this.cancelSection();
      td.dataModel.splice(index, 1);
      this.isEdited = true;
      this.cdr.markForCheck();
    }
  }

  addNewDataModelField(entity: any) {
    if (!entity) return;
    if (!Array.isArray(entity.fields)) entity.fields = [];
    const newF = { name: 'new_field', type: 'VARCHAR(255)', required: true, description: 'Field description' };
    entity.fields.push(newF);
    this.isEdited = true;
    this.editSection(newF, 'name');
    this.cdr.markForCheck();
  }

  deleteDataModelField(entity: any, index: number) {
    if (!entity || !Array.isArray(entity.fields)) return;
    if (index >= 0 && index < entity.fields.length) {
      if (this.editingSectionTarget === entity.fields[index]) this.cancelSection();
      entity.fields.splice(index, 1);
      this.isEdited = true;
      this.cdr.markForCheck();
    }
  }

  addNewComponent(td: any) {
    if (!td) return;
    if (!Array.isArray(td.components)) td.components = [];
    const newComp = {
      name: 'NewComponent',
      responsibility: 'Component responsibility',
      importantMethods: ['init() - initialization logic'],
      dependencies: ['DependencyService']
    };
    td.components.push(newComp);
    this.isEdited = true;
    this.editSection(newComp, 'name');
    this.cdr.markForCheck();
  }

  deleteComponent(td: any, index: number) {
    if (!td || !Array.isArray(td.components)) return;
    if (index >= 0 && index < td.components.length) {
      if (this.editingSectionTarget === td.components[index]) this.cancelSection();
      td.components.splice(index, 1);
      this.isEdited = true;
      this.cdr.markForCheck();
    }
  }

  addNewImplementationStep(td: any) {
    if (!td) return;
    if (!Array.isArray(td.implementationPlan)) td.implementationPlan = [];
    const nextStep = td.implementationPlan.length + 1;
    const newStep = {
      step: nextStep,
      phase: 'Backend / Frontend',
      action: 'Implementation action',
      deliverable: 'Source file',
      verification: 'Unit test'
    };
    td.implementationPlan.push(newStep);
    this.isEdited = true;
    this.editSection(newStep, 'action');
    this.cdr.markForCheck();
  }

  deleteImplementationStep(td: any, index: number) {
    if (!td || !Array.isArray(td.implementationPlan)) return;
    if (index >= 0 && index < td.implementationPlan.length) {
      if (this.editingSectionTarget === td.implementationPlan[index]) this.cancelSection();
      td.implementationPlan.splice(index, 1);
      td.implementationPlan.forEach((s: any, idx: number) => {
        if (s && typeof s === 'object') s.step = idx + 1;
      });
      this.isEdited = true;
      this.cdr.markForCheck();
    }
  }

  addNewTechRisk(td: any) {
    if (!td) return;
    if (!Array.isArray(td.technicalRisks)) td.technicalRisks = [];
    const newRisk = { risk: 'Technical risk description', impact: 'Medium', mitigation: 'Mitigation strategy' };
    td.technicalRisks.push(newRisk);
    this.isEdited = true;
    this.editSection(newRisk, 'risk');
    this.cdr.markForCheck();
  }

  deleteTechRisk(td: any, index: number) {
    if (!td || !Array.isArray(td.technicalRisks)) return;
    if (index >= 0 && index < td.technicalRisks.length) {
      if (this.editingSectionTarget === td.technicalRisks[index]) this.cancelSection();
      td.technicalRisks.splice(index, 1);
      this.isEdited = true;
      this.cdr.markForCheck();
    }
  }

  addNewTechDecision(td: any) {
    if (!td) return;
    if (!Array.isArray(td.technicalDecisions)) td.technicalDecisions = [];
    const newDec = { decision: 'Design decision', reason: 'Technical justification', alternativeConsidered: 'Alternative', whySelected: 'Evaluation reason' };
    td.technicalDecisions.push(newDec);
    this.isEdited = true;
    this.editSection(newDec, 'decision');
    this.cdr.markForCheck();
  }

  deleteTechDecision(td: any, index: number) {
    if (!td || !Array.isArray(td.technicalDecisions)) return;
    if (index >= 0 && index < td.technicalDecisions.length) {
      if (this.editingSectionTarget === td.technicalDecisions[index]) this.cancelSection();
      td.technicalDecisions.splice(index, 1);
      this.isEdited = true;
      this.cdr.markForCheck();
    }
  }

  addNewEdgeCase(td: any) {
    if (!td) return;
    if (!Array.isArray(td.edgeCases)) td.edgeCases = [];
    const newEc = { scenario: 'Edge case scenario', impact: 'Impact', handling: 'Technical mitigation' };
    td.edgeCases.push(newEc);
    this.isEdited = true;
    this.editSection(newEc, 'scenario');
    this.cdr.markForCheck();
  }

  deleteEdgeCase(td: any, index: number) {
    if (!td || !Array.isArray(td.edgeCases)) return;
    if (index >= 0 && index < td.edgeCases.length) {
      if (this.editingSectionTarget === td.edgeCases[index]) this.cancelSection();
      td.edgeCases.splice(index, 1);
      this.isEdited = true;
      this.cdr.markForCheck();
    }
  }

  addNewBusinessRuleMapping(td: any) {
    if (!td) return;
    if (!Array.isArray(td.businessRuleMappings)) td.businessRuleMappings = [];
    const newM = { businessRule: 'Business rule', technicalImplementation: 'Technical enforcement' };
    td.businessRuleMappings.push(newM);
    this.isEdited = true;
    this.editSection(newM, 'businessRule');
    this.cdr.markForCheck();
  }

  deleteBusinessRuleMapping(td: any, index: number) {
    if (!td || !Array.isArray(td.businessRuleMappings)) return;
    if (index >= 0 && index < td.businessRuleMappings.length) {
      if (this.editingSectionTarget === td.businessRuleMappings[index]) this.cancelSection();
      td.businessRuleMappings.splice(index, 1);
      this.isEdited = true;
      this.cdr.markForCheck();
    }
  }

  addNewAcceptanceCriteriaMapping(td: any) {
    if (!td) return;
    if (!Array.isArray(td.acceptanceCriteriaMappings)) td.acceptanceCriteriaMappings = [];
    const newM = { acceptanceCriterion: 'Acceptance criterion', technicalImplementation: 'Technical implementation details' };
    td.acceptanceCriteriaMappings.push(newM);
    this.isEdited = true;
    this.editSection(newM, 'acceptanceCriterion');
    this.cdr.markForCheck();
  }

  deleteAcceptanceCriteriaMapping(td: any, index: number) {
    if (!td || !Array.isArray(td.acceptanceCriteriaMappings)) return;
    if (index >= 0 && index < td.acceptanceCriteriaMappings.length) {
      if (this.editingSectionTarget === td.acceptanceCriteriaMappings[index]) this.cancelSection();
      td.acceptanceCriteriaMappings.splice(index, 1);
      this.isEdited = true;
      this.cdr.markForCheck();
    }
  }

  addNewDataFlowStep(td: any) {
    if (!td) return;
    if (!Array.isArray(td.dataFlow)) td.dataFlow = [];
    const nextStep = td.dataFlow.length + 1;
    const newDf = { step: nextStep, source: 'Component A', target: 'Component B', action: 'Data transmission', payload: 'Payload description' };
    td.dataFlow.push(newDf);
    this.isEdited = true;
    this.editSection(newDf, 'action');
    this.cdr.markForCheck();
  }

  deleteDataFlowStep(td: any, index: number) {
    if (!td || !Array.isArray(td.dataFlow)) return;
    if (index >= 0 && index < td.dataFlow.length) {
      if (this.editingSectionTarget === td.dataFlow[index]) this.cancelSection();
      td.dataFlow.splice(index, 1);
      td.dataFlow.forEach((s: any, idx: number) => {
        if (s && typeof s === 'object') s.step = idx + 1;
      });
      this.isEdited = true;
      this.cdr.markForCheck();
    }
  }

  isObject(val: any): boolean {
    return val !== null && typeof val === 'object' && !Array.isArray(val);
  }

  asArray(val: any): any[] {
    if (!val) return [];
    if (Array.isArray(val)) return val;
    return [val];
  }

  togglePanel(index: number) {
    this.collapsedPanels[index] = !this.collapsedPanels[index];
    this.cdr.markForCheck();
  }

  // ── Mode Toggle ────────────────────────────────────────────────────────────
  toggleEditMode() {
    if (this.mode === 'VIEW') {
      this.mode = 'EDIT_ALL';
      // Deep copy ALL requirements for editing
      this.editableRequirements = JSON.parse(JSON.stringify(this.requirementList));
      this.collapsedPanels = this.editableRequirements.map(() => false);
    } else {
      this.mode = 'VIEW';
    }
    this.cdr.markForCheck();
  }

  // ── Accept Flow ────────────────────────────────────────────────────────────
  onAcceptClick() {
    this.showConfirmPopup = true;
    this.cdr.markForCheck();
  }

  cancelConfirm() {
    this.showConfirmPopup = false;
    this.cdr.markForCheck();
  }

  get isRequirementLike(): boolean {
    return this.type === 'requirement' || this.type === 'userstory' || this.type === 'functionaldesign' || this.type === 'technicaldesign';
  }

  get functionalDesignData(): any {
    return this.data?.functionalDesign || null;
  }

  get technicalDesignData(): any {
    return this.data?.technicalDesign || null;
  }

  get userStoryList(): any[] {
    if (this.data && Array.isArray(this.data.userStories) && this.data.userStories.length > 0) {
      return this.data.userStories;
    }
    return this.requirementList;
  }

  confirmAccept() {
    this.showConfirmPopup = false;

    if (this.isRequirementLike) {
      // Emit ALL requirements (edited or original)
      const reqs = this.mode === 'EDIT_ALL' ? this.editableRequirements : this.requirementList;
      this.acceptAll.emit({
        requirements: reqs,
        isEdited: this.mode === 'EDIT_ALL' || this.isEdited
      });
    } else {
      // Non-requirement types — single object
      const finalData = this.mode === 'EDIT_ALL' ? this.editableData : this.data;
      this.accept.emit({
        editedData: finalData,
        isEdited: this.mode === 'EDIT_ALL' || this.isEdited
      });
    }
  }

  onRejectClick() {
    this.reject.emit();
    this.closeModal();
  }

  closeModal() {
    this.isOpen = false;
    this.showConfirmPopup = false;
    this.showSuccessPopup = false;
    this.mode = 'VIEW';
    this.close.emit();
  }

  notifySuccess(wasEdited = false) {
    this.successMessage = wasEdited
      ? 'Requirements updated and saved successfully. You can view them in Audit History.'
      : 'All requirements saved successfully. You can view them in Audit History.';
    this.showSuccessPopup = true;
    this.cdr.markForCheck();
  }

  saveAllEdits() {
    if (this.isRequirementLike && this.editableRequirements?.length) {
      if (this.data) {
        if (Array.isArray(this.data)) {
          this.data = JSON.parse(JSON.stringify(this.editableRequirements));
        } else if (this.data.userStories) {
          this.data.userStories = JSON.parse(JSON.stringify(this.editableRequirements));
        } else if (this.data.requirements) {
          this.data.requirements = JSON.parse(JSON.stringify(this.editableRequirements));
        } else if (this.data.items) {
          this.data.items = JSON.parse(JSON.stringify(this.editableRequirements));
        } else if (this.data.result) {
          this.data.result = JSON.parse(JSON.stringify(this.editableRequirements));
        }
      }
    } else if (this.editableData) {
      this.data = JSON.parse(JSON.stringify(this.editableData));
    }
    this.isEdited = true;
    this.mode = 'VIEW';
    this.cdr.markForCheck();
  }

  // ── Download ───────────────────────────────────────────────────────────────
  /** Collects live project/work/version metadata for PDF headers */
  private getPdfMeta(): any {
    return {
      documentName: this.meta?.documentName || '',
      project:      this.meta?.project   || '',
      work:         this.meta?.inputType || '',
      version:      this.meta?.version || ''
    };
  }

  downloadExcel() {
    const finalData = this.mode === 'EDIT_ALL' ? this.editableData : this.data;
    const items = Array.isArray(finalData) ? finalData : (finalData.items || []);
    this.exportService.downloadTestCaseExcel(items, 'test-cases');
  }

  downloadCsv() {
    const finalData = this.mode === 'EDIT_ALL' ? this.editableData : this.data;
    const items = Array.isArray(finalData) ? finalData : (finalData.items || []);
    this.exportService.downloadTestCaseCsv(items, 'test-cases');
  }

  downloadTestCasePdf() {
    const finalData = this.mode === 'EDIT_ALL' ? this.editableData : this.data;
    const items = Array.isArray(finalData) ? finalData : (finalData.items || []);
    this.exportService.downloadTestCasePdf(items, this.getPdfMeta());
  }

  download() {
    const finalData = this.mode === 'EDIT_ALL' ? this.editableData : this.data;
    const pdfMeta  = this.getPdfMeta();

    if (this.type === 'testcase') {
      this.downloadCsv();
    } else if (this.type === 'userstory') {
      const allReqs = this.mode === 'EDIT_ALL' ? this.editableRequirements : this.requirementList;
      this.exportService.downloadUserStoryPdf(allReqs, pdfMeta);
    } else if (this.type === 'functionaldesign') {
      const fd = this.functionalDesignData || finalData;
      this.exportService.downloadFunctionalDesignPdf(fd, pdfMeta);
    } else if (this.type === 'technicaldesign') {
      const td = this.technicalDesignData || finalData;
      this.exportService.downloadTechnicalDesignPdf(td, pdfMeta);
    } else if (this.type === 'requirement') {
      // Export ALL requirements into one PDF
      const allReqs = this.mode === 'EDIT_ALL' ? this.editableRequirements : this.requirementList;
      const cleanReqs = allReqs.map((req: any) => this.cleanRequirementForExport(req));
      this.exportService.downloadAllRequirementsPdf(cleanReqs, 'requirements', pdfMeta);
    } else if (this.type === 'defect') {
      this.exportService.downloadDefectPdf(finalData, 'defect-triage', pdfMeta);
    } else if (this.type === 'releasenote') {
      this.exportService.downloadReleaseNotePdf(finalData, 'release-notes', pdfMeta);
    }
  }

  downloadDefectExcel() {
    const finalData = this.mode === 'EDIT_ALL' ? this.editableData : this.data;
    this.exportService.downloadDefectExcel(finalData, 'defect-triage');
  }

  downloadDefectCsv() {
    const finalData = this.mode === 'EDIT_ALL' ? this.editableData : this.data;
    this.exportService.downloadDefectCsv(finalData, 'defect-triage');
  }

  downloadDefectPdf() {
    const finalData = this.mode === 'EDIT_ALL' ? this.editableData : this.data;
    this.exportService.downloadDefectPdf(finalData, 'defect-triage', this.getPdfMeta());
  }

  private cleanRequirementForExport(req: any): any {
    if (!req) return {};
    const toStrings = (items: any[]): string[] => {
      if (!Array.isArray(items)) return [];
      return items.map(item => this.getItemText(item));
    };

    return {
      title: req.requirementId ? `[${req.requirementId}] ${req.title || ''}` : (req.title || 'Requirement'),
      requirementId: req.requirementId,
      summary: req.summary,
      userStory: req.userStory,
      acceptanceCriteria: toStrings(req.acceptanceCriteria),
      assumptions: toStrings(req.assumptions),
      dependencies: toStrings(req.dependencies),
      edgeCases: toStrings(req.edgeCases)
    };
  }

  // ── Grounding Helpers ──────────────────────────────────────────────────────
  getItemText(item: any): string {
    if (!item) return '';
    if (typeof item === 'string') return item;
    if (typeof item.text === 'string') return item.text;
    return item.text != null ? String(item.text) : (typeof item === 'object' && Object.keys(item).length === 0 ? '' : JSON.stringify(item));
  }

  getItemGrounding(item: any): string {
    if (!item || typeof item === 'string') return 'EXPLICIT';
    return item.grounding || 'EXPLICIT';
  }

  getItemSource(item: any): string[] {
    if (!item || typeof item === 'string' || !item.source) return [];
    if (Array.isArray(item.source)) return item.source;
    return [item.source];
  }

  // ── Array Edit Helpers ─────────────────────────────────────────────────────
  addArrayItem(arrayRef: any[]) {
    if (arrayRef) {
      arrayRef.push({ text: '', grounding: 'DERIVED', source: [] });
      this.isEdited = true;
      this.cdr.markForCheck();
    }
  }

  /** Safe version: initializes the array on the parent object if it doesn't exist, then adds a new item */
  addArrayItemSafe(parent: any, key: string) {
    if (!parent) return;
    if (!Array.isArray(parent[key])) {
      parent[key] = [];
    }
    parent[key].push({ text: '', grounding: 'DERIVED', source: [] });
    this.isEdited = true;
    this.cdr.markForCheck();
  }

  /** Safe version for plain string arrays (e.g. bugFixes in Release Notes) */
  addStringItemSafe(parent: any, key: string) {
    if (!parent) return;
    if (!Array.isArray(parent[key])) {
      parent[key] = [];
    }
    parent[key].push('');
    this.isEdited = true;
    this.cdr.markForCheck();
  }

  onArrayItemChange(arrayRef: any[], index: number, newText: string) {
    if (!arrayRef || index < 0 || index >= arrayRef.length) return;
    const current = arrayRef[index];
    if (current && typeof current === 'object') {
      arrayRef[index] = { ...current, text: newText };
    } else {
      arrayRef[index] = { text: newText, grounding: 'DERIVED', source: [] };
    }
    this.isEdited = true;
    this.cdr.markForCheck();
  }

  removeArrayItem(arrayRef: any[], index: number) {
    if (arrayRef && index >= 0 && index < arrayRef.length) {
      arrayRef.splice(index, 1);
      this.isEdited = true;
      this.cdr.markForCheck();
    }
  }

  trackByIndex(index: number, obj: any): any {
    return index;
  }
}

