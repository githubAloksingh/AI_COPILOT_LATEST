import { Component, Input, OnChanges, SimpleChanges, ChangeDetectorRef, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import * as XLSX from 'xlsx-js-style';
import { ApiService } from '../../api';
import { ExportService } from '../../services/export.service';
import { PdfViewerComponent } from '../pdf-viewer/pdf-viewer';

@Component({
  selector: 'app-feature-history',
  standalone: true,
  imports: [CommonModule, PdfViewerComponent],
  templateUrl: './feature-history.html',
  styleUrls: ['./feature-history.scss']
})
export class FeatureHistoryComponent implements OnChanges {
  @ViewChild(PdfViewerComponent) pdfViewer?: PdfViewerComponent;

  @Input() projectId: number | null = null;
  @Input() documentId: number | null = null;
  @Input() documentName?: string = '';
  @Input() feature: string = '';
  @Input() projectName?: string = '';

  loading = false;
  historyItems: any[] = [];
  projectDocuments: any[] = [];
  errorMessage = '';

  constructor(
    private api: ApiService,
    private exportService: ExportService,
    private cdr: ChangeDetectorRef
  ) {}

  get isUserStory(): boolean {
    const f = (this.feature || '').toLowerCase().replace(/[-_\s]/g, '');
    return f === 'userstory';
  }

  get isTechnicalDesign(): boolean {
    const f = (this.feature || '').toLowerCase().replace(/[-_\s]/g, '');
    return f === 'technicaldesign';
  }

  get isFunctionalDesign(): boolean {
    const f = (this.feature || '').toLowerCase().replace(/[-_\s]/g, '');
    return f === 'functionaldesign';
  }

  get isRequirementAssistant(): boolean {
    const f = (this.feature || '').toLowerCase().replace(/[-_\s]/g, '');
    return f === 'requirementassistant' || f === 'requirement' || f === 'requirements';
  }

  get isTestGenerator(): boolean {
    const f = (this.feature || '').toLowerCase().replace(/[-_\s]/g, '');
    return f === 'testgenerator' || f === 'testcase' || f === 'testcases';
  }

  get isDefectTriage(): boolean {
    const f = (this.feature || '').toLowerCase().replace(/[-_\s]/g, '');
    return f === 'defecttriage' || f === 'defect';
  }

  get isReleaseNotes(): boolean {
    const f = (this.feature || '').toLowerCase().replace(/[-_\s]/g, '');
    return f === 'releasenotes' || f === 'releasenote';
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['projectId'] || changes['feature'] || changes['documentId']) {
      this.loadHistory();
    }
  }

  loadHistory(): void {
    if (this.isUserStory || this.isTechnicalDesign || this.isFunctionalDesign || this.isRequirementAssistant || this.isTestGenerator || this.isDefectTriage || this.isReleaseNotes) {
      if (!this.projectId || !this.documentId) {
        this.historyItems = [];
        this.loading = false;
        this.errorMessage = '';
        this.cdr.markForCheck();
        return;
      }
    } else if (!this.projectId || !this.feature) {
      this.historyItems = [];
      this.loading = false;
      this.errorMessage = '';
      this.cdr.markForCheck();
      return;
    }

    this.loading = true;
    this.errorMessage = '';
    this.cdr.markForCheck();

    if (this.isDefectTriage) {
      this.fetchHistoryRecords();
      return;
    }

    if (this.isReleaseNotes) {
      this.fetchHistoryRecords();
      return;
    }

    // Fetch project documents first to help resolve any unlinked history items
    this.api.getProjectDocuments(this.projectId!).subscribe({
      next: (docRes) => {
        this.projectDocuments = (docRes && docRes.success && docRes.data) ? docRes.data : [];
        this.fetchHistoryRecords();
      },
      error: () => {
        this.projectDocuments = [];
        this.fetchHistoryRecords();
      }
    });
  }

  private fetchHistoryRecords(): void {
    this.api.getHistory(this.projectId!, this.feature, this.documentId).subscribe({
      next: (res) => {
        this.loading = false;
        if (res.success) {
          const rawItems = res.data || [];
          this.historyItems = rawItems.map((item: any) => this.enrichHistoryItem(item));
        } else {
          this.historyItems = [];
          this.errorMessage = res.message || 'Failed to load history';
        }
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.loading = false;
        this.historyItems = [];
        this.errorMessage = err.error?.message || 'Error loading history records';
        this.cdr.markForCheck();
      }
    });
  }

  private enrichHistoryItem(item: any): any {
    const enriched = { ...item };
    const sourceDocumentName = enriched.documentName;

    // Ensure documentName exists
    if (!enriched.documentName) {
      enriched.documentName = this.documentName || enriched.fileName || `Document_${enriched.id || 'record'}`;
    }

    // Try resolving documentId if missing
    if (!enriched.documentId && this.projectDocuments.length > 0) {
      const match = this.findMatchingDocument(enriched);
      if (match) {
        enriched.documentId = match.id;
      } else {
        // Fallback to latest available document for the project if available
        const fallbackDoc = this.projectDocuments[0];
        if (fallbackDoc && fallbackDoc.id) {
          enriched.documentId = fallbackDoc.id;
        }
      }
    }

    enriched.sourceDocumentName = sourceDocumentName || enriched.documentName;
    enriched.documentName = this.getGeneratedArtifactName(enriched);
    return enriched;
  }

  private getGeneratedArtifactName(item: any): string {
    const sourceName = item.sourceDocumentName || item.documentName || this.documentName || 'GeneratedResponse';
    const baseName = this.sanitizeArtifactPart(sourceName.replace(/\.[^/.]+$/, ''));
    const featureNames: Record<string, string> = {
      user_story: 'USERSTORY',
      functional_design: 'FUNCTIONALDESIGN',
      technical_design: 'TECHNICALDESIGN',
      requirement_assistant: 'REQUIREMENTASSISTANT',
      test_generator: 'TESTGENERATOR',
      defect_triage: 'DEFECTTRIAGE',
      release_notes: 'RELEASENOTES'
    };
    const featureKey = (item.feature || this.feature || '').toLowerCase().replace(/[-\s]/g, '_');
    const featureName = featureNames[featureKey] || this.sanitizeArtifactPart(item.feature || this.feature || 'GeneratedResponse');
    const version = String(item.version || '1.0');
    const versionMatch = version.match(/^1\.(\d+)$/);
    const sequence = versionMatch ? Number(versionMatch[1]) + 1 : 1;
    return `${baseName}_${featureName}(${sequence})`;
  }

  private sanitizeArtifactPart(value: string): string {
    return String(value).replace(/[^a-zA-Z0-9_-]/g, '_');
  }

  private findMatchingDocument(item: any): any {
    if (!this.projectDocuments || this.projectDocuments.length === 0) return null;

    const itemName = (item.documentName || item.fileName || '').toLowerCase().trim();
    const itemCleanName = itemName.replace(/\.[^/.]+$/, '').replace(/[\s_()\-]/g, '');

    // 1. Exact match on fileName, originalFilename, or title
    for (const doc of this.projectDocuments) {
      const fn = (doc.fileName || '').toLowerCase().trim();
      const orig = (doc.originalFilename || '').toLowerCase().trim();
      const title = (doc.title || '').toLowerCase().trim();
      if (fn === itemName || orig === itemName || title === itemName) {
        return doc;
      }
    }

    // 2. Cleaned name match
    for (const doc of this.projectDocuments) {
      const fn = (doc.fileName || '').toLowerCase().trim();
      const cleanFn = fn.replace(/\.[^/.]+$/, '').replace(/[\s_()\-]/g, '');
      if (cleanFn && cleanFn === itemCleanName) {
        return doc;
      }
    }

    // 3. Substring match
    for (const doc of this.projectDocuments) {
      const fn = (doc.fileName || '').toLowerCase().trim();
      if (fn && (fn.includes(itemName) || itemName.includes(fn))) {
        return doc;
      }
    }

    // 4. File extension / type match
    const isPdf = itemName.endsWith('.pdf') || item.fileType === 'PDF';
    const isZip = itemName.endsWith('.zip') || item.fileType === 'ZIP';
    const isCsv = itemName.endsWith('.csv') || item.fileType === 'CSV';

    for (const doc of this.projectDocuments) {
      const fn = (doc.fileName || '').toLowerCase().trim();
      if (isPdf && fn.endsWith('.pdf')) return doc;
      if (isZip && fn.endsWith('.zip')) return doc;
      if (isCsv && fn.endsWith('.csv')) return doc;
    }

    return null;
  }

  viewDocument(item: any): void {
    if (this.isDefectTriage || item.feature === 'defect_triage') {
      this.viewDefectTriage(item);
      return;
    }

    if (this.isReleaseNotes || item.feature === 'release_notes') {
      this.viewReleaseNotes(item);
      return;
    }

    if (this.isUserStory || item.feature === 'user_story') {
      this.viewUserStory(item);
      return;
    }

    if (this.isTechnicalDesign || item.feature === 'technical_design') {
      this.viewTechnicalDesign(item);
      return;
    }

    if (this.isFunctionalDesign || item.feature === 'functional_design') {
      this.viewFunctionalDesign(item);
      return;
    }

    if (this.isRequirementAssistant || item.feature === 'requirement_assistant' || item.feature === 'requirement') {
      this.viewRequirementAssistant(item);
      return;
    }

    if (this.isTestGenerator || item.feature === 'test_generator' || item.feature === 'testcase') {
      this.viewTestGenerator(item);
      return;
    }

    const docId = item.documentId || item.fileId || item.id;
    if (!docId) {
      alert('Unable to view this document.');
      return;
    }

    const docName = (item.sourceDocumentName || item.documentName || item.fileName || 'document.pdf').toLowerCase();
    const isZip = docName.endsWith('.zip') || item.fileType === 'ZIP';
    const isCsv = docName.endsWith('.csv') || item.fileType === 'CSV';
    const isPdf = docName.endsWith('.pdf') || item.fileType === 'PDF';

    if (isPdf) {
      this.pdfViewer?.open(docId, item.documentName || item.fileName || 'document.pdf');
      return;
    }

    this.api.getDocumentFile(docId).subscribe({
      next: (blob: Blob) => {
        let mimeType = blob.type;
        if (!mimeType || mimeType === 'application/octet-stream') {
          if (isPdf) mimeType = 'application/pdf';
          else if (isCsv) mimeType = 'text/csv';
          else if (isZip) mimeType = 'application/zip';
          else mimeType = 'text/plain';
        }

        if (isZip) {
          const url = window.URL.createObjectURL(new Blob([blob], { type: mimeType }));
          const a = document.createElement('a');
          a.href = url;
          a.download = item.documentName || 'codebase.zip';
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          window.URL.revokeObjectURL(url);
          return;
        }

        const viewBlob = new Blob([blob], { type: mimeType });
        const url = window.URL.createObjectURL(viewBlob);
        window.location.href = url;
      },
      error: () => {
        alert('Unable to view this document.');
      }
    });
  }

  downloadDocument(item: any): void {
    if (this.isDefectTriage || item.feature === 'defect_triage') {
      this.downloadDefectTriage(item);
      return;
    }

    if (this.isReleaseNotes || item.feature === 'release_notes') {
      this.downloadReleaseNotes(item);
      return;
    }

    if (this.isUserStory || item.feature === 'user_story') {
      this.downloadUserStory(item);
      return;
    }

    if (this.isTechnicalDesign || item.feature === 'technical_design') {
      this.downloadTechnicalDesign(item);
      return;
    }

    if (this.isFunctionalDesign || item.feature === 'functional_design') {
      this.downloadFunctionalDesign(item);
      return;
    }

    if (this.isRequirementAssistant || item.feature === 'requirement_assistant' || item.feature === 'requirement') {
      this.downloadRequirementAssistant(item);
      return;
    }

    if (this.isTestGenerator || item.feature === 'test_generator' || item.feature === 'testcase') {
      this.downloadTestGenerator(item);
      return;
    }

    const docId = item.documentId || item.fileId || item.id;
    if (!docId) {
      alert('Unable to download this document.');
      return;
    }

    this.api.downloadDocument(docId).subscribe({
      next: (blob: Blob) => {
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = item.documentName || item.fileName || 'document.pdf';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
      },
      error: () => {
        alert('Unable to download this document.');
      }
    });
  }

  private viewDefectTriage(item: any): void {
    const renderPdf = (content: string) => {
      const defectData = this.parseDefectTriageContent(content);
      if (!defectData) {
        alert('No Defect Triage content available to view.');
        return;
      }
      const meta = {
        project: item.projectName || this.projectName,
        documentName: item.documentName || this.documentName || 'BRD',
        version: item.version || '1.0',
        work: 'Defect Triage'
      };
      const blob = this.exportService.generateDefectPdfBlob(defectData, `Defect_Triage_v${meta.version}`, meta);
      if (blob) {
        this.pdfViewer?.openBlob(blob, `${meta.project || 'Project'}_Defect_Triage_v${meta.version}.pdf`);
      } else {
        alert('Could not generate Defect Triage PDF for viewing.');
      }
    };

    if (item.content) {
      renderPdf(item.content);
    } else if (item.id) {
      this.api.getHistoryContent(item.id).subscribe({
        next: (res) => {
          if (res.success && res.data) {
            item.content = res.data;
            renderPdf(res.data);
          } else {
            alert('Unable to load Defect Triage content.');
          }
        },
        error: () => alert('Unable to load Defect Triage content.')
      });
    }
  }

  private downloadDefectTriage(item: any): void {
    const downloadPdf = (content: string) => {
      const defectData = this.parseDefectTriageContent(content);
      if (!defectData) {
        alert('No Defect Triage content available to download.');
        return;
      }
      const meta = {
        project: item.projectName || this.projectName,
        documentName: item.documentName || this.documentName || 'BRD',
        version: item.version || '1.0',
        work: 'Defect Triage'
      };
      this.exportService.downloadDefectPdf(defectData, `Defect_Triage_v${meta.version}`, meta);
    };

    if (item.content) {
      downloadPdf(item.content);
    } else if (item.id) {
      this.api.getHistoryContent(item.id).subscribe({
        next: (res) => res.success && res.data ? downloadPdf(res.data) : alert('Unable to load Defect Triage content for download.'),
        error: () => alert('Unable to load Defect Triage content for download.')
      });
    }
  }

  private parseDefectTriageContent(content: any): any | null {
    if (!content) return null;
    if (typeof content === 'object') return content;
    try {
      const parsed = JSON.parse(String(content));
      return parsed && typeof parsed === 'object' ? parsed : null;
    } catch {
      return null;
    }
  }

  private viewReleaseNotes(item: any): void {
    const renderPdf = (content: string) => {
      const releaseData = this.parseReleaseNotesContent(content);
      if (!releaseData) {
        alert('No Release Notes content available to view.');
        return;
      }
      const meta = {
        project: item.projectName || this.projectName,
        documentName: item.documentName || this.documentName || 'BRD',
        version: item.version || '1.0',
        work: 'Release Notes'
      };
      const blob = this.exportService.generateReleaseNotePdfBlob(releaseData, `Release_Notes_v${meta.version}`, meta);
      if (blob) {
        this.pdfViewer?.openBlob(blob, `${meta.project || 'Project'}_Release_Notes_v${meta.version}.pdf`);
      } else {
        alert('Could not generate Release Notes PDF for viewing.');
      }
    };

    if (item.content) {
      renderPdf(item.content);
    } else if (item.id) {
      this.api.getHistoryContent(item.id).subscribe({
        next: (res) => {
          if (res.success && res.data) {
            item.content = res.data;
            renderPdf(res.data);
          } else {
            alert('Unable to load Release Notes content.');
          }
        },
        error: () => alert('Unable to load Release Notes content.')
      });
    }
  }

  private downloadReleaseNotes(item: any): void {
    const downloadPdf = (content: string) => {
      const releaseData = this.parseReleaseNotesContent(content);
      if (!releaseData) {
        alert('No Release Notes content available to download.');
        return;
      }
      const meta = {
        project: item.projectName || this.projectName,
        documentName: item.documentName || this.documentName || 'BRD',
        version: item.version || '1.0',
        work: 'Release Notes'
      };
      this.exportService.downloadReleaseNotePdf(releaseData, `Release_Notes_v${meta.version}`, meta);
    };

    if (item.content) {
      downloadPdf(item.content);
    } else if (item.id) {
      this.api.getHistoryContent(item.id).subscribe({
        next: (res) => res.success && res.data ? downloadPdf(res.data) : alert('Unable to load Release Notes content for download.'),
        error: () => alert('Unable to load Release Notes content for download.')
      });
    }
  }

  private parseReleaseNotesContent(content: any): any | null {
    if (!content) return null;
    if (typeof content === 'object') return content;
    try {
      const parsed = JSON.parse(String(content));
      return parsed && typeof parsed === 'object' ? parsed : null;
    } catch {
      return null;
    }
  }

  private viewUserStory(item: any): void {
    const renderPdf = (contentStr: string) => {
      const stories = this.parseUserStoryContent(contentStr);
      if (!stories || stories.length === 0) {
        alert('No user story content available to view.');
        return;
      }
      const meta = {
        project: item.projectName || this.projectName,
        documentName: item.sourceDocumentName || this.documentName || 'BRD',
        version: item.version || '1.0',
        work: 'User Stories'
      };
      const blob = this.exportService.generateUserStoryPdfBlob(stories, meta);
      if (blob) {
        const title = `${meta.project || 'Project'}_User_Stories_v${meta.version}.pdf`;
        this.pdfViewer?.openBlob(blob, title);
      } else {
        alert('Could not generate PDF for viewing.');
      }
    };

    if (item.content) {
      renderPdf(item.content);
    } else if (item.id) {
      this.api.getHistoryContent(item.id).subscribe({
        next: (res) => {
          if (res.success && res.data) {
            item.content = res.data;
            renderPdf(res.data);
          } else {
            alert('Unable to load user story content.');
          }
        },
        error: () => alert('Unable to load user story content.')
      });
    }
  }

  private downloadUserStory(item: any): void {
    const triggerDownload = (contentStr: string) => {
      const stories = this.parseUserStoryContent(contentStr);
      if (!stories || stories.length === 0) {
        alert('No user story content available to download.');
        return;
      }
      const meta = {
        project: item.projectName || this.projectName,
        documentName: item.sourceDocumentName || this.documentName || 'BRD',
        version: item.version || '1.0',
        work: 'User Stories'
      };
      this.exportService.downloadUserStoryPdf(stories, meta);
    };

    if (item.content) {
      triggerDownload(item.content);
    } else if (item.id) {
      this.api.getHistoryContent(item.id).subscribe({
        next: (res) => {
          if (res.success && res.data) {
            item.content = res.data;
            triggerDownload(res.data);
          } else {
            alert('Unable to load user story content for download.');
          }
        },
        error: () => alert('Unable to load user story content for download.')
      });
    }
  }

  private parseUserStoryContent(contentStr: string): any[] {
    if (!contentStr) return [];
    try {
      if (typeof contentStr === 'object') {
        const obj = contentStr as any;
        if (Array.isArray(obj)) return obj;
        if (Array.isArray(obj.requirements)) return obj.requirements;
        if (Array.isArray(obj.userStories)) return obj.userStories;
        if (Array.isArray(obj.items)) return obj.items;
        return [obj];
      }
      const trimmed = contentStr.trim();
      if (trimmed.startsWith('{') || trimmed.startsWith('[')) {
        const parsed = JSON.parse(trimmed);
        if (Array.isArray(parsed)) return parsed;
        if (Array.isArray(parsed.requirements)) return parsed.requirements;
        if (Array.isArray(parsed.userStories)) return parsed.userStories;
        if (Array.isArray(parsed.items)) return parsed.items;
        return [parsed];
      }
    } catch (e) {
      console.error('Error parsing user story JSON:', e);
    }
    return [];
  }

  refresh(): void {
    this.loadHistory();
  }

  private viewTechnicalDesign(item: any): void {
    const renderPdf = (contentStr: string) => {
      const tdData = this.parseTechnicalDesignContent(contentStr);
      if (!tdData) {
        alert('No technical design content available to view.');
        return;
      }
      const meta = {
        project: item.projectName || this.projectName,
        documentName: item.documentName || this.documentName || 'BRD',
        version: item.version || '1.0',
        work: 'Technical Design'
      };
      const blob = this.exportService.generateTechnicalDesignPdfBlob(tdData, meta);
      if (blob) {
        const title = `${meta.project || 'Project'}_Technical_Design_v${meta.version}.pdf`;
        this.pdfViewer?.openBlob(blob, title);
      } else {
        alert('Could not generate PDF for viewing.');
      }
    };

    if (item.content) {
      renderPdf(item.content);
    } else if (item.id) {
      this.api.getHistoryContent(item.id).subscribe({
        next: (res) => {
          if (res.success && res.data) {
            item.content = res.data;
            renderPdf(res.data);
          } else {
            alert('Unable to load technical design content.');
          }
        },
        error: () => alert('Unable to load technical design content.')
      });
    }
  }

  private downloadTechnicalDesign(item: any): void {
    const triggerDownload = (contentStr: string) => {
      const tdData = this.parseTechnicalDesignContent(contentStr);
      if (!tdData) {
        alert('No technical design content available to download.');
        return;
      }
      const meta = {
        project: item.projectName || this.projectName,
        documentName: item.documentName || this.documentName || 'BRD',
        version: item.version || '1.0',
        work: 'Technical Design'
      };
      this.exportService.downloadTechnicalDesignPdf(tdData, meta);
    };

    if (item.content) {
      triggerDownload(item.content);
    } else if (item.id) {
      this.api.getHistoryContent(item.id).subscribe({
        next: (res) => {
          if (res.success && res.data) {
            item.content = res.data;
            triggerDownload(res.data);
          } else {
            alert('Unable to load technical design content for download.');
          }
        },
        error: () => alert('Unable to load technical design content for download.')
      });
    }
  }

  private parseTechnicalDesignContent(contentStr: any): any {
    if (!contentStr) return null;
    try {
      let parsed = contentStr;
      if (typeof contentStr === 'string') {
        const trimmed = contentStr.trim();
        if (trimmed.startsWith('{') || trimmed.startsWith('[')) {
          try {
            parsed = JSON.parse(trimmed);
          } catch (jsonErr) {
            console.warn('JSON parse failed for technical design content');
          }
        }
      }
      if (parsed && typeof parsed === 'object') {
        return parsed.technicalDesign || parsed;
      }
      if (typeof contentStr === 'string' && contentStr.trim()) {
        return {
          title: this.documentName || 'Technical Design',
          technicalOverview: {
            whatIsBeingImplemented: contentStr
          }
        };
      }
    } catch (e) {
      console.error('Error parsing technical design content:', e);
    }
    return null;
  }

  private viewFunctionalDesign(item: any): void {
    const renderPdf = (contentStr: string) => {
      const fdData = this.parseFunctionalDesignContent(contentStr);
      if (!fdData) {
        alert('No functional design content available to view.');
        return;
      }
      const meta = {
        project: item.projectName || this.projectName,
        documentName: item.documentName || this.documentName || 'BRD',
        version: item.version || '1.0',
        work: 'Functional Design'
      };
      const blob = this.exportService.generateFunctionalDesignPdfBlob(fdData, meta);
      if (blob) {
        const title = `${meta.project || 'Project'}_Functional_Design_v${meta.version}.pdf`;
        this.pdfViewer?.openBlob(blob, title);
      } else {
        alert('Could not generate PDF for viewing.');
      }
    };

    if (item.content) {
      renderPdf(item.content);
    } else if (item.id) {
      this.api.getHistoryContent(item.id).subscribe({
        next: (res) => {
          if (res.success && res.data) {
            item.content = res.data;
            renderPdf(res.data);
          } else {
            alert('Unable to load functional design content.');
          }
        },
        error: () => alert('Unable to load functional design content.')
      });
    }
  }

  private downloadFunctionalDesign(item: any): void {
    const triggerDownload = (contentStr: string) => {
      const fdData = this.parseFunctionalDesignContent(contentStr);
      if (!fdData) {
        alert('No functional design content available to download.');
        return;
      }
      const meta = {
        project: item.projectName || this.projectName,
        documentName: item.documentName || this.documentName || 'BRD',
        version: item.version || '1.0',
        work: 'Functional Design'
      };
      this.exportService.downloadFunctionalDesignPdf(fdData, meta);
    };

    if (item.content) {
      triggerDownload(item.content);
    } else if (item.id) {
      this.api.getHistoryContent(item.id).subscribe({
        next: (res) => {
          if (res.success && res.data) {
            item.content = res.data;
            triggerDownload(res.data);
          } else {
            alert('Unable to load functional design content for download.');
          }
        },
        error: () => alert('Unable to load functional design content for download.')
      });
    }
  }

  private parseFunctionalDesignContent(contentStr: any): any {
    if (!contentStr) return null;
    try {
      let parsed = contentStr;
      if (typeof contentStr === 'string') {
        const trimmed = contentStr.trim();
        if (trimmed.startsWith('{') || trimmed.startsWith('[')) {
          try {
            parsed = JSON.parse(trimmed);
          } catch (jsonErr) {
            console.warn('JSON parse failed for functional design content');
          }
        } else if (trimmed.includes('RequirementResponseDto') || trimmed.includes('RequirementItemDto')) {
          return this.parseLombokRequirementDto(trimmed);
        }
      }
      if (parsed && typeof parsed === 'object') {
        if (parsed.functionalDesign && typeof parsed.functionalDesign === 'object') {
          return parsed.functionalDesign;
        }
        if (Array.isArray(parsed.requirements) && parsed.requirements.length > 0) {
          const req = parsed.requirements[0];
          return {
            title: req.title || this.documentName || 'Functional Design',
            objective: req.summary || req.description || (req.userStory ? String(req.userStory).replace(/^Objective:\s*/i, '') : ''),
            scope: req.summary ? [req.summary] : [],
            validations: req.acceptanceCriteria || [],
            businessRules: req.businessRules || [],
            assumptions: req.assumptions || [],
            dependencies: req.dependencies || [],
            edgeCases: req.edgeCases || []
          };
        }
        return parsed;
      }
      if (typeof contentStr === 'string' && contentStr.trim()) {
        const cleaned = contentStr.replace(/^Objective:\s*/i, '').trim();
        if (!cleaned.includes('RequirementResponseDto') && !cleaned.includes('RequirementItemDto')) {
          return {
            title: this.documentName || 'Functional Design',
            objective: cleaned,
            scope: [cleaned]
          };
        }
      }
    } catch (e) {
      console.error('Error parsing functional design content:', e);
    }
    return null;
  }

  private parseLombokRequirementDto(str: string): any {
    const extractField = (key: string, nextKeys: string[]): string => {
      const pattern = new RegExp(key + '=(.*?)(?:,\\s*(?:' + nextKeys.join('|') + ')=|$)', 's');
      const match = str.match(pattern);
      return match ? match[1].trim() : '';
    };

    const extractListTexts = (key: string): string[] => {
      const idx = str.indexOf(key + '=[');
      if (idx === -1) return [];
      const start = idx + key.length + 2;
      let depth = 1;
      let end = start;
      while (end < str.length && depth > 0) {
        if (str[end] === '[') depth++;
        else if (str[end] === ']') depth--;
        end++;
      }
      const sub = str.substring(start, end - 1);
      const texts: string[] = [];
      const textMatches = Array.from(sub.matchAll(/text=(.*?)(?:,\s*grounding=|\})/g));
      for (const m of textMatches) {
        const t = (m[1] || '').trim();
        if (t) texts.push(t);
      }
      return texts;
    };

    const title = extractField('title', ['summary', 'userStory', 'description']);
    const summary = extractField('summary', ['userStory', 'description', 'acceptanceCriteria']);
    const userStory = extractField('userStory', ['description', 'acceptanceCriteria']);
    const description = extractField('description', ['acceptanceCriteria', 'businessRules']);

    const cleanObjective = (summary || description || userStory.replace(/^Objective:\s*/i, '') || title).trim();

    const businessRules = extractListTexts('businessRules');
    const acceptanceCriteria = extractListTexts('acceptanceCriteria');
    const assumptions = extractListTexts('assumptions');
    const dependencies = extractListTexts('dependencies');
    const edgeCases = extractListTexts('edgeCases');

    return {
      title: title || this.documentName || 'Functional Design',
      objective: cleanObjective,
      scope: cleanObjective ? [cleanObjective] : [],
      validations: acceptanceCriteria.map(ac => ({ field: 'General', rule: ac, grounding: 'EXPLICIT' })),
      businessRules: businessRules,
      assumptions: assumptions,
      dependencies: dependencies,
      edgeCases: edgeCases
    };
  }

  private viewRequirementAssistant(item: any): void {
    const renderPdf = (contentStr: string) => {
      const reqs = this.parseRequirementAssistantContent(contentStr);
      if (!reqs || reqs.length === 0) {
        alert('No requirement assistant content available to view.');
        return;
      }
      const meta = {
        project: item.projectName || this.projectName,
        documentName: item.documentName || this.documentName || 'BRD',
        version: item.version || '1.0',
        work: 'Requirement Assistant'
      };
      const blob = this.exportService.generateAllRequirementsPdfBlob(reqs, 'requirements', meta);
      if (blob) {
        const title = `${meta.project || 'Project'}_Requirement_Assistant_v${meta.version}.pdf`;
        this.pdfViewer?.openBlob(blob, title);
      } else {
        alert('Could not generate PDF for viewing.');
      }
    };

    if (item.content) {
      renderPdf(item.content);
    } else if (item.id) {
      this.api.getHistoryContent(item.id).subscribe({
        next: (res) => {
          if (res.success && res.data) {
            item.content = res.data;
            renderPdf(res.data);
          } else {
            alert('Unable to load requirement assistant content.');
          }
        },
        error: () => alert('Unable to load requirement assistant content.')
      });
    }
  }

  private downloadRequirementAssistant(item: any): void {
    const triggerDownload = (contentStr: string) => {
      const reqs = this.parseRequirementAssistantContent(contentStr);
      if (!reqs || reqs.length === 0) {
        alert('No requirement assistant content available to download.');
        return;
      }
      const meta = {
        project: item.projectName || this.projectName,
        documentName: item.documentName || this.documentName || 'BRD',
        version: item.version || '1.0',
        work: 'Requirement Assistant'
      };
      this.exportService.downloadAllRequirementsPdf(reqs, 'requirements', meta);
    };

    if (item.content) {
      triggerDownload(item.content);
    } else if (item.id) {
      this.api.getHistoryContent(item.id).subscribe({
        next: (res) => {
          if (res.success && res.data) {
            item.content = res.data;
            triggerDownload(res.data);
          } else {
            alert('Unable to load requirement assistant content for download.');
          }
        },
        error: () => alert('Unable to load requirement assistant content for download.')
      });
    }
  }

  private parseRequirementAssistantContent(contentStr: any): any[] {
    if (!contentStr) return [];
    try {
      let parsed = contentStr;
      if (typeof contentStr === 'string') {
        const trimmed = contentStr.trim();
        if (trimmed.startsWith('{') || trimmed.startsWith('[')) {
          try {
            parsed = JSON.parse(trimmed);
          } catch (jsonErr) {
            console.warn('JSON parse failed for requirement assistant content');
          }
        } else if (trimmed.includes('RequirementResponseDto') || trimmed.includes('RequirementItemDto')) {
          const single = this.parseLombokRequirementDto(trimmed);
          return single ? [single] : [];
        }
      }
      if (parsed && typeof parsed === 'object') {
        if (Array.isArray(parsed)) return parsed;
        if (Array.isArray(parsed.requirements)) return parsed.requirements;
        if (Array.isArray(parsed.items)) return parsed.items;
        return [parsed];
      }
      if (typeof contentStr === 'string' && contentStr.trim()) {
        return [{
          requirementId: 'REQ-001',
          title: this.documentName || 'Requirement Specification',
          summary: contentStr
        }];
      }
    } catch (e) {
      console.error('Error parsing requirement assistant content:', e);
    }
    return [];
  }

  private viewTestGenerator(item: any): void {
    const renderPdf = (contentStr: string) => {
      const testCases = this.parseTestCaseContent(contentStr);
      if (!testCases || testCases.length === 0) {
        alert('No test generator content available to view.');
        return;
      }
      const meta = {
        project: item.projectName || this.projectName,
        documentName: item.documentName || this.documentName || 'BRD',
        version: item.version || '1.0',
        work: 'Test Generator'
      };
      const blob = this.exportService.generateTestCasePdfBlob(testCases, meta);
      if (blob) {
        const title = `${meta.project || 'Project'}_Test_Cases_v${meta.version}.pdf`;
        this.pdfViewer?.openBlob(blob, title);
      } else {
        alert('Could not generate PDF for viewing.');
      }
    };

    if (item.content) {
      renderPdf(item.content);
    } else if (item.id) {
      this.api.getHistoryContent(item.id).subscribe({
        next: (res) => {
          if (res.success && res.data) {
            item.content = res.data;
            renderPdf(res.data);
          } else {
            alert('Unable to load test generator content.');
          }
        },
        error: () => alert('Unable to load test generator content.')
      });
    }
  }

  private downloadTestGenerator(item: any): void {
    this.loadTestGeneratorContent(item, (testCases) => {
      const meta = {
        project: item.projectName || this.projectName,
        documentName: item.documentName || this.documentName || 'BRD',
        version: item.version || '1.0',
        work: 'Test Generator'
      };
      this.exportService.downloadTestCasePdf(testCases, meta);
    });
  }

  viewTestGeneratorExcel(item: any): void {
    this.loadTestGeneratorContent(item, (testCases) => {
      const workbook = this.exportService.buildTestCaseWorkbook(testCases);
      const blob = XLSX.write(workbook, { bookType: 'xlsx', type: 'array' });
      const file = new Blob([blob], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
      this.pdfViewer?.openSpreadsheetBlob(file, this.getTestCaseFilename(item));
    });
  }

  downloadTestGeneratorExcel(item: any): void {
    this.loadTestGeneratorContent(item, (testCases) => {
      this.exportService.downloadTestCaseExcel(testCases, this.getTestCaseFilename(item));
    });
  }

  viewTestGeneratorCsv(item: any): void {
    this.loadTestGeneratorContent(item, (testCases) => {
      const csv = this.exportService.generateTestCaseCsvString(testCases);
      const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
      this.pdfViewer?.openCsvBlob(blob, this.getTestCaseFilename(item) + '.csv');
    });
  }

  downloadTestGeneratorCsv(item: any): void {
    this.loadTestGeneratorContent(item, (testCases) => {
      this.exportService.downloadTestCaseCsv(testCases, this.getTestCaseFilename(item));
    });
  }

  viewDefectTriageExcel(item: any): void {
    this.loadDefectTriageContent(item, (defectData) => {
      const workbook = this.exportService.buildDefectWorkbook(defectData);
      const blob = XLSX.write(workbook, { bookType: 'xlsx', type: 'array' });
      const file = new Blob([blob], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
      this.pdfViewer?.openSpreadsheetBlob(file, this.getDefectFilename(item));
    });
  }

  downloadDefectTriageExcel(item: any): void {
    this.loadDefectTriageContent(item, (defectData) => {
      this.exportService.downloadDefectExcel(defectData, this.getDefectFilename(item));
    });
  }

  viewDefectTriageCsv(item: any): void {
    this.loadDefectTriageContent(item, (defectData) => {
      const csv = this.exportService.generateDefectCsvString(defectData);
      const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
      this.pdfViewer?.openCsvBlob(blob, this.getDefectFilename(item) + '.csv');
    });
  }

  downloadDefectTriageCsv(item: any): void {
    this.loadDefectTriageContent(item, (defectData) => {
      this.exportService.downloadDefectCsv(defectData, this.getDefectFilename(item));
    });
  }

  private loadDefectTriageContent(item: any, onContent: (defectData: any) => void): void {
    const triggerDownload = (content: any) => {
      const defectData = this.parseDefectTriageContent(content);
      if (!defectData) {
        alert('No Defect Triage content available to download.');
        return;
      }
      onContent(defectData);
    };

    if (item.content) {
      triggerDownload(item.content);
    } else if (item.id) {
      this.api.getHistoryContent(item.id).subscribe({
        next: (res) => res.success && res.data
          ? (item.content = res.data, triggerDownload(res.data))
          : alert('Unable to load Defect Triage content for download.'),
        error: () => alert('Unable to load Defect Triage content for download.')
      });
    }
  }

  private getDefectFilename(item: any): string {
    const sourceName = item.sourceDocumentName || item.documentName || 'defect-triage';
    return sourceName.replace(/\.[^/.]+$/, '').replace(/[^a-zA-Z0-9_-]/g, '_')
      + `_defect-triage_v${item.version || '1.0'}`;
  }

  private loadTestGeneratorContent(item: any, onContent: (testCases: any[]) => void): void {
    const triggerDownload = (contentStr: string) => {
      const testCases = this.parseTestCaseContent(contentStr);
      if (!testCases || testCases.length === 0) {
        alert('No test generator content available to download.');
        return;
      }
      onContent(testCases);
    };

    if (item.content) {
      triggerDownload(item.content);
    } else if (item.id) {
      this.api.getHistoryContent(item.id).subscribe({
        next: (res) => {
          if (res.success && res.data) {
            item.content = res.data;
            triggerDownload(res.data);
          } else {
            alert('Unable to load test generator content for download.');
          }
        },
        error: () => alert('Unable to load test generator content for download.')
      });
    }
  }

  private parseTestCaseContent(contentStr: any): any[] {
    if (!contentStr) return [];
    try {
      let parsed = contentStr;
      if (typeof contentStr === 'string') {
        const trimmed = contentStr.trim();
        if (trimmed.startsWith('{') || trimmed.startsWith('[')) {
          try {
            parsed = JSON.parse(trimmed);
          } catch (jsonErr) {
            console.warn('JSON parse failed for test generator content');
          }
        }
      }

      if (parsed && typeof parsed === 'object') {
        if (Array.isArray(parsed)) return parsed;
        if (Array.isArray(parsed.result)) return parsed.result;
        if (Array.isArray(parsed.testCases)) return parsed.testCases;
        if (Array.isArray(parsed.items)) return parsed.items;
        return [parsed];
      }
      if (typeof contentStr === 'string' && contentStr.trim()) {
        return [{
          tcId: 'TC-001',
          scenario: this.documentName || 'Test Case',
          preconditions: [],
          steps: [contentStr],
          expectedResult: ''
        }];
      }
    } catch (e) {
      console.error('Error parsing test generator content:', e);
    }
    return [];
  }

  private getTestCaseFilename(item: any): string {
    const sourceName = item.sourceDocumentName || item.documentName || 'test-cases';
    return sourceName.replace(/\.[^/.]+$/, '').replace(/[^a-zA-Z0-9_-]/g, '_')
      + `_test-cases_v${item.version || '1.0'}`;
  }
}

