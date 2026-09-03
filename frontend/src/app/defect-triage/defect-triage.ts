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

  // Knowledge Base ZIP documents only
  zipDocuments: any[] = [];
  loadingDocs = false;
  selectedZipId: number | null = null;
  selectedZipDoc: any = null;

  // Optional contextual inputs
  defectTitle = '';
  logsOrSymptoms = '';

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
  promptVersion = 'defect-v1';
  executionTimeMs = 0;

  constructor(private api: ApiService, private cdr: ChangeDetectorRef) {}

  ngOnInit() {
    this.loadZipDocuments();
  }

  loadZipDocuments() {
    this.loadingDocs = true;
    this.api.getDocuments().subscribe({
      next: (res) => {
        if (res.success) {
          // Strictly filter ONLY ZIP files uploaded to Knowledge Base
          this.zipDocuments = (res.data || []).filter((d: any) => 
            d.status === 'COMPLETED' && (
              d.fileName.toLowerCase().endsWith('.zip') || 
              (d.fileType && d.fileType.toLowerCase().includes('zip'))
            )
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

  onZipSelect(docId: any) {
    this.selectedZipId = docId ? Number(docId) : null;
    this.selectedZipDoc = this.zipDocuments.find(d => d.id === this.selectedZipId) || null;
    if (this.selectedZipDoc && !this.defectTitle) {
      this.defectTitle = 'Defect Triage: ' + this.selectedZipDoc.fileName;
    }
    this.error = '';
    this.cdr.markForCheck();
  }

  removeSelectedZip() {
    this.selectedZipId = null;
    this.selectedZipDoc = null;
    this.cdr.markForCheck();
  }

  analyze() {
    if (!this.selectedZipId) {
      this.error = 'Please select a ZIP file from Knowledge Base to triage.';
      return;
    }

    this.loading = true;
    this.error = '';
    this.cdr.markForCheck();

    const title = this.defectTitle.trim() || ('Defect Triage: ' + (this.selectedZipDoc?.fileName || 'Project ZIP'));
    const description = `Automated defect triage for Knowledge Base ZIP archive: ${this.selectedZipDoc?.fileName || ''}`;

    const payload = {
      title: title,
      description: description,
      logs: this.logsOrSymptoms || '',
      environment: 'Knowledge Base ZIP Archive',
      document_id: String(this.selectedZipId)
    };

    this.api.analyzeDefect(payload).subscribe({
      next: (res) => {
        if (res.success && res.data) {
          const aiResponse = res.data;
          this.generatedResult = aiResponse.result || aiResponse;
          this.sources = aiResponse.sources || [];
          this.model = aiResponse.model || 'gemini-3.7-flash';
          this.promptVersion = aiResponse.prompt_version || 'defect-v1';
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
        this.error = err.error?.message || 'Failed to analyze defect file from Knowledge Base. Please try again.';
        this.cdr.markForCheck();
      }
    });
  }

  onAccept(event: { editedData: any; isEdited: boolean }) {
    this.saving = true;
    this.cdr.markForCheck();

    const acceptPayload = {
      title: this.defectTitle.trim() || ('Defect: ' + (this.selectedZipDoc?.fileName || 'Knowledge Base ZIP')),
      description: 'Defect triage from Knowledge Base ZIP archive: ' + (this.selectedZipDoc?.fileName || ''),
      logs: event.editedData.evidence || this.logsOrSymptoms || '',
      environment: 'Knowledge Base ZIP',
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
      executionTimeMs: this.executionTimeMs
    };

    this.api.acceptDefect(acceptPayload).subscribe({
      next: (res) => {
        this.saving = false;
        if (res.success) {
          if (this.responseModal) {
            this.responseModal.notifySuccess(event.isEdited);
          }
          this.showToast('Defect triage accepted successfully. Saved to SQL & Audit History.', 'success');
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
    this.showToast('Data rejected successfully.', 'info');
    this.cdr.markForCheck();
  }

  formatBytes(bytes: number): string {
    if (!bytes) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
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
