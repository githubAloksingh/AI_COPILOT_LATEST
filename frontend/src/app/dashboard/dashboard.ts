import { Component, OnInit, ChangeDetectorRef, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../core/api';
import { FeatureHistoryComponent } from '../core/components/feature-history/feature-history';
import { catchError, forkJoin, map, of, switchMap } from 'rxjs';

export interface ActivityRow {
  sNo: number;
  projectId: number | null;
  documentId: number | null;
  projectName: string;
  knowledgeBase: string;
  version: string;
  artifacts: {
    user_story?: any;
    functional_design?: any;
    technical_design?: any;
    requirement_assistant?: any;
    test_generator?: any;
    defect_triage?: any;
    release_notes?: any;
  };
  feature?: string;
  artifact?: any;
  artifactId?: number;
  category: string;
  userStory: string | null;
  functionalDesign: string | null;
  technicalDesign: string | null;
  requirementAnalysis: string | null;
  testGenerator: string | null;
  defectTriage: string | null;
  releaseNotes: string | null;
  lastUpdated: number;
}

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule, FeatureHistoryComponent],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.scss'
})
export class Dashboard implements OnInit {
  @ViewChild('artifactViewer') artifactViewer?: FeatureHistoryComponent;

  private readonly artifactFeatures = [
    'user_story',
    'functional_design',
    'technical_design',
    'requirement_assistant',
    'test_generator',
    'defect_triage',
    'release_notes'
  ];

  stats: any = null;
  recentActivity: any[] = [];
  activityRows: ActivityRow[] = [];
  allDocuments: any[] = [];
  allProjects: any[] = [];
  rawLogs: any[] = [];
  downloadingSNo: number | null = null;
  selectedVersion = 'ALL';
  loading = true;

  constructor(private api: ApiService, private cdr: ChangeDetectorRef) {}

  get availableVersions(): string[] {
    return Array.from(new Set(this.activityRows.map((row) => row.version)))
      .filter(Boolean)
      .sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));
  }

  get filteredActivityRows(): ActivityRow[] {
    const rows = this.selectedVersion === 'ALL'
      ? this.activityRows
      : this.activityRows.filter((row) => row.version === this.selectedVersion);
    return rows.map((row, index) => ({ ...row, sNo: index + 1 }));
  }

  ngOnInit() {
    this.loadArtifactRows();

    this.api.getStats().subscribe({
      next: (res) => {
        if (res.success) {
          this.stats = res.data;
        }
        this.loading = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.loading = false;
        this.cdr.markForCheck();
      }
    });

  }

  private loadArtifactRows(): void {
    this.api.getProjects().pipe(
      switchMap((projectResponse) => {
        const projects = projectResponse.success ? (projectResponse.data || []) : [];
        this.allProjects = projects;

        if (projects.length === 0) {
          return of([] as ActivityRow[]);
        }

        const projectRequests = projects.map((project: any) =>
          this.api.getProjectDocuments(Number(project.id)).pipe(
            switchMap((documentResponse) => {
              const documents = (documentResponse.success ? (documentResponse.data || []) : [])
                .filter((document: any) => this.isSupportedSourceDocument(document));
              const historyRequests = documents.flatMap((document: any) =>
                this.artifactFeatures.map((feature) =>
                  this.api.getHistory(Number(project.id), feature, Number(document.id)).pipe(
                    map((historyResponse) => historyResponse.success ? (historyResponse.data || []) : []),
                    catchError(() => of([] as any[]))
                  )
                )
              );

              return historyRequests.length > 0
                ? forkJoin(historyRequests).pipe(
                    map((histories) => histories.flatMap((items) => items).map((item) =>
                      this.toActivityRow(item, project, documents)
                    )))
                : of([] as ActivityRow[]);
            }),
            catchError(() => of([] as ActivityRow[]))
          )
        );

        return forkJoin(projectRequests).pipe(
          map((rows) => rows.flatMap((projectRows) => projectRows))
        );
      })
    ).subscribe({
      next: (rows) => {
        this.activityRows = this.groupArtifactRows(rows)
          .sort((a, b) => b.lastUpdated - a.lastUpdated)
          .map((row, index) => ({ ...row, sNo: index + 1 }));
        this.loading = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.activityRows = [];
        this.loading = false;
        this.cdr.markForCheck();
      }
    });
  }

  private groupArtifactRows(rows: ActivityRow[]): ActivityRow[] {
    const grouped = new Map<string, ActivityRow>();

    for (const row of rows) {
      const feature = this.normalizeFeature(row.artifact?.feature || row.feature);
      const isSupportedArtifact = row.artifact?.fileType === 'PDF'
        || (feature === 'defect_triage' && row.artifact?.fileType === 'JSON');
      if (!this.artifactFeatures.includes(feature as string)
        || !row.artifact?.id
        || !row.artifact?.canView
        || !isSupportedArtifact) {
        continue;
      }

      const documentKey = row.documentId ?? row.knowledgeBase.toLowerCase();
      const key = `${row.projectId ?? ''}::${documentKey}::${row.version}`;
      let groupedRow = grouped.get(key);
      if (!groupedRow) {
        groupedRow = {
          ...row,
          artifacts: {},
          userStory: null,
          functionalDesign: null,
          technicalDesign: null,
          requirementAnalysis: null,
          testGenerator: null,
          defectTriage: null,
          releaseNotes: null
        };
        grouped.set(key, groupedRow);
      }

      groupedRow.artifacts[feature as keyof ActivityRow['artifacts']] = row.artifact;
      groupedRow.lastUpdated = Math.max(groupedRow.lastUpdated, row.lastUpdated);
    }

    return Array.from(grouped.values());
  }

  private normalizeFeature(feature: string): string {
    return (feature || '').toLowerCase().replace(/[-\s]/g, '_');
  }

  private isSupportedSourceDocument(document: any): boolean {
    return document.status === 'COMPLETED' && !!document.id && !!document.fileName;
  }

  private toActivityRow(item: any, project: any, documents: any[]): ActivityRow {
    const sourceDocument = documents.find((document) => Number(document.id) === Number(item.documentId));
    const feature = this.normalizeFeature(item.feature);
    return {
      sNo: 0,
      projectId: Number(project.id),
      documentId: item.documentId ? Number(item.documentId) : null,
      projectName: item.projectName || project.projectName || '—',
      knowledgeBase: item.documentName || sourceDocument?.fileName || '—',
      version: String(item.version),
      artifacts: {},
      feature,
      artifact: item,
      category: '—',
      userStory: null,
      functionalDesign: null,
      technicalDesign: null,
      requirementAnalysis: null,
      testGenerator: null,
      defectTriage: null,
      releaseNotes: null,
      lastUpdated: new Date(item.createdAt || 0).getTime()
    };
  }

  viewArtifact(row: ActivityRow, feature: keyof ActivityRow['artifacts'], event: MouseEvent): void {
    event.stopPropagation();
    const artifact = row.artifacts[feature];
    if (!artifact?.id) return;
    this.artifactViewer?.viewDocument({
      ...artifact,
      id: artifact.id,
      feature,
      projectName: row.projectName,
      sourceDocumentName: row.knowledgeBase,
      documentName: row.knowledgeBase,
      version: row.version
    });
  }

  downloadTestCasesExcel(row: ActivityRow, event: MouseEvent): void {
    event.stopPropagation();
    const artifact = row.artifacts.test_generator;
    if (artifact) {
      this.artifactViewer?.downloadTestGeneratorExcel(artifact);
    }
  }

  downloadTestCasesCsv(row: ActivityRow, event: MouseEvent): void {
    event.stopPropagation();
    const artifact = row.artifacts.test_generator;
    if (artifact) {
      this.artifactViewer?.downloadTestGeneratorCsv(artifact);
    }
  }

  downloadDefectTriageExcel(row: ActivityRow, event: MouseEvent): void {
    event.stopPropagation();
    const artifact = row.artifacts.defect_triage;
    if (artifact) {
      this.artifactViewer?.downloadDefectTriageExcel(artifact);
    }
  }

  downloadDefectTriageCsv(row: ActivityRow, event: MouseEvent): void {
    event.stopPropagation();
    const artifact = row.artifacts.defect_triage;
    if (artifact) {
      this.artifactViewer?.downloadDefectTriageCsv(artifact);
    }
  }

  downloadDocument(row: ActivityRow, event: MouseEvent): void {
    event.stopPropagation();
    if (!row.documentId) return;

    this.api.downloadDocument(row.documentId).subscribe({
      next: (blob: Blob) => {
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = row.knowledgeBase || `document-${row.documentId}`;
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

  loadProjects() {
    this.api.getProjects().subscribe({
      next: (res) => {
        if (res.success && res.data) {
          this.allProjects = res.data;
          if (this.rawLogs && this.rawLogs.length > 0) {
            this.processActivityRows(this.rawLogs);
          }
        }
        this.cdr.markForCheck();
      },
      error: () => {}
    });
  }

  loadDocuments() {
    this.api.getDocuments().subscribe({
      next: (res) => {
        if (res.success && res.data) {
          this.allDocuments = res.data;
        }
        this.cdr.markForCheck();
      },
      error: () => {}
    });
  }

  processActivityRows(logs: any[]) {
    if (!logs || logs.length === 0) {
      this.activityRows = [];
      return;
    }

    // Set of active projects currently present in Knowledge Base
    const validProjectIds = new Set<number>(
      (this.allProjects || []).map((p) => Number(p.id)).filter((id) => !isNaN(id) && id > 0)
    );
    const validProjectNames = new Set<string>(
      (this.allProjects || []).map((p) => (p.projectName || '').trim().toLowerCase()).filter(Boolean)
    );

    const activityMap = new Map<string, ActivityRow>();

    // Process from oldest to newest so newest statuses take precedence
    const sorted = [...logs].sort((a, b) => {
      const ta = new Date(a.createdAt || a.timestamp || 0).getTime();
      const tb = new Date(b.createdAt || b.timestamp || 0).getTime();
      return ta - tb;
    });

    for (const log of sorted) {
      if (log.action === 'DELETE_PROJECT') {
        continue;
      }

      const logProjId = log.projectId ? Number(log.projectId) : null;
      const logProjName = (log.projectName && log.projectName.trim()) ? log.projectName.trim() : '';

      // ONLY projects currently present in Knowledge Base are allowed
      if (this.allProjects.length > 0) {
        const matchesId = logProjId && validProjectIds.has(logProjId);
        const matchesName = logProjName && validProjectNames.has(logProjName.toLowerCase());
        if (!matchesId && !matchesName) {
          // Project was deleted from Knowledge Base — do NOT display
          continue;
        }
      } else {
        // Projects not yet loaded or empty — do not display stale data
        continue;
      }

      const matchedProj = this.allProjects.find(
        (p) => (logProjId && Number(p.id) === logProjId) ||
               (logProjName && (p.projectName || '').trim().toLowerCase() === logProjName.toLowerCase())
      );
      const proj = matchedProj ? matchedProj.projectName : logProjName;
      const doc = (log.documentName && log.documentName.trim()) ? log.documentName.trim() : '—';
      const groupKey = `${proj}:::${doc}`;

      if (!activityMap.has(groupKey)) {
        activityMap.set(groupKey, {
          sNo: 0,
          projectId: matchedProj ? Number(matchedProj.id) : logProjId,
          documentId: log.documentId ? Number(log.documentId) : null,
          artifactId: 0,
          projectName: proj,
          knowledgeBase: doc,
          version: '',
          artifacts: {},
          feature: '',
          artifact: log,
          category: this.formatCategory(log),
          userStory: null,
          functionalDesign: null,
          technicalDesign: null,
          requirementAnalysis: null,
          testGenerator: null,
          defectTriage: null,
          releaseNotes: null,
          lastUpdated: new Date(log.createdAt || log.timestamp || 0).getTime()
        });
      }

      const row = activityMap.get(groupKey)!;
      if (!row.projectId && logProjId) {
        row.projectId = logProjId;
      }
      if (!row.documentId && log.documentId) {
        row.documentId = Number(log.documentId);
      }

      const logTime = new Date(log.createdAt || log.timestamp || 0).getTime();
      if (logTime > row.lastUpdated) {
        row.lastUpdated = logTime;
      }

      const cat = this.formatCategory(log);
      if (cat && cat !== '—' && (row.category === '—' || !row.category)) {
        row.category = cat;
      }

      const feat = (log.feature || '').toLowerCase().trim();
      const status = log.status || 'COMPLETED';

      if (feat.includes('user story')) {
        row.userStory = status;
      } else if (feat.includes('functional design')) {
        row.functionalDesign = status;
      } else if (feat.includes('technical design')) {
        row.technicalDesign = status;
      } else if (feat.includes('requirement')) {
        row.requirementAnalysis = status;
      } else if (feat.includes('test')) {
        row.testGenerator = status;
      } else if (feat.includes('defect')) {
        row.defectTriage = status;
      } else if (feat.includes('release')) {
        row.releaseNotes = status;
      }
    }

    // Filter out dummy '—' rows if the project already has actual document rows
    const projectHasDocRows = new Set<string>();
    for (const r of activityMap.values()) {
      if (r.knowledgeBase && r.knowledgeBase !== '—') {
        projectHasDocRows.add(r.projectName.toLowerCase());
      }
    }

    const filteredRows = Array.from(activityMap.values()).filter((r) => {
      if (r.knowledgeBase === '—' && projectHasDocRows.has(r.projectName.toLowerCase())) {
        return false;
      }
      return true;
    });

    // Sort by most recent activity timestamp descending
    const rows = filteredRows.sort((a, b) => b.lastUpdated - a.lastUpdated);

    rows.forEach((r, idx) => {
      r.sNo = idx + 1;
    });

    this.activityRows = rows;
  }

  downloadFiles(row: ActivityRow, event?: MouseEvent) {
    if (event) {
      event.stopPropagation();
    }

    const filesToDownload: any[] = [];
    const seenDocIds = new Set<number>();

    // 1. Resolve Project ID
    let resolvedProjectId: number | null = row.projectId;
    if (!resolvedProjectId && row.projectName && row.projectName !== 'General' && row.projectName !== '—') {
      const matchProj = this.allProjects.find(
        (p) => (p.projectName || '').trim().toLowerCase() === row.projectName.trim().toLowerCase()
      );
      if (matchProj) {
        resolvedProjectId = Number(matchProj.id);
      }
    }

    // 2. If row specifies an exact document, download ONLY that document
    if (row.knowledgeBase && row.knowledgeBase !== '—' && row.knowledgeBase !== 'Direct Text Input') {
      const matchDoc = this.allDocuments.find(
        (d) => (d.fileName || '').trim().toLowerCase() === row.knowledgeBase.trim().toLowerCase()
      );
      if (matchDoc) {
        filesToDownload.push(matchDoc);
      }
    }

    // 3. Only if no specific document was matched from the row, download corresponding project documents
    if (filesToDownload.length === 0 && resolvedProjectId) {
      const projectDocs = this.allDocuments.filter((d) => Number(d.projectId) === resolvedProjectId);

      // Identify corresponding BRD file
      const brdDoc = projectDocs.find((d) => {
        if (seenDocIds.has(Number(d.id))) return false;
        const ft = (d.fileType || '').toUpperCase();
        const fn = (d.fileName || '').toLowerCase();
        return ft === 'BRD' || fn.endsWith('.pdf') || fn.endsWith('.docx') || fn.endsWith('.doc') || fn.endsWith('.txt');
      });

      if (brdDoc) {
        seenDocIds.add(Number(brdDoc.id));
        filesToDownload.push(brdDoc);
      }

      // Identify corresponding Codebase file
      const codebaseDoc = projectDocs.find((d) => {
        if (seenDocIds.has(Number(d.id))) return false;
        const ft = (d.fileType || '').toUpperCase();
        const fn = (d.fileName || '').toLowerCase();
        return ft === 'ZIP' || ft === 'CODEBASE' || fn.endsWith('.zip');
      });

      if (codebaseDoc) {
        seenDocIds.add(Number(codebaseDoc.id));
        filesToDownload.push(codebaseDoc);
      }

      // Fallback: If neither was categorized but project has docs, add them
      if (filesToDownload.length === 0 && projectDocs.length > 0) {
        for (const pd of projectDocs) {
          if (!seenDocIds.has(Number(pd.id))) {
            seenDocIds.add(Number(pd.id));
            filesToDownload.push(pd);
          }
        }
      }
    }

    // 4. Handle missing files gracefully
    if (filesToDownload.length === 0) {
      alert(`No uploaded BRD or Codebase files available for ${row.projectName !== '—' ? row.projectName : 'this activity'}.`);
      return;
    }

    // 5. Trigger direct browser download for each resolved file (staggered to prevent browser cancellation)
    this.downloadingSNo = row.sNo;
    this.cdr.markForCheck();

    filesToDownload.forEach((doc, idx) => {
      setTimeout(() => {
        const downloadUrl = this.api.getDocumentDownloadUrl(Number(doc.id));
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = doc.fileName || `document-${doc.id}`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);

        if (idx === filesToDownload.length - 1) {
          setTimeout(() => {
            this.downloadingSNo = null;
            this.cdr.markForCheck();
          }, 400);
        }
      }, idx * 600);
    });
  }

  getCategoryLabel(row: ActivityRow): string {
    if (!row) return '';

    // 1. Resolve document from row
    let doc: any = null;
    if (row.documentId) {
      doc = this.allDocuments.find((d) => Number(d.id) === row.documentId);
    }
    if (!doc && row.knowledgeBase && row.knowledgeBase !== '—' && row.knowledgeBase !== 'Direct Text Input') {
      doc = this.allDocuments.find(
        (d) => (d.fileName || '').trim().toLowerCase() === row.knowledgeBase.trim().toLowerCase()
      );
    }

    // 2. Check document's actual uploaded fileType and fileName
    if (doc) {
      const ft = (doc.fileType || '').toUpperCase().trim();
      const fn = (doc.fileName || '').toLowerCase().trim();
      if (ft === 'ZIP' || ft === 'CODEBASE' || ft.includes('ZIP') || fn.endsWith('.zip') || fn.endsWith('.tar') || fn.endsWith('.gz') || fn.endsWith('.7z')) {
        return '(Code Base)';
      }
      if (ft === 'BRD' || ft.includes('PDF') || fn.endsWith('.pdf') || fn.endsWith('.docx') || fn.endsWith('.doc') || fn.endsWith('.txt')) {
        return '(BRD)';
      }
    }

    // 3. Fallback to knowledgeBase filename if document wasn't matched in list
    const kb = (row.knowledgeBase || '').toLowerCase().trim();
    if (kb.endsWith('.zip') || kb.endsWith('.tar') || kb.endsWith('.gz') || kb.endsWith('.7z')) {
      return '(Code Base)';
    }
    if (kb.endsWith('.pdf') || kb.endsWith('.docx') || kb.endsWith('.doc') || kb.endsWith('.txt')) {
      return '(BRD)';
    }

    // 4. Fallback for rows where knowledgeBase is '—' (project-level activity)
    let resolvedProjectId: number | null = row.projectId;
    if (!resolvedProjectId && row.projectName && row.projectName !== 'General' && row.projectName !== '—') {
      const matchProj = this.allProjects.find(
        (p) => (p.projectName || '').trim().toLowerCase() === row.projectName.trim().toLowerCase()
      );
      if (matchProj) {
        resolvedProjectId = Number(matchProj.id);
      }
    }
    if (resolvedProjectId) {
      const projectDocs = this.allDocuments.filter((d) => Number(d.projectId) === resolvedProjectId);
      const brdDoc = projectDocs.find((d) => {
        const ft = (d.fileType || '').toUpperCase();
        const fn = (d.fileName || '').toLowerCase();
        return ft === 'BRD' || fn.endsWith('.pdf') || fn.endsWith('.docx') || fn.endsWith('.doc') || fn.endsWith('.txt');
      });
      const zipDoc = projectDocs.find((d) => {
        const ft = (d.fileType || '').toUpperCase();
        const fn = (d.fileName || '').toLowerCase();
        return ft === 'ZIP' || ft === 'CODEBASE' || fn.endsWith('.zip');
      });

      if (brdDoc && !zipDoc) return '(BRD)';
      if (zipDoc && !brdDoc) return '(Code Base)';
      if (brdDoc) return '(BRD)';
    }

    // 5. Check row.category
    const cat = (row.category || '').toLowerCase().trim();
    if (cat.includes('codebase') || cat === 'zip') return '(Code Base)';
    if (cat.includes('brd')) return '(BRD)';

    return '';
  }

  formatCategory(log: any): string {
    const raw = log.inputType || log.category || '';
    if (!raw) {
      if (log.documentName) {
        const lower = log.documentName.toLowerCase();
        if (lower.endsWith('.zip')) return 'Codebase';
        if (lower.endsWith('.pdf') || lower.endsWith('.doc') || lower.endsWith('.docx') || lower.endsWith('.txt')) return 'BRD';
      }
      return 'BRD';
    }

    const trimmed = raw.trim();
    if (trimmed.toUpperCase() === 'KNOWLEDGE_BASE') return 'Knowledge Base';
    if (trimmed.toLowerCase().includes('codebase') || trimmed.toUpperCase() === 'ZIP') return 'Codebase';
    if (trimmed.toLowerCase().includes('brd')) return 'BRD';
    return trimmed;
  }

  getStatusBadgeClass(status: string): string {
    if (!status) return '';
    const s = status.toUpperCase();
    if (s === 'SUCCESS' || s === 'ACCEPTED' || s === 'COMPLETED') {
      return 'status-badge status-success';
    }
    if (s === 'FAILED' || s === 'ERROR' || s === 'REJECTED') {
      return 'status-badge status-failed';
    }
    return 'status-badge status-info';
  }

  formatStatus(status: string): string {
    if (!status) return '—';
    return status.toUpperCase();
  }

  formatDate(timestamp: string) {
    if (!timestamp) return '';
    const d = new Date(timestamp);
    return `${d.toLocaleDateString()} ${d.toLocaleTimeString()}`;
  }
}

