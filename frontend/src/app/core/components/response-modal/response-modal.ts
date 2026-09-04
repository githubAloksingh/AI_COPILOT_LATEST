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
  @Input() sources: string[] = [];
  @Input() model = 'gemini-3.7-flash';
  @Input() promptVersion = '';
  @Input() executionTimeMs = 0;
  @Input() saving = false;
  @Input() meta?: { project?: string; inputType?: string; brd?: string; codebase?: string };

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
      // Pre-populate editable requirements list
      const list = this.requirementList;
      this.editableRequirements = JSON.parse(JSON.stringify(list));
      this.collapsedPanels = list.map(() => false); // all expanded by default
    }
  }

  // ── Requirement Helpers ────────────────────────────────────────────────────
  get requirementList(): any[] {
    if (!this.data) return [];
    if (Array.isArray(this.data.requirements) && this.data.requirements.length > 0) {
      return this.data.requirements;
    }
    if (Array.isArray(this.data)) {
      return this.data;
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
    this.selectedReqIndex = index;
    this.cdr.markForCheck();
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
        isEdited: this.mode === 'EDIT_ALL'
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

  // ── Download ───────────────────────────────────────────────────────────────
  download() {
    const finalData = this.mode === 'EDIT_ALL' ? this.editableData : this.data;

    if (this.type === 'testcase') {
      const items = Array.isArray(finalData) ? finalData : (finalData.items || []);
      this.exportService.downloadTestCaseCsv(items, 'test-cases');
    } else if (this.type === 'userstory') {
      const allReqs = this.mode === 'EDIT_ALL' ? this.editableRequirements : this.requirementList;
      this.exportService.downloadUserStoryPdf(allReqs);
    } else if (this.type === 'functionaldesign') {
      const fd = this.functionalDesignData || finalData;
      this.exportService.downloadFunctionalDesignPdf(fd);
    } else if (this.type === 'technicaldesign') {
      const td = this.technicalDesignData || finalData;
      this.exportService.downloadTechnicalDesignPdf(td);
    } else if (this.type === 'requirement') {
      // Export ALL requirements into one PDF
      const allReqs = this.mode === 'EDIT_ALL' ? this.editableRequirements : this.requirementList;
      const cleanReqs = allReqs.map(req => this.cleanRequirementForExport(req));
      this.exportService.downloadAllRequirementsPdf(cleanReqs, 'requirements');
    } else if (this.type === 'defect') {
      this.exportService.downloadDefectPdf(finalData, 'defect-triage');
    } else if (this.type === 'releasenote') {
      this.exportService.downloadReleaseNotePdf(finalData, 'release-notes');
    }
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
      edgeCases: toStrings(req.edgeCases),
      priority: req.priority || 'Medium'
    };
  }

  // ── Grounding Helpers ──────────────────────────────────────────────────────
  getItemText(item: any): string {
    if (!item) return '';
    if (typeof item === 'string') return item;
    return item.text || JSON.stringify(item);
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
    }
  }

  removeArrayItem(arrayRef: any[], index: number) {
    if (arrayRef && index >= 0 && index < arrayRef.length) {
      arrayRef.splice(index, 1);
    }
  }

  trackByIndex(index: number, obj: any): any {
    return index;
  }
}

