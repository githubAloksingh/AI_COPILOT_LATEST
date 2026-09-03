import { Injectable } from '@angular/core';
import { jsPDF } from 'jspdf';

@Injectable({
  providedIn: 'root'
})
export class ExportService {

  // ==========================================
  // CSV EXPORT (TEST CASES ONLY)
  // RFC 4180 Compliant
  // ==========================================
  downloadTestCaseCsv(items: any[], baseFilename = 'test-cases'): void {
    if (!items || items.length === 0) {
      alert('No test case data available to export.');
      return;
    }

    const headers = [
      'Test Case ID',
      'Scenario / Title',
      'Type',
      'Priority',
      'Preconditions',
      'Test Steps',
      'Expected Result'
    ];

    const escapeCsvCell = (val: any): string => {
      if (val === null || val === undefined) return '""';
      if (Array.isArray(val)) {
        val = val.join('\n');
      }
      const str = String(val);
      // Double up existing quotes and wrap in quotes
      const escaped = str.replace(/"/g, '""');
      return `"${escaped}"`;
    };

    const rows: string[] = [];
    rows.push(headers.map(h => escapeCsvCell(h)).join(','));

    items.forEach((item, index) => {
      const tcId = item.tcId || `TC-${String(index + 1).padStart(3, '0')}`;
      const scenario = item.scenario || '';
      const type = item.type || 'POSITIVE';
      const priority = item.priority || 'MEDIUM';
      const preconditions = item.preconditions ? (Array.isArray(item.preconditions) ? item.preconditions.join('\n') : item.preconditions) : '';
      const steps = item.steps ? (Array.isArray(item.steps) ? item.steps.map((s: string, i: number) => `${i + 1}. ${s}`).join('\n') : item.steps) : '';
      const expectedResult = item.expectedResult || '';

      const row = [
        escapeCsvCell(tcId),
        escapeCsvCell(scenario),
        escapeCsvCell(type),
        escapeCsvCell(priority),
        escapeCsvCell(preconditions),
        escapeCsvCell(steps),
        escapeCsvCell(expectedResult)
      ];
      rows.push(row.join(','));
    });

    const csvContent = '\uFEFF' + rows.join('\r\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    this.triggerDownload(blob, `${baseFilename}-${this.getTimestampSuffix()}.csv`);
  }

  // ==========================================
  // PDF EXPORT (REQUIREMENTS)
  // ==========================================
  downloadRequirementPdf(data: any, baseFilename = 'requirement'): void {
    const doc = new jsPDF({ unit: 'pt', format: 'a4' });
    const pageWidth = doc.internal.pageSize.getWidth();
    const margin = 40;
    const contentWidth = pageWidth - (margin * 2);
    let y = 40;

    const checkPageBreak = (neededHeight: number) => {
      if (y + neededHeight > doc.internal.pageSize.getHeight() - 40) {
        doc.addPage();
        y = 40;
      }
    };

    // Header Title
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(20);
    doc.setTextColor(15, 23, 42);
    doc.text('Software Requirement Specification', margin, y);
    y += 24;

    // Subtitle & Priority
    doc.setFontSize(10);
    doc.setFont('helvetica', 'normal');
    doc.setTextColor(100, 116, 139);
    doc.text(`Generated & Accepted: ${new Date().toLocaleString()} | Priority: ${data.priority || 'Medium'}`, margin, y);
    y += 20;

    // Horizontal divider
    doc.setDrawColor(226, 232, 240);
    doc.line(margin, y, margin + contentWidth, y);
    y += 18;

    // Requirement Title
    if (data.title) {
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(14);
      doc.setTextColor(30, 41, 59);
      doc.text(data.title, margin, y);
      y += 20;
    }

    // Summary Section
    if (data.summary) {
      checkPageBreak(50);
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(12);
      doc.setTextColor(30, 41, 59);
      doc.text('Summary', margin, y);
      y += 14;

      doc.setFont('helvetica', 'normal');
      doc.setFontSize(10);
      doc.setTextColor(51, 65, 85);
      const splitSummary = doc.splitTextToSize(data.summary, contentWidth);
      doc.text(splitSummary, margin, y);
      y += (splitSummary.length * 13) + 14;
    }



    // Acceptance Criteria
    if (data.acceptanceCriteria && data.acceptanceCriteria.length > 0) {
      checkPageBreak(60);
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(12);
      doc.setTextColor(30, 41, 59);
      doc.text('Acceptance Criteria', margin, y);
      y += 14;

      doc.setFont('helvetica', 'normal');
      doc.setFontSize(10);
      doc.setTextColor(51, 65, 85);
      data.acceptanceCriteria.forEach((ac: string) => {
        const itemText = `•  ${ac}`;
        const splitAc = doc.splitTextToSize(itemText, contentWidth - 10);
        checkPageBreak(splitAc.length * 13 + 4);
        doc.text(splitAc, margin + 5, y);
        y += (splitAc.length * 13) + 4;
      });
      y += 10;
    }

    // Assumptions
    if (data.assumptions && data.assumptions.length > 0) {
      checkPageBreak(50);
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(12);
      doc.setTextColor(30, 41, 59);
      doc.text('Assumptions', margin, y);
      y += 14;

      doc.setFont('helvetica', 'normal');
      doc.setFontSize(10);
      doc.setTextColor(51, 65, 85);
      data.assumptions.forEach((as: string) => {
        const itemText = `•  ${as}`;
        const splitAs = doc.splitTextToSize(itemText, contentWidth - 10);
        checkPageBreak(splitAs.length * 13 + 4);
        doc.text(splitAs, margin + 5, y);
        y += (splitAs.length * 13) + 4;
      });
      y += 10;
    }

    // Dependencies
    if (data.dependencies && data.dependencies.length > 0) {
      checkPageBreak(50);
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(12);
      doc.setTextColor(30, 41, 59);
      doc.text('Dependencies', margin, y);
      y += 14;

      doc.setFont('helvetica', 'normal');
      doc.setFontSize(10);
      doc.setTextColor(51, 65, 85);
      data.dependencies.forEach((dp: string) => {
        const itemText = `•  ${dp}`;
        const splitDp = doc.splitTextToSize(itemText, contentWidth - 10);
        checkPageBreak(splitDp.length * 13 + 4);
        doc.text(splitDp, margin + 5, y);
        y += (splitDp.length * 13) + 4;
      });
      y += 10;
    }

    // Edge Cases
    if (data.edgeCases && data.edgeCases.length > 0) {
      checkPageBreak(50);
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(12);
      doc.setTextColor(30, 41, 59);
      doc.text('Edge Cases', margin, y);
      y += 14;

      doc.setFont('helvetica', 'normal');
      doc.setFontSize(10);
      doc.setTextColor(51, 65, 85);
      data.edgeCases.forEach((ec: string) => {
        const itemText = `•  ${ec}`;
        const splitEc = doc.splitTextToSize(itemText, contentWidth - 10);
        checkPageBreak(splitEc.length * 13 + 4);
        doc.text(splitEc, margin + 5, y);
        y += (splitEc.length * 13) + 4;
      });
      y += 10;
    }

    doc.save(`${baseFilename}-${this.getTimestampSuffix()}.pdf`);
  }

  // ==========================================
  // PDF EXPORT (ALL REQUIREMENTS — ONE PDF)
  // ==========================================
  downloadAllRequirementsPdf(requirements: any[], baseFilename = 'requirements'): void {
    if (!requirements || requirements.length === 0) {
      alert('No requirements available to export.');
      return;
    }

    const doc = new jsPDF({ unit: 'pt', format: 'a4' });
    const pageWidth = doc.internal.pageSize.getWidth();
    const margin = 40;
    const contentWidth = pageWidth - (margin * 2);
    let y = 40;

    const checkPageBreak = (neededHeight: number) => {
      if (y + neededHeight > doc.internal.pageSize.getHeight() - 40) {
        doc.addPage();
        y = 40;
      }
    };

    // ── Document Header ──────────────────────────────────────
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(20);
    doc.setTextColor(15, 23, 42);
    doc.text('Software Requirement Specification', margin, y);
    y += 24;

    doc.setFontSize(10);
    doc.setFont('helvetica', 'normal');
    doc.setTextColor(100, 116, 139);
    doc.text(`Generated & Accepted: ${new Date().toLocaleString()} | Total Requirements: ${requirements.length}`, margin, y);
    y += 20;

    doc.setDrawColor(226, 232, 240);
    doc.line(margin, y, margin + contentWidth, y);
    y += 24;

    // ── Each Requirement ─────────────────────────────────────
    requirements.forEach((data: any, idx: number) => {
      // Requirement divider heading
      checkPageBreak(60);

      // Colored background banner for req ID + title
      doc.setFillColor(241, 245, 249);
      doc.roundedRect(margin, y - 14, contentWidth, 26, 4, 4, 'F');

      doc.setFont('helvetica', 'bold');
      doc.setFontSize(13);
      doc.setTextColor(30, 41, 59);
      const reqLabel = data.requirementId ? `${data.requirementId}  —  ${data.title || ''}` : (data.title || `Requirement ${idx + 1}`);
      const splitLabel = doc.splitTextToSize(reqLabel, contentWidth - 10);
      doc.text(splitLabel, margin + 6, y);
      y += (splitLabel.length * 16) + 10;

      // Priority
      if (data.priority) {
        doc.setFont('helvetica', 'normal');
        doc.setFontSize(9);
        doc.setTextColor(100, 116, 139);
        doc.text(`Priority: ${data.priority}`, margin, y);
        y += 14;
      }

      // Summary
      if (data.summary) {
        checkPageBreak(50);
        doc.setFont('helvetica', 'bold');
        doc.setFontSize(11);
        doc.setTextColor(30, 41, 59);
        doc.text('Summary', margin, y);
        y += 13;

        doc.setFont('helvetica', 'normal');
        doc.setFontSize(10);
        doc.setTextColor(51, 65, 85);
        const splitSummary = doc.splitTextToSize(data.summary, contentWidth);
        doc.text(splitSummary, margin, y);
        y += (splitSummary.length * 13) + 12;
      }

      // Acceptance Criteria
      if (data.acceptanceCriteria && data.acceptanceCriteria.length > 0) {
        checkPageBreak(50);
        doc.setFont('helvetica', 'bold');
        doc.setFontSize(11);
        doc.setTextColor(30, 41, 59);
        doc.text('Acceptance Criteria', margin, y);
        y += 13;

        doc.setFont('helvetica', 'normal');
        doc.setFontSize(10);
        doc.setTextColor(51, 65, 85);
        data.acceptanceCriteria.forEach((ac: string) => {
          const itemText = `•  ${ac}`;
          const splitAc = doc.splitTextToSize(itemText, contentWidth - 10);
          checkPageBreak(splitAc.length * 13 + 4);
          doc.text(splitAc, margin + 5, y);
          y += (splitAc.length * 13) + 4;
        });
        y += 8;
      }

      // Assumptions
      if (data.assumptions && data.assumptions.length > 0) {
        checkPageBreak(40);
        doc.setFont('helvetica', 'bold');
        doc.setFontSize(11);
        doc.setTextColor(30, 41, 59);
        doc.text('Assumptions', margin, y);
        y += 13;

        doc.setFont('helvetica', 'normal');
        doc.setFontSize(10);
        doc.setTextColor(51, 65, 85);
        data.assumptions.forEach((as: string) => {
          const itemText = `•  ${as}`;
          const splitAs = doc.splitTextToSize(itemText, contentWidth - 10);
          checkPageBreak(splitAs.length * 13 + 4);
          doc.text(splitAs, margin + 5, y);
          y += (splitAs.length * 13) + 4;
        });
        y += 8;
      }

      // Dependencies
      if (data.dependencies && data.dependencies.length > 0) {
        checkPageBreak(40);
        doc.setFont('helvetica', 'bold');
        doc.setFontSize(11);
        doc.setTextColor(30, 41, 59);
        doc.text('Dependencies', margin, y);
        y += 13;

        doc.setFont('helvetica', 'normal');
        doc.setFontSize(10);
        doc.setTextColor(51, 65, 85);
        data.dependencies.forEach((dp: string) => {
          const itemText = `•  ${dp}`;
          const splitDp = doc.splitTextToSize(itemText, contentWidth - 10);
          checkPageBreak(splitDp.length * 13 + 4);
          doc.text(splitDp, margin + 5, y);
          y += (splitDp.length * 13) + 4;
        });
        y += 8;
      }

      // Edge Cases
      if (data.edgeCases && data.edgeCases.length > 0) {
        checkPageBreak(40);
        doc.setFont('helvetica', 'bold');
        doc.setFontSize(11);
        doc.setTextColor(30, 41, 59);
        doc.text('Edge Cases', margin, y);
        y += 13;

        doc.setFont('helvetica', 'normal');
        doc.setFontSize(10);
        doc.setTextColor(51, 65, 85);
        data.edgeCases.forEach((ec: string) => {
          const itemText = `•  ${ec}`;
          const splitEc = doc.splitTextToSize(itemText, contentWidth - 10);
          checkPageBreak(splitEc.length * 13 + 4);
          doc.text(splitEc, margin + 5, y);
          y += (splitEc.length * 13) + 4;
        });
        y += 8;
      }

      // Separator between requirements (not after the last one)
      if (idx < requirements.length - 1) {
        checkPageBreak(30);
        doc.setDrawColor(203, 213, 225);
        doc.setLineDashPattern([4, 3], 0);
        doc.line(margin, y + 4, margin + contentWidth, y + 4);
        doc.setLineDashPattern([], 0);
        y += 24;
      }
    });

    doc.save(`${baseFilename}-${this.getTimestampSuffix()}.pdf`);
  }

  // ==========================================
  // PDF EXPORT (DEFECT TRIAGE)
  // ==========================================
  downloadDefectPdf(data: any, baseFilename = 'defect-triage'): void {
    const doc = new jsPDF({ unit: 'pt', format: 'a4' });
    const pageWidth = doc.internal.pageSize.getWidth();
    const margin = 40;
    const contentWidth = pageWidth - (margin * 2);
    let y = 40;

    const checkPageBreak = (neededHeight: number) => {
      if (y + neededHeight > doc.internal.pageSize.getHeight() - 40) {
        doc.addPage();
        y = 40;
      }
    };

    // Header
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(20);
    doc.setTextColor(15, 23, 42);
    doc.text('Defect Triage Report', margin, y);
    y += 24;

    doc.setFontSize(10);
    doc.setFont('helvetica', 'normal');
    doc.setTextColor(100, 116, 139);
    doc.text(`Severity: ${data.severity || 'MEDIUM'} | Priority: ${data.priority || 'P2'} | Confidence: ${data.confidence || 'HIGH'}`, margin, y);
    y += 20;

    doc.setDrawColor(226, 232, 240);
    doc.line(margin, y, margin + contentWidth, y);
    y += 18;

    if (data.title) {
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(14);
      doc.setTextColor(30, 41, 59);
      doc.text(data.title, margin, y);
      y += 20;
    }

    // Probable Root Cause
    if (data.probableRootCause) {
      checkPageBreak(60);
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(12);
      doc.setTextColor(185, 28, 28);
      doc.text('Probable Root Cause', margin, y);
      y += 14;

      doc.setFont('helvetica', 'normal');
      doc.setFontSize(10);
      doc.setTextColor(51, 65, 85);
      const splitRc = doc.splitTextToSize(data.probableRootCause, contentWidth);
      doc.text(splitRc, margin, y);
      y += (splitRc.length * 13) + 14;
    }

    // Suggested Fix
    if (data.suggestedFix) {
      checkPageBreak(60);
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(12);
      doc.setTextColor(16, 185, 129);
      doc.text('Suggested Fix / Resolution', margin, y);
      y += 14;

      doc.setFont('courier', 'normal');
      doc.setFontSize(9);
      doc.setTextColor(30, 41, 59);
      const splitFix = doc.splitTextToSize(data.suggestedFix, contentWidth);
      doc.text(splitFix, margin, y);
      y += (splitFix.length * 12) + 14;
    }

    // Evidence & Stack Trace Analysis
    if (data.evidence) {
      checkPageBreak(50);
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(12);
      doc.setTextColor(30, 41, 59);
      doc.text('Evidence & Technical Analysis', margin, y);
      y += 14;

      doc.setFont('helvetica', 'normal');
      doc.setFontSize(10);
      doc.setTextColor(51, 65, 85);
      const splitEvidence = doc.splitTextToSize(data.evidence, contentWidth);
      doc.text(splitEvidence, margin, y);
      y += (splitEvidence.length * 13) + 14;
    }

    // Suggested Investigation
    if (data.suggestedInvestigation) {
      checkPageBreak(50);
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(12);
      doc.setTextColor(30, 41, 59);
      doc.text('Suggested Investigation Steps', margin, y);
      y += 14;

      doc.setFont('helvetica', 'normal');
      doc.setFontSize(10);
      doc.setTextColor(51, 65, 85);
      const splitInv = doc.splitTextToSize(data.suggestedInvestigation, contentWidth);
      doc.text(splitInv, margin, y);
      y += (splitInv.length * 13) + 14;
    }

    doc.save(`${baseFilename}-${this.getTimestampSuffix()}.pdf`);
  }

  // ==========================================
  // PDF EXPORT (RELEASE NOTES)
  // ==========================================
  downloadReleaseNotePdf(data: any, baseFilename = 'release-notes'): void {
    const doc = new jsPDF({ unit: 'pt', format: 'a4' });
    const pageWidth = doc.internal.pageSize.getWidth();
    const margin = 40;
    const contentWidth = pageWidth - (margin * 2);
    let y = 40;

    const checkPageBreak = (neededHeight: number) => {
      if (y + neededHeight > doc.internal.pageSize.getHeight() - 40) {
        doc.addPage();
        y = 40;
      }
    };

    // Header
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(20);
    doc.setTextColor(15, 23, 42);
    doc.text(`Release Notes — Version ${data.version || '1.0.0'}`, margin, y);
    y += 24;

    doc.setFontSize(10);
    doc.setFont('helvetica', 'normal');
    doc.setTextColor(100, 116, 139);
    doc.text(`Generated: ${new Date().toLocaleDateString()}`, margin, y);
    y += 18;

    doc.setDrawColor(226, 232, 240);
    doc.line(margin, y, margin + contentWidth, y);
    y += 18;

    // Summary
    if (data.summary) {
      checkPageBreak(50);
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(12);
      doc.setTextColor(30, 41, 59);
      doc.text('Summary', margin, y);
      y += 14;

      doc.setFont('helvetica', 'normal');
      doc.setFontSize(10);
      doc.setTextColor(51, 65, 85);
      const splitSummary = doc.splitTextToSize(data.summary, contentWidth);
      doc.text(splitSummary, margin, y);
      y += (splitSummary.length * 13) + 14;
    }

    // New Features
    if (data.newFeatures && data.newFeatures.length > 0) {
      checkPageBreak(50);
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(12);
      doc.setTextColor(16, 185, 129);
      doc.text('New Features', margin, y);
      y += 14;

      doc.setFont('helvetica', 'normal');
      doc.setFontSize(10);
      doc.setTextColor(51, 65, 85);
      data.newFeatures.forEach((f: string) => {
        const itemText = `•  ${f}`;
        const splitF = doc.splitTextToSize(itemText, contentWidth - 10);
        checkPageBreak(splitF.length * 13 + 4);
        doc.text(splitF, margin + 5, y);
        y += (splitF.length * 13) + 4;
      });
      y += 10;
    }

    // Improvements
    if (data.improvements && data.improvements.length > 0) {
      checkPageBreak(50);
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(12);
      doc.setTextColor(59, 130, 246);
      doc.text('Improvements', margin, y);
      y += 14;

      doc.setFont('helvetica', 'normal');
      doc.setFontSize(10);
      doc.setTextColor(51, 65, 85);
      data.improvements.forEach((imp: string) => {
        const itemText = `•  ${imp}`;
        const splitImp = doc.splitTextToSize(itemText, contentWidth - 10);
        checkPageBreak(splitImp.length * 13 + 4);
        doc.text(splitImp, margin + 5, y);
        y += (splitImp.length * 13) + 4;
      });
      y += 10;
    }

    // Bug Fixes
    if (data.bugFixes && data.bugFixes.length > 0) {
      checkPageBreak(50);
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(12);
      doc.setTextColor(245, 158, 11);
      doc.text('Bug Fixes', margin, y);
      y += 14;

      doc.setFont('helvetica', 'normal');
      doc.setFontSize(10);
      doc.setTextColor(51, 65, 85);
      data.bugFixes.forEach((bf: string) => {
        const itemText = `•  ${bf}`;
        const splitBf = doc.splitTextToSize(itemText, contentWidth - 10);
        checkPageBreak(splitBf.length * 13 + 4);
        doc.text(splitBf, margin + 5, y);
        y += (splitBf.length * 13) + 4;
      });
      y += 10;
    }

    // Breaking Changes
    if (data.breakingChanges && data.breakingChanges.length > 0) {
      checkPageBreak(50);
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(12);
      doc.setTextColor(239, 68, 68);
      doc.text('Breaking Changes', margin, y);
      y += 14;

      doc.setFont('helvetica', 'normal');
      doc.setFontSize(10);
      doc.setTextColor(51, 65, 85);
      data.breakingChanges.forEach((bc: string) => {
        const itemText = `•  ${bc}`;
        const splitBc = doc.splitTextToSize(itemText, contentWidth - 10);
        checkPageBreak(splitBc.length * 13 + 4);
        doc.text(splitBc, margin + 5, y);
        y += (splitBc.length * 13) + 4;
      });
      y += 10;
    }

    // Technical Notes
    if (data.technicalNotes) {
      checkPageBreak(50);
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(12);
      doc.setTextColor(30, 41, 59);
      doc.text('Technical Notes', margin, y);
      y += 14;

      doc.setFont('helvetica', 'normal');
      doc.setFontSize(10);
      doc.setTextColor(51, 65, 85);
      const splitTech = doc.splitTextToSize(data.technicalNotes, contentWidth);
      doc.text(splitTech, margin, y);
      y += (splitTech.length * 13) + 14;
    }

    doc.save(`${baseFilename}-${this.getTimestampSuffix()}.pdf`);
  }

  private getTimestampSuffix(): string {
    const d = new Date();
    return `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, '0')}${String(d.getDate()).padStart(2, '0')}_${String(d.getHours()).padStart(2, '0')}${String(d.getMinutes()).padStart(2, '0')}`;
  }

  private triggerDownload(blob: Blob, filename: string): void {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  }
}
