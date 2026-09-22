import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../core/api';

export interface ActivityRow {
  sNo: number;
  projectId: number | null;
  documentId: number | null;
  projectName: string;
  knowledgeBase: string;
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
  imports: [CommonModule],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.scss'
})
export class Dashboard implements OnInit {
  stats: any = null;
  recentActivity: any[] = [];
  activityRows: ActivityRow[] = [];
  allDocuments: any[] = [];
  allProjects: any[] = [];
  downloadingSNo: number | null = null;
  loading = true;

  constructor(private api: ApiService, private cdr: ChangeDetectorRef) {}

  ngOnInit() {
    this.loadProjects();
    this.loadDocuments();

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

    this.api.getRecentActivity().subscribe({
      next: (res) => {
        if (res.success && res.data) {
          this.recentActivity = res.data;
          this.processActivityRows(this.recentActivity);
        }
        this.cdr.markForCheck();
      }
    });

    this.api.getAuditLogs('ALL').subscribe({
      next: (res) => {
        if (res.success && res.data && res.data.length > 0) {
          this.processActivityRows(res.data);
        }
        this.cdr.markForCheck();
      },
      error: () => {}
    });
  }

  loadProjects() {
    this.api.getProjects().subscribe({
      next: (res) => {
        if (res.success && res.data) {
          this.allProjects = res.data;
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
      return;
    }

    const activityMap = new Map<string, ActivityRow>();

    // Process from oldest to newest so newest statuses take precedence
    const sorted = [...logs].sort((a, b) => {
      const ta = new Date(a.createdAt || a.timestamp || 0).getTime();
      const tb = new Date(b.createdAt || b.timestamp || 0).getTime();
      return ta - tb;
    });

    for (const log of sorted) {
      const proj = (log.projectName && log.projectName.trim()) ? log.projectName.trim() : 'General';
      const doc = (log.documentName && log.documentName.trim()) ? log.documentName.trim() : '—';
      const groupKey = `${proj}:::${doc}`;

      if (!activityMap.has(groupKey)) {
        activityMap.set(groupKey, {
          sNo: 0,
          projectId: log.projectId ? Number(log.projectId) : null,
          documentId: log.documentId ? Number(log.documentId) : null,
          projectName: proj,
          knowledgeBase: doc,
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
      if (!row.projectId && log.projectId) {
        row.projectId = Number(log.projectId);
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

    // Sort by most recent activity timestamp descending
    const rows = Array.from(activityMap.values()).sort((a, b) => b.lastUpdated - a.lastUpdated);

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

