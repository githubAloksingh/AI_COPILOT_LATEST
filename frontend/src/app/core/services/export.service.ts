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
        const itemText = `â€¢  ${ac}`;
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
        const itemText = `â€¢  ${as}`;
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
        const itemText = `â€¢  ${dp}`;
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
        const itemText = `â€¢  ${ec}`;
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
  // PDF EXPORT (ALL REQUIREMENTS â€” ONE PDF)
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

    // â”€â”€ Document Header â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

    // â”€â”€ Each Requirement â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    requirements.forEach((data: any, idx: number) => {
      // Requirement divider heading
      checkPageBreak(60);

      // Colored background banner for req ID + title
      doc.setFillColor(241, 245, 249);
      doc.roundedRect(margin, y - 14, contentWidth, 26, 4, 4, 'F');

      doc.setFont('helvetica', 'bold');
      doc.setFontSize(13);
      doc.setTextColor(30, 41, 59);
      const reqLabel = data.requirementId ? `${data.requirementId}  â€”  ${data.title || ''}` : (data.title || `Requirement ${idx + 1}`);
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
          const itemText = `â€¢  ${ac}`;
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
          const itemText = `â€¢  ${as}`;
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
          const itemText = `â€¢  ${dp}`;
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
          const itemText = `â€¢  ${ec}`;
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
    doc.text(`Release Notes â€” Version ${data.version || '1.0.0'}`, margin, y);
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
        const itemText = `â€¢  ${f}`;
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
        const itemText = `â€¢  ${imp}`;
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
        const itemText = `â€¢  ${bf}`;
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
        const itemText = `â€¢  ${bc}`;
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

  // ==========================================
  // UNIFIED DOCUMENT PDF GENERATOR
  // ==========================================
  generateDocumentPdf(
    type: 'USER_STORY' | 'FUNCTIONAL_DESIGN' | 'TECHNICAL_DESIGN' | 'REQUIREMENT' | 'DEFECT' | 'RELEASE_NOTE',
    data: any,
    meta?: any
  ): void {
    if (type === 'USER_STORY') {
      this.downloadUserStoryPdf(data, meta);
    } else if (type === 'FUNCTIONAL_DESIGN') {
      this.downloadFunctionalDesignPdf(data, meta);
    } else if (type === 'TECHNICAL_DESIGN') {
      this.downloadTechnicalDesignPdf(data, meta);
    } else if (type === 'REQUIREMENT') {
      const items = Array.isArray(data) ? data : (data.requirements || [data]);
      this.downloadAllRequirementsPdf(items);
    } else if (type === 'DEFECT') {
      this.downloadDefectPdf(data);
    } else if (type === 'RELEASE_NOTE') {
      this.downloadReleaseNotePdf(data);
    }
  }

  // ============================================================
  // SHARED DOC-STYLE LAYOUT ENGINE
  // Clean Word/business document style â€” black on white, no boxes
  // ============================================================

  /** Creates a fresh doc context. Call once per PDF. */
  private newDocCtx(docType: string, docTitle: string, meta?: any) {
    const doc = new jsPDF({ unit: 'pt', format: 'a4' });
    const pageWidth  = doc.internal.pageSize.getWidth();   // 595.28
    const pageHeight = doc.internal.pageSize.getHeight();  // 841.89
    const margin = 54;                  // ~19mm â€” matches Word normal margins
    const contentWidth = pageWidth - margin * 2;
    let y = margin;

    const checkPageBreak = (need: number): void => {
      if (y + need > pageHeight - 50) {
        doc.addPage();
        y = margin;
      }
    };

    return { doc, pageWidth, pageHeight, margin, contentWidth, y, checkPageBreak,
             docType, docTitle, meta,
             setY: (v: number) => { y = v; },
             getY: () => y,
             addY: (v: number) => { y += v; } };
  }

  /** Big document title  (e.g. "Technical Design Document â€” Preferred Custody Platform") */
  private docTitle(ctx: any, title: string): void {
    const { doc, margin, contentWidth } = ctx;
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(20);
    doc.setTextColor(0, 0, 0);
    const lines = doc.splitTextToSize(title, contentWidth);
    doc.text(lines, margin, ctx.getY());
    ctx.addY(lines.length * 26 + 6);
  }

  /** Program / Work / BRD Version info line â€” bold labels, normal values inline */
  private docMetaLine(ctx: any, parts: { label: string; value: string }[]): void {
    const { doc, margin, contentWidth } = ctx;
    const filtered = parts.filter(p => p.value && p.value.trim() !== '');
    if (filtered.length === 0) return;

    // Build mixed-style text by drawing label then value sequentially
    doc.setFontSize(10);
    doc.setTextColor(0, 0, 0);

    let x = margin;
    const lineY = ctx.getY();

    filtered.forEach((part, idx) => {
      const label = part.label + ': ';
      const value = part.value + (idx < filtered.length - 1 ? '  ' : '');

      // Bold label
      doc.setFont('helvetica', 'bold');
      doc.text(label, x, lineY);
      x += doc.getTextWidth(label);

      // Normal value
      doc.setFont('helvetica', 'normal');
      doc.text(value, x, lineY);
      x += doc.getTextWidth(value);

      // Wrap to next line if needed
      if (x > margin + ctx.contentWidth - 40) {
        x = margin;
        ctx.addY(14);
      }
    });

    ctx.addY(20);
  }

  /** Horizontal rule */
  private docRule(ctx: any): void {
    const { doc, margin, contentWidth } = ctx;
    doc.setDrawColor(180, 180, 180);
    doc.setLineWidth(0.75);
    doc.line(margin, ctx.getY(), margin + contentWidth, ctx.getY());
    ctx.addY(18);
  }

  /** Top-level section heading: "1. Technical Objective" */
  private docSection(ctx: any, title: string): void {
    ctx.checkPageBreak(36);
    const { doc, margin } = ctx;
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(13);
    doc.setTextColor(0, 0, 0);
    doc.text(title, margin, ctx.getY());
    ctx.addY(20);
  }

  /** Sub-section heading: "2.1 ODR Feed Ingestion Component" */
  private docSubSection(ctx: any, title: string): void {
    ctx.checkPageBreak(28);
    const { doc, margin } = ctx;
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(11);
    doc.setTextColor(0, 0, 0);
    doc.text(title, margin, ctx.getY());
    ctx.addY(16);
  }

  /** Inline bold label + normal text on same line: "Responsibility: lorem ipsum" */
  private docInlineLabel(ctx: any, label: string, value: string): void {
    if (!value || value.trim() === '') return;
    ctx.checkPageBreak(24);
    const { doc, margin, contentWidth } = ctx;

    const boldLabel = label + ': ';
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(10);
    doc.setTextColor(0, 0, 0);
    const labelW = doc.getTextWidth(boldLabel);
    doc.text(boldLabel, margin, ctx.getY());

    doc.setFont('helvetica', 'normal');
    const avail = contentWidth - labelW;
    const lines = doc.splitTextToSize(value, avail);
    doc.text(lines[0] || '', margin + labelW, ctx.getY());
    ctx.addY(14);

    // Overflow lines
    for (let i = 1; i < lines.length; i++) {
      ctx.checkPageBreak(14);
      doc.text(lines[i], margin, ctx.getY());
      ctx.addY(14);
    }
    ctx.addY(4);
  }

  /** Bold label on its own line: "Key Logic:" */
  private docLabelLine(ctx: any, label: string): void {
    ctx.checkPageBreak(20);
    const { doc, margin } = ctx;
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(10);
    doc.setTextColor(0, 0, 0);
    doc.text(label + ':', margin, ctx.getY());
    ctx.addY(14);
  }

  /** Normal paragraph text */
  private docParagraph(ctx: any, text: string, indent = 0): void {
    if (!text || text.trim() === '') return;
    ctx.checkPageBreak(16);
    const { doc, margin, contentWidth } = ctx;
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(10);
    doc.setTextColor(30, 30, 30);
    const lines = doc.splitTextToSize(text, contentWidth - indent);
    lines.forEach((line: string) => {
      ctx.checkPageBreak(14);
      doc.text(line, margin + indent, ctx.getY());
      ctx.addY(14);
    });
    ctx.addY(4);
  }

  /**
   * Bullet list item.
   * level 0 â†’ "â€¢" bullet at margin+12
   * level 1 â†’ "â—¦" bullet at margin+28
   */
  private docBullet(ctx: any, text: string, level = 0, sourceTag = ''): void {
    if (!text || text.trim() === '') return;
    const { doc, margin, contentWidth } = ctx;

    const bulletChar = level === 0 ? '\u2022' : '\u25e6'; // â€¢ or â—¦
    const indentBase = level === 0 ? 14 : 30;
    const textIndent = indentBase + 10;

    doc.setFont('helvetica', 'normal');
    doc.setFontSize(10);
    doc.setTextColor(30, 30, 30);

    const fullText = text + (sourceTag ? `  ${sourceTag}` : '');
    const avail = contentWidth - textIndent;
    const lines = doc.splitTextToSize(fullText, avail);

    ctx.checkPageBreak(lines.length * 14 + 4);
    doc.text(bulletChar, margin + indentBase, ctx.getY());
    lines.forEach((line: string, i: number) => {
      doc.text(line, margin + textIndent, ctx.getY());
      ctx.addY(14);
    });
  }

  /** Numbered list item: "1.  text..." */
  private docNumbered(ctx: any, num: number, text: string): void {
    if (!text || text.trim() === '') return;
    const { doc, margin, contentWidth } = ctx;

    const prefix = `${num}.`;
    const textIndent = 22;

    doc.setFont('helvetica', 'normal');
    doc.setFontSize(10);
    doc.setTextColor(30, 30, 30);

    const avail = contentWidth - textIndent;
    const lines = doc.splitTextToSize(text, avail);

    ctx.checkPageBreak(lines.length * 14 + 4);
    doc.setFont('helvetica', 'bold');
    doc.text(prefix, margin, ctx.getY());
    doc.setFont('helvetica', 'normal');
    lines.forEach((line: string) => {
      doc.text(line, margin + textIndent, ctx.getY());
      ctx.addY(14);
    });
  }

  /**
   * Lightweight 2-column table â€” no colored backgrounds.
   * Header row is bold, rows alternate no-fill / very-light-gray.
   */
  private docTable(
    ctx: any,
    cols: { header: string; key: string; width: number }[],
    rows: any[]
  ): void {
    if (!rows || rows.length === 0) return;
    const { doc, margin, pageHeight } = ctx;

    const renderHeader = () => {
      let cx = margin;
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(9.5);
      doc.setTextColor(0, 0, 0);

      // Header bottom border
      const headerY = ctx.getY();
      cols.forEach(col => {
        const lines = doc.splitTextToSize(col.header, col.width - 8);
        doc.text(lines, cx + 4, headerY + 12);
        cx += col.width;
      });

      ctx.addY(22);
      doc.setDrawColor(100, 100, 100);
      doc.setLineWidth(0.75);
      doc.line(margin, ctx.getY(), margin + cols.reduce((s, c) => s + c.width, 0), ctx.getY());
      ctx.addY(4);
    };

    renderHeader();

    rows.forEach((row, rowIdx) => {
      // Measure row height
      let maxLines = 1;
      const cellLines: string[][] = cols.map(col => {
        const val = String(row[col.key] ?? '');
        const ls = doc.splitTextToSize(val, col.width - 8);
        if (ls.length > maxLines) maxLines = ls.length;
        return ls;
      });

      const rowH = Math.max(18, maxLines * 13 + 8);

      if (ctx.getY() + rowH > pageHeight - 50) {
        doc.addPage();
        ctx.setY(54);
        renderHeader();
      }

      // Very light alternate rows
      if (rowIdx % 2 === 1) {
        doc.setFillColor(246, 246, 246);
        doc.rect(margin, ctx.getY() - 2, cols.reduce((s, c) => s + c.width, 0), rowH, 'F');
      }

      doc.setFont('helvetica', 'normal');
      doc.setFontSize(9.5);
      doc.setTextColor(30, 30, 30);

      let cx = margin;
      cellLines.forEach((lines, ci) => {
        doc.text(lines, cx + 4, ctx.getY() + 12);
        cx += cols[ci].width;
      });

      // Light bottom border
      doc.setDrawColor(210, 210, 210);
      doc.setLineWidth(0.4);
      const lineY = ctx.getY() + rowH;
      doc.line(margin, lineY, margin + cols.reduce((s, c) => s + c.width, 0), lineY);

      ctx.addY(rowH);
    });

    ctx.addY(12);
  }

  /** Apply "Page X of Y" footer on all pages */
  private docApplyFooters(ctx: any): void {
    const { doc, margin, pageWidth, pageHeight, docType, docTitle } = ctx;
    const total = doc.getNumberOfPages();
    for (let i = 1; i <= total; i++) {
      doc.setPage(i);
      doc.setFont('helvetica', 'normal');
      doc.setFontSize(8);
      doc.setTextColor(120, 120, 120);

      // Left footer
      doc.text(`${docType}  |  ${docTitle}`, margin, pageHeight - 16);

      // Right footer â€” page number
      const pageStr = `Page ${i} of ${total}`;
      const pw = doc.getTextWidth(pageStr);
      doc.text(pageStr, pageWidth - margin - pw, pageHeight - 16);

      // Footer rule
      doc.setDrawColor(200, 200, 200);
      doc.setLineWidth(0.4);
      doc.line(margin, pageHeight - 26, pageWidth - margin, pageHeight - 26);
    }
  }

  // ============================================================
  // 1. USER STORY PDF  â€”  Word-document style
  // ============================================================
  downloadUserStoryPdf(items: any | any[], meta?: any): void {
    const list: any[] = Array.isArray(items) ? items : [items];
    if (!list || list.length === 0) {
      alert('No user story data available to export.');
      return;
    }

    const rawDocName = (meta?.documentName || '').trim();
    const docName = rawDocName || 'User Stories';
    const ctx = this.newDocCtx('User Stories', docName, meta);

    // Cover header
    const titleText = rawDocName && rawDocName.toLowerCase() !== 'user stories'
      ? `User Stories - ${rawDocName}`
      : 'User Stories';
    this.docTitle(ctx, titleText);

    const metaParts: { label: string; value: string }[] = [
      { label: 'Program', value: meta?.project || '' },
      { label: 'Work', value: meta?.work || '' },
      { label: 'BRD Version', value: meta?.version || '' }
    ];
    this.docMetaLine(ctx, metaParts);
    this.docRule(ctx);

    // â”€â”€ User Stories â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    list.forEach((story: any, idx: number) => {
      const storyId = story.userStoryId || story.requirementId || `US-${String(idx + 1).padStart(3, '0')}`;
      const storyTitle = story.title || `User Story ${idx + 1}`;

      // Sub-section header: "US-001  Title"
      this.docSubSection(ctx, `${storyId}  ${storyTitle}`);

      // "As aâ€¦" user story statement
      if (story.userStory) {
        this.docParagraph(ctx, story.userStory);
      }

      // Description / Summary
      const desc = story.description || story.summary;
      if (desc && desc.trim()) {
        this.docInlineLabel(ctx, 'Description', desc);
      }

      // Acceptance Criteria
      if (story.acceptanceCriteria && story.acceptanceCriteria.length > 0) {
        this.docLabelLine(ctx, 'Acceptance Criteria');
        story.acceptanceCriteria.forEach((ac: any, acIdx: number) => {
          const text = this.toText(ac);
          const defaultId = `AC-${String(acIdx + 1).padStart(3, '0')}`;
          const prefix = text.startsWith('AC-') ? '' : `${defaultId}  `;
          const srcTag = this.formatItemSource(ac);
          this.docBullet(ctx, `${prefix}${text}`, 0, srcTag);
        });
        ctx.addY(4);
      }

      // Business Rules
      if (story.businessRules && story.businessRules.length > 0) {
        this.docLabelLine(ctx, 'Business Rules');
        story.businessRules.forEach((br: any, brIdx: number) => {
          const text = this.toText(br);
          const defaultId = `BR-${String(brIdx + 1).padStart(3, '0')}`;
          const prefix = text.startsWith('BR-') ? '' : `${defaultId}  `;
          this.docBullet(ctx, `${prefix}${text}`);
        });
        ctx.addY(4);
      }

      // Dependencies
      if (story.dependencies && story.dependencies.length > 0) {
        this.docLabelLine(ctx, 'Dependencies');
        story.dependencies.forEach((d: any) => this.docBullet(ctx, this.toText(d)));
        ctx.addY(4);
      }

      // Assumptions
      if (story.assumptions && story.assumptions.length > 0) {
        this.docLabelLine(ctx, 'Assumptions');
        story.assumptions.forEach((a: any) => this.docBullet(ctx, this.toText(a)));
        ctx.addY(4);
      }

      // Edge Cases
      if (story.edgeCases && story.edgeCases.length > 0) {
        this.docLabelLine(ctx, 'Edge Cases');
        story.edgeCases.forEach((e: any) => this.docBullet(ctx, this.toText(e)));
        ctx.addY(4);
      }

      // Source / Reference
      const storySrc = story.sources || story.source;
      if (storySrc) {
        const srcArr = Array.isArray(storySrc) ? storySrc : [storySrc];
        if (srcArr.length > 0) {
          this.docLabelLine(ctx, 'Source / Reference');
          srcArr.forEach((s: any) => this.docBullet(ctx, this.toText(s)));
        }
      }

      // Separator (thin rule) between stories
      if (idx < list.length - 1) {
        ctx.addY(10);
        const { doc, margin, contentWidth } = ctx;
        doc.setDrawColor(210, 210, 210);
        doc.setLineWidth(0.4);
        doc.line(margin, ctx.getY(), margin + contentWidth, ctx.getY());
        ctx.addY(14);
      }
    });

    this.docApplyFooters(ctx);

    const firstId = list[0]?.userStoryId || list[0]?.requirementId || 'US-001';
    const filename = list.length === 1
      ? `User_Story_${this.sanitizeFilename(firstId)}.pdf`
      : `User_Stories_${this.sanitizeFilename(docName)}_${this.getTimestampSuffix()}.pdf`;
    ctx.doc.save(filename);
  }

  // ============================================================
  // 2. FUNCTIONAL DESIGN PDF  â€”  Word-document style
  // ============================================================
  downloadFunctionalDesignPdf(data: any, meta?: any): void {
    if (!data) { alert('No functional design data available to export.'); return; }

    const rawDocName = (data.title || meta?.documentName || '').trim();
    const docName = rawDocName || 'Functional Specification';
    const ctx = this.newDocCtx('Functional Design', docName, meta);

    // Cover header
    const titleText = rawDocName && rawDocName.toLowerCase() !== 'functional design document' && rawDocName.toLowerCase() !== 'functional specification'
      ? `Functional Design Document - ${rawDocName}`
      : 'Functional Design Document';
    this.docTitle(ctx, titleText);
    this.docMetaLine(ctx, [
      { label: 'Program', value: meta?.project || '' },
      { label: 'Work', value: meta?.work || meta?.inputType || '' },
      { label: 'Version', value: meta?.version || '' }
    ]);
    this.docRule(ctx);

    let sectionIdx = 1;

    // 1. Objective
    if (data.objective) {
      this.docSection(ctx, `${sectionIdx++}. Objective`);
      this.docParagraph(ctx, data.objective);
    }

    // 2. Scope
    const scopeList = Array.isArray(data.scope) ? data.scope : (data.scope ? [data.scope] : []);
    if (scopeList.length > 0) {
      this.docSection(ctx, `${sectionIdx++}. Scope`);

      this.docLabelLine(ctx, 'In Scope');
      scopeList.forEach((s: any) => this.docBullet(ctx, this.toText(s)));

      if (data.outOfScope && Array.isArray(data.outOfScope) && data.outOfScope.length > 0) {
        ctx.addY(6);
        this.docLabelLine(ctx, 'Out of Scope');
        data.outOfScope.forEach((s: any) => this.docBullet(ctx, this.toText(s)));
      }
      ctx.addY(6);
    }

    // 3. Actors
    if (data.actors && data.actors.length > 0) {
      this.docSection(ctx, `${sectionIdx++}. Actors`);
      data.actors.forEach((act: any, idx: number) => {
        const name = act.name || `Actor ${idx + 1}`;
        const desc = act.description || '';
        this.docSubSection(ctx, `${idx + 1 < 10 ? sectionIdx - 1 + '.' + idx : (idx + 1)}  ${name}`);
        if (desc) this.docParagraph(ctx, desc);
      });
    }

    // 4. Preconditions
    if (data.preconditions && data.preconditions.length > 0) {
      this.docSection(ctx, `${sectionIdx++}. Preconditions`);
      data.preconditions.forEach((p: any, i: number) => this.docNumbered(ctx, i + 1, this.toText(p)));
      ctx.addY(6);
    }

    // 5. Main Functional Flow
    if (data.mainFlow && data.mainFlow.length > 0) {
      this.docSection(ctx, `${sectionIdx++}. Main Functional Flow`);
      data.mainFlow.forEach((step: any) => {
        const sNum = step.step != null ? `Step ${step.step}` : '';
        const actor = step.actor ? `  Actor: ${step.actor}` : '';
        const label = sNum + actor;
        if (label) this.docSubSection(ctx, label);
        if (step.action) this.docInlineLabel(ctx, 'Action', step.action);
        if (step.systemResponse) this.docInlineLabel(ctx, 'System Response', step.systemResponse);
      });
    }

    // 6. Alternate Flows
    if (data.alternateFlows && data.alternateFlows.length > 0) {
      this.docSection(ctx, `${sectionIdx++}. Alternate Flows`);
      data.alternateFlows.forEach((af: any, i: number) => {
        const flowName = af.name || `Alternate Flow ${i + 1}`;
        this.docSubSection(ctx, `${sectionIdx - 1}.${i + 1}  ${flowName}`);
        if (af.steps && af.steps.length > 0) {
          af.steps.forEach((s: any, si: number) => this.docNumbered(ctx, si + 1, this.toText(s)));
        }
        ctx.addY(4);
      });
    }

    // 7. Validations
    if (data.validations && data.validations.length > 0) {
      this.docSection(ctx, `${sectionIdx++}. Validation Rules`);
      const tableRows = data.validations.map((v: any) => ({
        field: v.field || 'General',
        rule: v.rule || this.toText(v),
        grounding: v.grounding || ''
      }));
      this.docTable(ctx, [
        { header: 'Field / Target', key: 'field', width: 140 },
        { header: 'Validation Rule', key: 'rule', width: 270 },
        { header: 'Source / Grounding', key: 'grounding', width: 105 }
      ], tableRows);
    }

    // 8. Business Rules
    if (data.businessRules && data.businessRules.length > 0) {
      this.docSection(ctx, `${sectionIdx++}. Business Rules`);
      data.businessRules.forEach((br: any) => this.docBullet(ctx, this.toText(br)));
      ctx.addY(6);
    }

    // 9. Inputs
    if (data.inputs && data.inputs.length > 0) {
      this.docSection(ctx, `${sectionIdx++}. Inputs`);
      this.docTable(ctx, [
        { header: 'Input', key: 'name', width: 120 },
        { header: 'Description', key: 'description', width: 215 },
        { header: 'Required', key: 'reqText', width: 75 },
        { header: 'Format', key: 'format', width: 105 }
      ], data.inputs.map((inp: any) => ({
        name: inp.name || '',
        description: inp.description || '',
        reqText: inp.required ? 'Yes' : 'No',
        format: inp.format || 'String'
      })));
    }

    // 10. Outputs
    if (data.outputs && data.outputs.length > 0) {
      this.docSection(ctx, `${sectionIdx++}. Outputs`);
      data.outputs.forEach((o: any) => this.docBullet(ctx, this.toText(o)));
      ctx.addY(6);
    }

    // 11. Error Handling
    if (data.errorHandling && data.errorHandling.length > 0) {
      this.docSection(ctx, `${sectionIdx++}. Error Handling`);
      data.errorHandling.forEach((eh: any) => {
        const scenario = eh.scenario || '';
        const behavior = eh.expectedBehavior || eh.handling || this.toText(eh);
        if (scenario) this.docSubSection(ctx, scenario);
        this.docParagraph(ctx, behavior);
      });
    }

    // 12. Dependencies
    if (data.dependencies && data.dependencies.length > 0) {
      this.docSection(ctx, `${sectionIdx++}. Dependencies`);
      data.dependencies.forEach((d: any) => this.docBullet(ctx, this.toText(d)));
      ctx.addY(6);
    }

    // 13. Assumptions
    if (data.assumptions && data.assumptions.length > 0) {
      this.docSection(ctx, `${sectionIdx++}. Assumptions`);
      data.assumptions.forEach((a: any) => this.docBullet(ctx, this.toText(a)));
      ctx.addY(6);
    }

    // 14. Edge Cases
    if (data.edgeCases && data.edgeCases.length > 0) {
      this.docSection(ctx, `${sectionIdx++}. Edge Cases`);
      data.edgeCases.forEach((e: any) => this.docBullet(ctx, this.toText(e)));
      ctx.addY(6);
    }

    // 15. Source References
    if (data.sources) {
      const srcArr = Array.isArray(data.sources) ? data.sources : [data.sources];
      if (srcArr.length > 0) {
        this.docSection(ctx, `${sectionIdx++}. Source References`);
        srcArr.forEach((s: any) => this.docBullet(ctx, this.toText(s)));
      }
    }

    this.docApplyFooters(ctx);
    ctx.doc.save(`Functional_Design_${this.sanitizeFilename(docName)}.pdf`);
  }

  // ============================================================
  // 3. TECHNICAL DESIGN PDF  â€”  Word-document style
  // ============================================================
  downloadTechnicalDesignPdf(data: any, meta?: any): void {
    if (!data) { alert('No technical design data available to export.'); return; }

    const rawDocName = (data.title || meta?.documentName || '').trim();
    const docName = rawDocName || 'Technical Specification';
    const ctx = this.newDocCtx('Technical Design', docName, meta);

    // Cover header
    const titleText = rawDocName && rawDocName.toLowerCase() !== 'technical design document' && rawDocName.toLowerCase() !== 'technical specification'
      ? `Technical Design Document - ${rawDocName}`
      : 'Technical Design Document';
    this.docTitle(ctx, titleText);
    this.docMetaLine(ctx, [
      { label: 'Program', value: meta?.project || '' },
      { label: 'Work', value: meta?.work || meta?.inputType || '' },
      { label: 'BRD Version', value: meta?.version || '' }
    ]);
    this.docRule(ctx);

    let secIdx = 1;

    // 1. System Overview / Technical Objective
    if (data.objective) {
      this.docSection(ctx, `${secIdx++}. System Overview`);
      this.docParagraph(ctx, data.objective);
    }

    // 2. Requirement Summary
    if (data.requirementSummary) {
      this.docSection(ctx, `${secIdx++}. Requirement Summary`);
      this.docParagraph(ctx, data.requirementSummary);
    }

    // 3. Component Design  (maps to "components" array)
    if (data.components && data.components.length > 0) {
      this.docSection(ctx, `${secIdx++}. Component Design`);
      data.components.forEach((comp: any, idx: number) => {
        const name = comp.name || `Component ${idx + 1}`;
        this.docSubSection(ctx, `${secIdx - 1}.${idx + 1}  ${name}`);
        if (comp.responsibility) this.docInlineLabel(ctx, 'Responsibility', comp.responsibility);

        // Key Logic from various possible fields
        const logic: string[] = [];
        if (comp.keyLogic && Array.isArray(comp.keyLogic)) logic.push(...comp.keyLogic.map((k: any) => this.toText(k)));
        if (comp.steps && Array.isArray(comp.steps)) logic.push(...comp.steps.map((k: any) => this.toText(k)));
        if (comp.logic) logic.push(this.toText(comp.logic));
        if (comp.details) logic.push(this.toText(comp.details));
        if (comp.notes && Array.isArray(comp.notes)) logic.push(...comp.notes.map((n: any) => this.toText(n)));

        if (logic.length > 0) {
          this.docLabelLine(ctx, 'Key Logic');
          logic.forEach((line: string) => {
            // Handle nested sub-bullets that start with "â—¦" or "-"
            if (line.startsWith('-') || line.startsWith('\u25e6')) {
              this.docBullet(ctx, line.replace(/^[-\u25e6]\s*/, ''), 1);
            } else {
              this.docBullet(ctx, line, 0);
            }
          });
        }

        if (comp.rules && Array.isArray(comp.rules) && comp.rules.length > 0) {
          ctx.addY(4);
          this.docLabelLine(ctx, 'Rules');
          comp.rules.forEach((r: any) => this.docBullet(ctx, this.toText(r)));
        }

        ctx.addY(8);
      });
    }

    // 4. Architecture Flow
    if (data.architectureFlow && data.architectureFlow.length > 0) {
      this.docSection(ctx, `${secIdx++}. Architecture Flow`);
      data.architectureFlow.forEach((step: any, i: number) => {
        const sNum = step.step != null ? `Step ${step.step}` : `Step ${i + 1}`;
        const comp = step.component ? `  [${step.component}]` : '';
        this.docSubSection(ctx, `${sNum}${comp}`);
        if (step.action) this.docParagraph(ctx, step.action, 10);
      });
    }

    // 5. API Specifications
    if (data.apis && data.apis.length > 0) {
      this.docSection(ctx, `${secIdx++}. API Specifications`);
      const tableRows = data.apis.map((api: any) => {
        const statusStr = api.statusCodes
          ? (Array.isArray(api.statusCodes) ? api.statusCodes.join(', ') : api.statusCodes)
          : '';
        return {
          name: api.name || '',
          method: api.method || 'GET',
          endpoint: api.endpoint || '',
          purpose: api.purpose || '',
          statusCodes: statusStr
        };
      });
      this.docTable(ctx, [
        { header: 'API Name', key: 'name', width: 110 },
        { header: 'Method', key: 'method', width: 55 },
        { header: 'Endpoint', key: 'endpoint', width: 175 },
        { header: 'Purpose', key: 'purpose', width: 135 },
        { header: 'Status Codes', key: 'statusCodes', width: 40 }
      ], tableRows);
    }

    // 6. Data Model
    if (data.dataModel && data.dataModel.length > 0) {
      this.docSection(ctx, `${secIdx++}. Data Model`);
      data.dataModel.forEach((dm: any, idx: number) => {
        const entity = dm.entity || `Entity ${idx + 1}`;
        this.docSubSection(ctx, `${secIdx - 1}.${idx + 1}  ${entity}`);
        if (dm.fields && dm.fields.length > 0) {
          this.docTable(ctx, [
            { header: 'Field', key: 'name', width: 120 },
            { header: 'Type', key: 'type', width: 80 },
            { header: 'Required', key: 'reqText', width: 65 },
            { header: 'Description', key: 'description', width: 250 }
          ], dm.fields.map((f: any) => ({
            name: f.name || '',
            type: f.type || 'String',
            reqText: f.required ? 'Yes' : 'No',
            description: f.description || ''
          })));
        }
        if (dm.relationships && dm.relationships.length > 0) {
          const relStr = Array.isArray(dm.relationships) ? dm.relationships.join(', ') : dm.relationships;
          this.docInlineLabel(ctx, 'Relationships', relStr);
        }
      });
    }

    // 7. Business Logic
    if (data.businessLogic && data.businessLogic.length > 0) {
      this.docSection(ctx, `${secIdx++}. Business Logic`);
      data.businessLogic.forEach((bl: any) => {
        const text = bl.rule || this.toText(bl);
        this.docBullet(ctx, text);
      });
      ctx.addY(6);
    }

    // 8. Validation
    if (data.validation && data.validation.length > 0) {
      this.docSection(ctx, `${secIdx++}. Validation`);
      data.validation.forEach((v: any) => this.docBullet(ctx, this.toText(v)));
      ctx.addY(6);
    }

    // 9. Error Handling
    if (data.errorHandling && data.errorHandling.length > 0) {
      this.docSection(ctx, `${secIdx++}. Error Handling`);
      data.errorHandling.forEach((eh: any) => {
        const scenario = eh.scenario || '';
        const handling = eh.handling || eh.expectedBehavior || this.toText(eh);
        if (scenario) this.docSubSection(ctx, scenario);
        this.docParagraph(ctx, handling, 10);
      });
    }

    // 10. Security
    if (data.security && data.security.length > 0) {
      this.docSection(ctx, `${secIdx++}. Security Considerations`);
      data.security.forEach((s: any) => {
        const text = s.consideration || this.toText(s);
        this.docBullet(ctx, text);
      });
      ctx.addY(6);
    }

    // 11. Database Changes
    if (data.databaseChanges && data.databaseChanges.length > 0) {
      this.docSection(ctx, `${secIdx++}. Database Changes`);
      this.docTable(ctx, [
        { header: 'Entity / Table', key: 'entity', width: 150 },
        { header: 'Change Description', key: 'change', width: 365 }
      ], data.databaseChanges.map((dbc: any) => ({
        entity: dbc.entity || dbc.table || 'Schema',
        change: dbc.change || this.toText(dbc)
      })));
    }

    // 12. Integrations
    if (data.integrations && data.integrations.length > 0) {
      this.docSection(ctx, `${secIdx++}. Integrations`);
      this.docTable(ctx, [
        { header: 'External System', key: 'system', width: 150 },
        { header: 'Purpose & Protocol', key: 'purpose', width: 365 }
      ], data.integrations.map((int: any) => ({
        system: int.system || 'External Service',
        purpose: int.purpose || this.toText(int)
      })));
    }

    // 13. Performance Considerations
    if (data.performanceConsiderations && data.performanceConsiderations.length > 0) {
      this.docSection(ctx, `${secIdx++}. Performance Considerations`);
      data.performanceConsiderations.forEach((pc: any) => {
        this.docBullet(ctx, pc.consideration || this.toText(pc));
      });
      ctx.addY(6);
    }

    // 14. Dependencies
    if (data.dependencies && data.dependencies.length > 0) {
      this.docSection(ctx, `${secIdx++}. Dependencies`);
      data.dependencies.forEach((d: any) => this.docBullet(ctx, this.toText(d)));
      ctx.addY(6);
    }

    // 15. Assumptions
    if (data.assumptions && data.assumptions.length > 0) {
      this.docSection(ctx, `${secIdx++}. Assumptions`);
      data.assumptions.forEach((a: any) => this.docBullet(ctx, this.toText(a)));
      ctx.addY(6);
    }

    // 16. Implementation Notes
    if (data.implementationNotes && data.implementationNotes.length > 0) {
      this.docSection(ctx, `${secIdx++}. Implementation Notes`);
      data.implementationNotes.forEach((n: any) => this.docBullet(ctx, n.note || this.toText(n)));
      ctx.addY(6);
    }

    // 17. Source References
    if (data.sources) {
      const srcArr = Array.isArray(data.sources) ? data.sources : [data.sources];
      if (srcArr.length > 0) {
        this.docSection(ctx, `${secIdx++}. Source References`);
        srcArr.forEach((s: any) => this.docBullet(ctx, this.toText(s)));
      }
    }

    this.docApplyFooters(ctx);
    ctx.doc.save(`Technical_Design_${this.sanitizeFilename(docName)}.pdf`);
  }

  // ============================================================
  // PRIVATE UTILITIES
  // ============================================================

  private sanitizeFilename(name: string): string {
    if (!name) return 'document';
    return name.replace(/[^a-zA-Z0-9_\-]/g, '_').substring(0, 50);
  }

  private toText(item: any): string {
    if (!item) return '';
    if (typeof item === 'string') return item;
    if (typeof item === 'number' || typeof item === 'boolean') return String(item);
    return item.text || item.scenario || item.rule || item.description || item.name ||
           item.handling || item.change || item.purpose || item.note ||
           item.consideration || item.dependency || JSON.stringify(item);
  }

  private formatItemSource(item: any): string {
    if (!item || typeof item === 'string') return '';
    const parts: string[] = [];
    if (item.grounding && item.grounding !== 'EXPLICIT') {
      parts.push(`Grounding: ${item.grounding}`);
    }
    if (item.source) {
      const srcList = Array.isArray(item.source) ? item.source : [item.source];
      if (srcList.length > 0) parts.push(`Source: ${srcList.join(', ')}`);
    }
    return parts.length > 0 ? `[${parts.join(' | ')}]` : '';
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

