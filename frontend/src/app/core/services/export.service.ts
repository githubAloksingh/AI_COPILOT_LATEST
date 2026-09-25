import { Injectable } from '@angular/core';
import { jsPDF } from 'jspdf';
import * as XLSX from 'xlsx-js-style';

@Injectable({
  providedIn: 'root'
})
export class ExportService {

  private newgenLogo: HTMLImageElement | null = null;

  constructor() {
    if (typeof Image !== 'undefined') {
      const logo = new Image();
      logo.onload = () => {
        this.newgenLogo = logo;
      };
      logo.src = 'logo.png';
    }
  }

  // ==========================================
  // EXCEL EXPORT (TEST CASES - .xlsx)
  // ==========================================
  buildTestCaseWorkbook(items: any[]): XLSX.WorkBook {
    if (!items || items.length === 0) {
      throw new Error('No test case data available to export.');
    }

    const headers = ['Test Case ID', 'Scenario / Title', 'Preconditions', 'Test Steps', 'Expected Result'];
    const rows = items.map((item, index) => [
      this.firstValue(item, ['tcId', 'testCaseId'], `TC-${String(index + 1).padStart(3, '0')}`),
      this.excelText(item?.scenario ?? item?.title),
      this.excelText(item?.preconditions),
      this.excelNumberedText(item?.steps),
      this.excelText(item?.expectedResult ?? item?.expectedBehavior)
    ]);

    const ws = this.createWorksheet(headers, rows, [16, 42, 34, 52, 42]);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Test Cases');
    XLSX.utils.book_append_sheet(wb, this.createSummarySheet('Test Case Export', rows.length, headers), 'Summary');
    return wb;
  }

  downloadTestCaseExcel(items: any[], baseFilename = 'test-cases'): void {
    if (!items || items.length === 0) {
      alert('No test case data available to export.');
      return;
    }

    const wb = this.buildTestCaseWorkbook(items);
    XLSX.writeFile(wb, `${baseFilename}-${this.getTimestampSuffix()}.xlsx`);
  }

  buildDefectWorkbook(data: any): XLSX.WorkBook {
    const defects = Array.isArray(data?.defects)
      ? data.defects
      : (data ? [data] : []);

    if (defects.length === 0) {
      throw new Error('No defect triage data available to export.');
    }

    const headers = [
      'Defect ID', 'Title', 'Component',
      'Location', 'Trigger', 'Root Cause', 'Impact', 'Evidence',
      'Investigation', 'Suggested Fix'
    ];
    const rows = defects.map((defect: any, index: number) => [
      this.firstValue(defect, ['defectId', 'id'], `DEF-${String(index + 1).padStart(3, '0')}`),
      this.excelText(defect?.title),
      this.excelText(defect?.component),
      this.excelText(defect?.location),
      this.excelText(defect?.trigger),
      this.excelText(defect?.rootCause ?? defect?.probableRootCause),
      this.excelText(defect?.impact),
      this.excelText(defect?.evidence),
      this.excelText(defect?.investigation ?? defect?.suggestedInvestigation),
      this.excelText(defect?.fix ?? defect?.suggestedFix)
    ]);

    const ws = this.createWorksheet(headers, rows, [16, 36, 22, 22, 28, 48, 36, 48, 48, 48]);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Defect Triage');
    XLSX.utils.book_append_sheet(wb, this.createSummarySheet('Defect Triage Export', rows.length, headers), 'Summary');
    return wb;
  }

  downloadDefectExcel(data: any, baseFilename = 'defect-triage'): void {
    const defects = Array.isArray(data?.defects)
      ? data.defects
      : (data ? [data] : []);

    if (defects.length === 0) {
      alert('No defect triage data available to export.');
      return;
    }

    const wb = this.buildDefectWorkbook(data);
    XLSX.writeFile(wb, `${baseFilename}-${this.getTimestampSuffix()}.xlsx`);
  }

  private createWorksheet(headers: string[], rows: any[][], widths: number[]): XLSX.WorkSheet {
    const ws = XLSX.utils.aoa_to_sheet([headers, ...rows]);
    ws['!cols'] = widths.map(wch => ({ wch }));
    ws['!rows'] = [
      { hpt: 30 },
      ...rows.map((row, rowIndex) => ({ hpt: this.getExcelRowHeight(row, widths, rowIndex) }))
    ];
    this.applyExcelWrapping(ws, headers.length, rows.length);
    ws['!autofilter'] = { ref: XLSX.utils.encode_range({
      s: { r: 0, c: 0 },
      e: { r: rows.length, c: headers.length - 1 }
    }) };
    return ws;
  }

  private applyExcelWrapping(ws: XLSX.WorkSheet, columnCount: number, rowCount: number): void {
    for (let rowIndex = 0; rowIndex <= rowCount; rowIndex++) {
      for (let columnIndex = 0; columnIndex < columnCount; columnIndex++) {
        const address = XLSX.utils.encode_cell({ r: rowIndex, c: columnIndex });
        const cell = ws[address];
        if (cell) {
          cell.s = {
            alignment: {
              horizontal: rowIndex === 0 ? 'center' : 'left',
              vertical: 'top',
              wrapText: true
            },
            font: rowIndex === 0 ? { bold: true } : undefined
          };
        }
      }
    }
  }

  private getExcelRowHeight(row: any[], widths: number[], rowIndex: number): number {
    const lineCount = row.reduce((maxLines, value, columnIndex) => {
      const text = value === null || value === undefined ? '' : String(value);
      const width = Math.max(8, widths[columnIndex] || 16);
      const wrappedLines = text.split('\n').reduce((total, line) => {
        return total + Math.max(1, Math.ceil(line.length / width));
      }, 0);
      return Math.max(maxLines, wrappedLines);
    }, 1);

    return Math.min(360, Math.max(rowIndex === 0 ? 30 : 30, lineCount * 15 + 6));
  }

  private createSummarySheet(title: string, rowCount: number, headers: string[]): XLSX.WorkSheet {
    const ws = XLSX.utils.aoa_to_sheet([
      [title],
      ['Generated', new Date()],
      ['Records', rowCount],
      [],
      ['Exported columns'],
      ...headers.map(header => [header])
    ]);
    ws['!cols'] = [{ wch: 26 }, { wch: 28 }];
    ws['!rows'] = [{ hpt: 28 }];
    return ws;
  }

  private firstValue(item: any, keys: string[], fallback: string): string {
    for (const key of keys) {
      if (item?.[key] !== null && item?.[key] !== undefined && String(item[key]).trim()) {
        return String(item[key]);
      }
    }
    return fallback;
  }

  private excelText(value: any, fallback = ''): string {
    if (value === null || value === undefined || value === '') return fallback;
    if (Array.isArray(value)) return value.map(item => this.excelText(item)).filter(Boolean).join('\n');
    if (typeof value === 'object') return JSON.stringify(value);
    const text = String(value);
    return this.normalizeExcelNumberedList(text);
  }

  private normalizeExcelNumberedList(text: string): string {
    if (!text) return text;
    return text.replace(/(?<=\S)\s+(?=\d+\.\s)/g, '\n');
  }

  private excelNumberedText(value: any): string {
    const text = this.excelText(value);
    if (!Array.isArray(value)) return text;
    return value.map((item, index) => `${index + 1}. ${this.excelText(item)}`).join('\n');
  }

  generateDefectCsvString(data: any): string {
    const defects = Array.isArray(data?.defects) ? data.defects : (data ? [data] : []);
    if (defects.length === 0) {
      return '';
    }

    const headers = ['Defect ID', 'Title', 'Component', 'Location', 'Trigger', 'Root Cause', 'Impact', 'Evidence', 'Investigation', 'Suggested Fix'];
    const value = (defect: any, field: string, fallback = ''): string => String(defect[field] ?? fallback);
    const rows = defects.map((defect: any, index: number) => [
      value(defect, 'defectId', `DEF-${String(index + 1).padStart(3, '0')}`),
      value(defect, 'title'), value(defect, 'component'), value(defect, 'location'), value(defect, 'trigger'),
      value(defect, 'rootCause', defect.probableRootCause), value(defect, 'impact'), value(defect, 'evidence'),
      value(defect, 'investigation', defect.suggestedInvestigation), value(defect, 'fix', defect.suggestedFix)
    ]);
    const escape = (cell: string) => `"${cell.replace(/"/g, '""')}"`;
    return ['\uFEFF' + headers.map(escape).join(','), ...rows.map((row: any[]) => row.map(escape).join(','))].join('\r\n');
  }

  downloadDefectCsv(data: any, baseFilename = 'defect-triage'): void {
    const csv = this.generateDefectCsvString(data);
    if (!csv) {
      alert('No defect triage data available to export.');
      return;
    }
    this.triggerDownload(new Blob([csv], { type: 'text/csv;charset=utf-8;' }), `${baseFilename}-${this.getTimestampSuffix()}.csv`);
  }

  // ==========================================
  // CSV EXPORT (TEST CASES ONLY)
  // RFC 4180 Compliant
  // ==========================================
  generateTestCaseCsvString(items: any[]): string {
    if (!items || items.length === 0) {
      return '';
    }

    const headers = [
      'Test Case ID',
      'Scenario / Title',
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
      const escaped = str.replace(/"/g, '""');
      return `"${escaped}"`;
    };

    const rows: string[] = [];
    rows.push(headers.map(h => escapeCsvCell(h)).join(','));

    items.forEach((item, index) => {
      const tcId = item.tcId || `TC-${String(index + 1).padStart(3, '0')}`;
      const scenario = item.scenario || '';
      const preconditions = item.preconditions ? (Array.isArray(item.preconditions) ? item.preconditions.join('\n') : item.preconditions) : '';
      const steps = item.steps ? (Array.isArray(item.steps) ? item.steps.map((s: string, i: number) => `${i + 1}. ${s}`).join('\n') : item.steps) : '';
      const expectedResult = item.expectedResult || '';

      const row = [
        escapeCsvCell(tcId),
        escapeCsvCell(scenario),
        escapeCsvCell(preconditions),
        escapeCsvCell(steps),
        escapeCsvCell(expectedResult)
      ];
      rows.push(row.join(','));
    });

    return '\uFEFF' + rows.join('\r\n');
  }

  downloadTestCaseCsv(items: any[], baseFilename = 'test-cases'): void {
    const csvContent = this.generateTestCaseCsvString(items);
    if (!csvContent) {
      alert('No test case data available to export.');
      return;
    }

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    this.triggerDownload(blob, `${baseFilename}-${this.getTimestampSuffix()}.csv`);
  }

  // ============================================================
  // MASTER DOC-STYLE LAYOUT ENGINE (SPECIFICATION COMPLIANT)
  // Specs: A4, 20mm margins, Helvetica, Bold hierarchy,
  // Aligned Metadata, Clean Tables, Flowcharts, Header/Footer
  // ============================================================

  /** Strips raw markdown syntax (#, **, *, ``, ---, etc.) and emojis (Specs 47 & 48) */
  cleanMarkdown(text: any): string {
    if (text === null || text === undefined) return '';
    let str = String(text);
    // Strip markdown headings
    str = str.replace(/^#{1,6}\s+/gm, '');
    // Strip bold and italic formatting
    str = str.replace(/\*\*([^*]+)\*\*/g, '$1');
    str = str.replace(/\*([^*]+)\*/g, '$1');
    str = str.replace(/__([^_]+)__/g, '$1');
    str = str.replace(/_([^_]+)_/g, '$1');
    // Strip inline backticks
    str = str.replace(/`([^`]+)`/g, '$1');
    // Strip horizontal rules
    str = str.replace(/^[-*_]{3,}\s*$/gm, '');
    // Replace smart quotes and special typographical symbols with ASCII equivalents
    str = str.replace(/[\u201C\u201D]/g, '"');
    str = str.replace(/[\u2018\u2019]/g, "'");
    str = str.replace(/[\u2013\u2014]/g, '-');
    str = str.replace(/[\u2192\u21D2\u21B3]/g, '->');
    str = str.replace(/\u2026/g, '...');
    // Strip emojis
    str = str.replace(/[\u{1F300}-\u{1F9FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}\u{1F600}-\u{1F64F}\u{1F680}-\u{1F6FF}]/gu, '');
    return str.trim();
  }

  /** Creates a fresh document context strictly respecting A4 size, 20mm margins, and available content width (Specs 1–3) */
  private newDocCtx(docType: string, docTitle: string, meta?: any, orientation: 'portrait' | 'landscape' = 'portrait') {
    const doc = new jsPDF({ unit: 'pt', format: 'a4', orientation });
    const pageWidth = doc.internal.pageSize.getWidth();   // 595.28 (portrait) or 841.89 (landscape)
    const pageHeight = doc.internal.pageSize.getHeight(); // 841.89 (portrait) or 595.28 (landscape)
    const margin = 56.7;                                  // Exactly 20 mm (visual equality left/right/top/bottom)
    const contentWidth = pageWidth - (margin * 2);        // 481.88 pt (portrait)
    let y = margin;

    const checkPageBreak = (need: number): void => {
      if (y + need > pageHeight - margin - 35) {
        doc.addPage(orientation);
        y = margin + 8; // Compact top spacing to use page space efficiently
      }
    };

    return {
      doc, pageWidth, pageHeight, margin, contentWidth, y, checkPageBreak,
      docType, docTitle, meta, orientation,
      setY: (v: number) => { y = v; },
      getY: () => y,
      addY: (v: number) => { y += v; }
    };
  }

  /** Standardized Document Title (22 pt Bold, clean and distinct, Specs 4, 5, 6) */
  private docTitle(ctx: any, title: string, centered = false): void {
    const { doc, margin, contentWidth } = ctx;
    const cleanT = this.cleanMarkdown(title).toUpperCase();
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(21);
    doc.setTextColor(15, 23, 42); // Deep slate
    const lines = doc.splitTextToSize(cleanT, contentWidth);
    doc.text(lines, centered ? ctx.pageWidth / 2 : margin, ctx.getY() + 18,
      centered ? { align: 'center' } : undefined);
    ctx.addY(lines.length * 26 + 8);
  }

  private docArtifactHeading(ctx: any): void {
    const { doc, contentWidth } = ctx;
    const projectName = String(ctx.meta?.project || 'Project').trim();
    const brdName = String(ctx.meta?.documentName || ctx.meta?.brd || 'BRD').trim();
    const typeName = String(ctx.docType || '').replace(/^\(|\)$/g, '').trim();
    const heading = this.cleanMarkdown(`${projectName} : ${brdName} : ${typeName}`);
    const headingLines = doc.splitTextToSize(heading, contentWidth);

    doc.setTextColor(15, 23, 42);
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(17);
    doc.text(headingLines, ctx.pageWidth / 2, ctx.getY() + 18, { align: 'center' });
    ctx.addY(headingLines.length * 21 + 28);
  }

  /** Aligned Structured Document Metadata Block (Spec 7: Project Name, Source Document, Version, Generated On) */
  private docMetaBlock(ctx: any, parts: { label: string; value: string }[]): void {
    const { doc, margin, contentWidth } = ctx;
    const filtered = parts.filter(p => p.value && String(p.value).trim() !== '');
    if (filtered.length === 0) return;

    ctx.checkPageBreak(filtered.length * 16 + 20);

    const startY = ctx.getY();
    const rowH = 15;
    const totalH = (filtered.length * rowH) + 12;

    // Subtle background card with border
    doc.setFillColor(248, 250, 252); // #f8fafc
    doc.setDrawColor(226, 232, 240); // #e2e8f0
    doc.setLineWidth(0.75);
    doc.roundedRect(margin, startY, contentWidth, totalH, 4, 4, 'FD');

    let curY = startY + 13;
    const labelWidth = 120;

    filtered.forEach(part => {
      const cleanVal = this.cleanMarkdown(part.value);
      // Label
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(9.5);
      doc.setTextColor(71, 85, 105);
      doc.text(part.label, margin + 12, curY);

      // Colon
      doc.text(':', margin + labelWidth - 10, curY);

      // Value
      doc.setFont('helvetica', 'normal');
      doc.setFontSize(9.5);
      doc.setTextColor(15, 23, 42);
      const valLines = doc.splitTextToSize(cleanVal, contentWidth - labelWidth - 20);
      doc.text(valLines[0] || '', margin + labelWidth, curY);
      curY += rowH;
    });

    ctx.setY(startY + totalH + 16);
  }

  /** Backward-compatible alias for docMetaBlock */
  private docMetaLine(ctx: any, parts: { label: string; value: string }[]): void {
    this.docMetaBlock(ctx, parts);
  }

  /** Subtle divider rule across content width (Spec 2 & 10) */
  private docRule(ctx: any): void {
    const { doc, margin, contentWidth } = ctx;
    doc.setDrawColor(226, 232, 240);
    doc.setLineWidth(0.75);
    doc.line(margin, ctx.getY(), margin + contentWidth, ctx.getY());
    ctx.addY(16);
  }

  /** Main Section Heading (16 pt Bold, Specs 4, 5, 8, 9, with orphan prevention Specs 43 & 44) */
  private docSection(ctx: any, title: string): void {
    ctx.checkPageBreak(48); // Keep headings tight with their content while preserving readability
    const { doc, margin, contentWidth } = ctx;
    const cleanT = this.cleanMarkdown(title);
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(15.5);
    doc.setTextColor(15, 23, 42);
    const lines = doc.splitTextToSize(cleanT, contentWidth);
    doc.text(lines, margin, ctx.getY() + 14);
    ctx.addY(lines.length * 18 + 8);
  }

  /** Subsection Heading (13 pt Bold, Specs 4, 5, 8, 9) */
  private docSubSection(ctx: any, title: string): void {
    ctx.checkPageBreak(36);
    const { doc, margin, contentWidth } = ctx;
    const cleanT = this.cleanMarkdown(title);
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(12.5);
    doc.setTextColor(30, 41, 59);
    const lines = doc.splitTextToSize(cleanT, contentWidth);
    doc.text(lines, margin, ctx.getY() + 11);
    ctx.addY(lines.length * 15 + 6);
  }

  /** Sub-subsection Heading (11.5 pt Semi-bold) */
  private docSubSubSection(ctx: any, title: string): void {
    ctx.checkPageBreak(30);
    const { doc, margin, contentWidth } = ctx;
    const cleanT = this.cleanMarkdown(title);
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(11.5);
    doc.setTextColor(51, 65, 85);
    const lines = doc.splitTextToSize(cleanT, contentWidth);
    doc.text(lines, margin, ctx.getY() + 9);
    ctx.addY(lines.length * 13 + 5);
  }

  /** Regular Paragraph with consistent 1.25 line height and boundary wrapping (Specs 11 & 45) */
  private docParagraph(ctx: any, text: string, indent = 0): void {
    if (!text || String(text).trim() === '') return;
    const { doc, margin, contentWidth } = ctx;
    const cleanT = this.cleanMarkdown(text);
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(9.8);
    doc.setTextColor(30, 41, 59);

    const avail = contentWidth - indent;
    const lines = doc.splitTextToSize(cleanT, avail);
    lines.forEach((line: string) => {
      ctx.checkPageBreak(15);
      doc.text(line, margin + indent, ctx.getY() + 9);
      ctx.addY(13.5);
    });
    ctx.addY(5);
  }

  /** Bullet Item with strict hanging indent and vector glyphs (ZERO character encoding bugs) */
  private docBullet(ctx: any, text: string, level = 0, sourceTag = ''): void {
    if (!text || String(text).trim() === '') return;
    const { doc, margin, contentWidth } = ctx;

    const bulletIndent = level === 0 ? 8 : 20;
    const textIndent = level === 0 ? 20 : 32;

    const rawT = this.cleanMarkdown(text);
    // Strip any leading bullet symbols from the text itself so they never duplicate
    const cleanT = rawT.replace(/^[-•*◦\u25e6\u2022\u25aa\u25ab>]+\s*/, '') + (sourceTag ? `  [${this.cleanMarkdown(sourceTag)}]` : '');
    const avail = contentWidth - textIndent;

    doc.setFont('helvetica', 'normal');
    doc.setFontSize(10);
    doc.setTextColor(30, 41, 59);

    const lines = doc.splitTextToSize(cleanT, avail);
    ctx.checkPageBreak(lines.length * 13.5 + 4);

    // Vector drawing: Level 0 = crisp filled circle; Level 1 = crisp open ring (ZERO %af glyph corruption)
    if (level === 0) {
      doc.setFillColor(30, 41, 59);
      doc.circle(margin + bulletIndent, ctx.getY() + 5.5, 1.8, 'F');
    } else {
      doc.setDrawColor(71, 85, 105);
      doc.setLineWidth(0.8);
      doc.circle(margin + bulletIndent, ctx.getY() + 5.5, 1.4, 'S');
    }

    // Draw wrapped text lines with aligned continuation
    doc.setFont('helvetica', 'normal');
    lines.forEach((line: string) => {
      doc.text(line, margin + textIndent, ctx.getY() + 9);
      ctx.addY(13.5);
    });
    ctx.addY(3);
  }

  /** Numbered List Item with strict hanging indent (Spec 13: continuation lines align with text) */
  private docNumbered(ctx: any, num: number | string, text: string): void {
    if (!text || String(text).trim() === '') return;
    const { doc, margin, contentWidth } = ctx;

    const prefix = `${num}.`;
    const numIndent = 4;
    const textIndent = 22;

    const cleanT = this.cleanMarkdown(text);
    const avail = contentWidth - textIndent;

    doc.setFont('helvetica', 'normal');
    doc.setFontSize(10);
    doc.setTextColor(30, 41, 59);

    const lines = doc.splitTextToSize(cleanT, avail);
    ctx.checkPageBreak(lines.length * 13.5 + 4);

    // Draw number prefix
    doc.setFont('helvetica', 'bold');
    doc.text(prefix, margin + numIndent, ctx.getY() + 9);

    // Draw wrapped text lines with aligned continuation
    doc.setFont('helvetica', 'normal');
    lines.forEach((line: string) => {
      doc.text(line, margin + textIndent, ctx.getY() + 9);
      ctx.addY(13.5);
    });
    ctx.addY(3);
  }

  /** Inline bold label + value: "Severity: High" (Spec 5) */
  private docInlineLabel(ctx: any, label: string, value: string): void {
    if (!value || String(value).trim() === '') return;
    ctx.checkPageBreak(18);
    const { doc, margin, contentWidth } = ctx;

    const cleanVal = this.cleanMarkdown(value);
    const boldLabel = label + ': ';
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(10);
    doc.setTextColor(15, 23, 42);
    const labelW = doc.getTextWidth(boldLabel);
    doc.text(boldLabel, margin, ctx.getY() + 9);

    doc.setFont('helvetica', 'normal');
    doc.setTextColor(51, 65, 85);
    const avail = contentWidth - labelW;
    const lines = doc.splitTextToSize(cleanVal, avail);
    doc.text(lines[0] || '', margin + labelW, ctx.getY() + 9);
    ctx.addY(13.5);

    for (let i = 1; i < lines.length; i++) {
      ctx.checkPageBreak(14);
      doc.text(lines[i], margin + 14, ctx.getY() + 9);
      ctx.addY(13.5);
    }
    ctx.addY(3);
  }

  /** Bold label on its own line: "Acceptance Criteria:" (Spec 5) */
  private docLabelLine(ctx: any, label: string): void {
    ctx.checkPageBreak(22);
    const { doc, margin } = ctx;
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(10.5);
    doc.setTextColor(15, 23, 42);
    doc.text(label + ':', margin, ctx.getY() + 9);
    ctx.addY(14);
  }

  /** Monospace code block in shaded container (Spec 33) */
  private docCodeBlock(ctx: any, code: string, label?: string): void {
    if (!code || String(code).trim() === '') return;
    const { doc, margin, contentWidth } = ctx;
    if (label) this.docLabelLine(ctx, label);

    const cleanC = String(code).trim();
    doc.setFont('courier', 'normal');
    doc.setFontSize(8.5);
    const lines = doc.splitTextToSize(cleanC, contentWidth - 18);
    const blockH = lines.length * 11 + 12;

    ctx.checkPageBreak(Math.min(blockH, 120));

    doc.setFillColor(248, 250, 252);
    doc.setDrawColor(226, 232, 240);
    doc.roundedRect(margin, ctx.getY(), contentWidth, blockH, 3, 3, 'FD');

    doc.setTextColor(30, 41, 59);
    let lineY = ctx.getY() + 10;
    lines.forEach((line: string) => {
      if (lineY > ctx.pageHeight - ctx.margin - 35) {
        ctx.doc.addPage(ctx.orientation);
        ctx.setY(ctx.margin + 8);
        lineY = ctx.getY() + 10;
      }
      doc.text(line, margin + 9, lineY);
      lineY += 11;
    });

    ctx.setY(lineY + 6);
  }

  /** Professional Flowchart / Visual Architecture Diagram (Specs 28–32) */
  private docFlowchart(ctx: any, title: string, steps: { label: string; desc?: string; component?: string }[]): void {
    if (!steps || steps.length === 0) return;
    const { doc, margin, contentWidth, pageHeight } = ctx;

    const boxW = Math.min(340, contentWidth - 30);
    const boxX = margin + (contentWidth - boxW) / 2;
    const arrowH = 18;

    // Measure the complete diagram before drawing so it can stay on one page.
    const boxHeights: number[] = steps.map(s => {
      doc.setFont('helvetica', 'normal');
      doc.setFontSize(9);
      const descLines = s.desc ? doc.splitTextToSize(this.cleanMarkdown(s.desc), boxW - 18) : [];
      return Math.max(34, 18 + (descLines.length * 11) + 12);
    });
    const baseHeight = 28 + boxHeights.reduce((sum, height) => sum + height, 0) + ((steps.length - 1) * arrowH) + 14;
    const bottomY = pageHeight - margin - 35;
    let startY = ctx.getY();

    // Keep the diagram with the section whenever it can fit on the current page,
    // but avoid forcing a blank page for modest spacing overhead.
    if (startY + baseHeight > bottomY - 18) {
      doc.addPage(ctx.orientation);
      ctx.setY(margin + 8);
      startY = ctx.getY();
    }

    const availableHeight = bottomY - startY;
    const scale = Math.min(1, availableHeight / baseHeight);
    const scaledBoxW = boxW * scale;
    const scaledBoxX = margin + (contentWidth - scaledBoxW) / 2;
    const scaledArrowH = arrowH * scale;
    const scaledBoxHeights = boxHeights.map(height => height * scale);
    const diagramHeight = baseHeight * scale;

    doc.setFillColor(248, 250, 252);
    doc.setDrawColor(203, 213, 225);
    doc.setLineWidth(0.75);
    doc.roundedRect(margin, startY, contentWidth, diagramHeight, 6, 6, 'FD');

    doc.setFont('helvetica', 'bold');
    doc.setFontSize(Math.max(7, 11 * scale));
    doc.setTextColor(15, 23, 42);
    doc.text(this.cleanMarkdown(title), margin + (14 * scale), startY + (16 * scale));

    let curY = startY + (28 * scale);
    steps.forEach((step, index) => {
      const bH = scaledBoxHeights[index];
      const innerPad = Math.max(3, 9 * scale);

      doc.setFillColor(255, 255, 255);
      doc.setDrawColor(2, 132, 199);
      doc.setLineWidth(Math.max(0.5, scale));
      doc.roundedRect(scaledBoxX, curY, scaledBoxW, bH, 4 * scale, 4 * scale, 'FD');

      const compLabel = step.component ? `[${this.cleanMarkdown(step.component)}] ` : '';
      const stepTitle = `${compLabel}${this.cleanMarkdown(step.label)}`;
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(Math.max(5.5, 9.5 * scale));
      doc.setTextColor(2, 132, 199);
      doc.text(stepTitle, scaledBoxX + innerPad, curY + (13 * scale));

      if (step.desc) {
        doc.setFont('helvetica', 'normal');
        doc.setFontSize(Math.max(5, 8.5 * scale));
        doc.setTextColor(51, 65, 85);
        const dLines = doc.splitTextToSize(this.cleanMarkdown(step.desc), scaledBoxW - (18 * scale));
        dLines.forEach((line: string, lineIndex: number) => {
          doc.text(line, scaledBoxX + innerPad, curY + (25 * scale) + (lineIndex * 11 * scale));
        });
      }

      curY += bH;
      if (index < steps.length - 1) {
        const arrowCenterX = scaledBoxX + (scaledBoxW / 2);
        const arrowEndY = curY + scaledArrowH;
        doc.setDrawColor(100, 116, 139);
        doc.setLineWidth(Math.max(0.5, 1.2 * scale));
        doc.line(arrowCenterX, curY, arrowCenterX, arrowEndY);
        doc.setFillColor(100, 116, 139);
        doc.triangle(arrowCenterX, arrowEndY, arrowCenterX - (3.5 * scale), arrowEndY - (5 * scale), arrowCenterX + (3.5 * scale), arrowEndY - (5 * scale), 'FD');
        curY += scaledArrowH;
      }
    });

    ctx.setY(startY + diagramHeight + 16);
  }

  /** Master Table Engine (Specs 14–23: auto-width normalization, cell padding, top alignment, repeated headers, row break protection) */
  private docTable(
    ctx: any,
    cols: { header: string; key: string; width: number; align?: 'left' | 'center' | 'right' }[],
    rows: any[]
  ): void {
    rows = (rows || []).filter(row =>
      row && Object.values(row).some(value => value !== null && value !== undefined && String(value).trim() !== '')
    );
    if (rows.length === 0) return;
    const { doc, margin, contentWidth, pageHeight } = ctx;

    const rawTotalW = cols.reduce((sum, c) => sum + c.width, 0);
    const scaledCols = cols.map(c => ({
      ...c,
      width: (c.width / rawTotalW) * contentWidth,
      align: c.align || (['sno', 'id', 'tcid', 'defectid', 'status', 'priority', 'type', 'version', 'step', 'stepstr'].includes(c.key.toLowerCase()) ? 'center' : 'left')
    }));

    const padX = 7;
    const padY = 6;
    const headerH = 22;
    const rowBreakBuffer = 16;

    const renderHeader = () => {
      const hy = ctx.getY();
      let cx = margin;

      doc.setFillColor(241, 245, 249);
      doc.rect(margin, hy, contentWidth, headerH, 'F');
      doc.setDrawColor(203, 213, 225);
      doc.setLineWidth(0.75);
      doc.rect(margin, hy, contentWidth, headerH, 'S');

      doc.setFont('helvetica', 'bold');
      doc.setFontSize(9.5);
      doc.setTextColor(15, 23, 42);

      scaledCols.forEach(col => {
        const text = this.cleanMarkdown(col.header);
        const avail = col.width - (padX * 2);
        const lines = doc.splitTextToSize(text, avail);
        const tx = col.align === 'center'
          ? cx + Math.max(padX, (col.width - doc.getTextWidth(lines[0] || '')) / 2)
          : cx + padX;
        doc.text(lines[0] || '', tx, hy + 15);

        doc.line(cx + col.width, hy, cx + col.width, hy + headerH);
        cx += col.width;
      });
      ctx.addY(headerH);
    };

    const ensureTableFits = (nextY: number) => {
      if (nextY + rowBreakBuffer > pageHeight - margin - 35) {
        doc.addPage(ctx.orientation);
        ctx.setY(margin + 8);
      }
    };

    ensureTableFits(ctx.getY() + headerH + 10);
    renderHeader();

    rows.forEach((row, rowIndex) => {
      let maxLines = 1;
      const cellLines = scaledCols.map(col => {
        const lines = doc.splitTextToSize(this.cleanMarkdown(row[col.key] == null ? '' : String(row[col.key])), col.width - (padX * 2));
        maxLines = Math.max(maxLines, lines.length);
        return lines;
      });
      const rowHeight = Math.max(20, maxLines * 12.5 + padY * 2);
      if (ctx.getY() + rowHeight > pageHeight - margin - 35) {
        doc.addPage(ctx.orientation);
        ctx.setY(margin + 8);
        renderHeader();
      }
      const rowY = ctx.getY();
      if (rowIndex % 2 === 1) {
        doc.setFillColor(248, 250, 252);
        doc.rect(margin, rowY, contentWidth, rowHeight, 'F');
      }
      doc.setDrawColor(226, 232, 240);
      doc.setLineWidth(0.5);
      doc.rect(margin, rowY, contentWidth, rowHeight, 'S');
      doc.setFont('helvetica', 'normal');
      doc.setFontSize(9);
      doc.setTextColor(30, 41, 59);
      let currentX = margin;
      scaledCols.forEach((col, columnIndex) => {
        cellLines[columnIndex].forEach((line: string, lineIndex: number) => {
          const x = col.align === 'center' ? currentX + Math.max(padX, (col.width - doc.getTextWidth(line)) / 2) : currentX + padX;
          doc.text(line, x, rowY + padY + 8.5 + lineIndex * 12.5);
        });
        doc.line(currentX + col.width, rowY, currentX + col.width, rowY + rowHeight);
        currentX += col.width;
      });
      ctx.addY(rowHeight);
    });
    ctx.addY(14);
    return;
  }

  /*
        const padY = 6;
        const boxHeights: number[] = steps.map(s => {
          doc.setFont('helvetica', 'normal');
          doc.setFontSize(9);
          const descLines = s.desc ? doc.splitTextToSize(this.cleanMarkdown(s.desc), boxW - 18) : [];
          return Math.max(34, 18 + (descLines.length * 11) + (padY * 2));
        });
        const baseHeight = 28 + boxHeights.reduce((sum, height) => sum + height, 0) + ((steps.length - 1) * arrowH) + 14;
        const bottomY = pageHeight - margin - 35;
        let stepIndex = 0;
        let pagePart = 0;

        while (stepIndex < steps.length) {
          const availableHeight = Math.max(120, bottomY - ctx.getY());
          const chunkStart = stepIndex;
          let chunkHeight = 28 + 14;

          while (stepIndex < steps.length) {
            const nextHeight = boxHeights[stepIndex] + (stepIndex > chunkStart ? arrowH : 0);
            if (stepIndex > chunkStart && chunkHeight + nextHeight > availableHeight) break;
            chunkHeight += nextHeight;
            stepIndex += 1;
          }

          if (chunkStart === stepIndex) {
            doc.addPage(ctx.orientation);
            ctx.setY(margin + 20);
            continue;
          }

          const chunk = steps.slice(chunkStart, stepIndex);
          const startY = ctx.getY();

          doc.setFillColor(248, 250, 252);
          doc.setDrawColor(203, 213, 225);
          doc.setLineWidth(0.75);
          doc.roundedRect(margin, startY, contentWidth, chunkHeight, 6, 6, 'FD');

          doc.setFont('helvetica', 'bold');
          doc.setFontSize(11);
          doc.setTextColor(15, 23, 42);
          doc.text(`${this.cleanMarkdown(title)}${pagePart ? ' (continued)' : ''}`, margin + 14, startY + 16);

          let curY = startY + 28;
          chunk.forEach((step, chunkIndex) => {
            const originalIndex = chunkStart + chunkIndex;
            const bH = boxHeights[originalIndex];

            doc.setFillColor(255, 255, 255);
            doc.setDrawColor(2, 132, 199);
            doc.setLineWidth(1);
            doc.roundedRect(boxX, curY, boxW, bH, 4, 4, 'FD');

            const compLabel = step.component ? `[${this.cleanMarkdown(step.component)}] ` : '';
            const stepTitle = `${compLabel}${this.cleanMarkdown(step.label)}`;
            doc.setFont('helvetica', 'bold');
            doc.setFontSize(9.5);
            doc.setTextColor(2, 132, 199);
            doc.text(stepTitle, boxX + 9, curY + 13);

            if (step.desc) {
              doc.setFont('helvetica', 'normal');
              doc.setFontSize(8.5);
              doc.setTextColor(51, 65, 85);
              const dLines = doc.splitTextToSize(this.cleanMarkdown(step.desc), boxW - 18);
              dLines.forEach((line: string, lineIndex: number) => {
                doc.text(line, boxX + 9, curY + 25 + (lineIndex * 11));
              });
            }

            curY += bH;
            if (chunkIndex < chunk.length - 1) {
              const arrowCenterX = boxX + (boxW / 2);
              const arrowEndY = curY + arrowH;
              doc.setDrawColor(100, 116, 139);
              doc.setLineWidth(1.2);
              doc.line(arrowCenterX, curY, arrowCenterX, arrowEndY);
              doc.setFillColor(100, 116, 139);
              doc.triangle(arrowCenterX, arrowEndY, arrowCenterX - 3.5, arrowEndY - 5, arrowCenterX + 3.5, arrowEndY - 5, 'FD');
              curY += arrowH;
            }
          });

          ctx.setY(startY + chunkHeight + 16);
          pagePart += 1;
          if (stepIndex < steps.length) {
            doc.addPage(ctx.orientation);
            ctx.setY(margin + 20);
          }
        }
      }
      if (i > 1) {
        doc.setFont('helvetica', 'normal');
        doc.setFontSize(8.5);
        doc.setTextColor(100, 116, 139);

        // Left header
        doc.text(this.cleanMarkdown(projectName), margin, 32);

        // Right header (Document Type uppercase)
        const typeStr = this.cleanMarkdown(docType).toUpperCase();
        const typeW = doc.getTextWidth(typeStr);
        doc.text(typeStr, pageWidth - margin - typeW, 32);

        // Top divider rule
        doc.setDrawColor(226, 232, 240);
        doc.setLineWidth(0.5);
        doc.line(margin, 38, pageWidth - margin, 38);
      }

      // Running Footer on EVERY page (Specs 41 & 42)
      doc.setFont('helvetica', 'normal');
      doc.setFontSize(8.5);
      doc.setTextColor(100, 116, 139);

      // Bottom divider rule
      doc.setDrawColor(226, 232, 240);
      doc.setLineWidth(0.5);
      doc.line(margin, pageHeight - 34, pageWidth - margin, pageHeight - 34);

      // Left footer
      const leftFooter = `AI Work Copilot  |  Project: ${this.cleanMarkdown(projectName)}`;
      doc.text(leftFooter, margin, pageHeight - 20);

      // Right footer: "Page X of Y"
      const pageStr = `Page ${i} of ${total}`;
      const pw = doc.getTextWidth(pageStr);
      doc.text(pageStr, pageWidth - margin - pw, pageHeight - 20);
    }
  }

  // Alias for backward compatibility
  */

  private docApplyHeaderAndFooters(ctx: any): void {
    const { doc, margin, pageWidth, pageHeight, docType, meta } = ctx;
    const total = doc.getNumberOfPages();
    const projectName = meta?.project || meta?.documentName || 'AI Work Copilot';
    for (let page = 1; page <= total; page++) {
      doc.setPage(page);
      doc.setFont('helvetica', 'normal');
      doc.setFontSize(8.5);
      doc.setTextColor(100, 116, 139);
      if (page > 1) {
        doc.text(this.cleanMarkdown(projectName), margin, 32);
        const typeText = this.cleanMarkdown(docType).toUpperCase();
        doc.text(typeText, pageWidth - margin - doc.getTextWidth(typeText), 32);
        doc.setDrawColor(226, 232, 240);
        doc.line(margin, 38, pageWidth - margin, 38);
      }
      doc.setDrawColor(226, 232, 240);
      doc.line(margin, pageHeight - 34, pageWidth - margin, pageHeight - 34);
      this.addNewgenFooterLogo(doc, margin, pageHeight - 20);
      const pageText = `Page ${page} of ${total}`;
      doc.text(pageText, pageWidth - margin - doc.getTextWidth(pageText), pageHeight - 20);
    }
  }

  private addNewgenFooterLogo(doc: any, x: number, baselineY: number): void {
    if (this.newgenLogo) {
      doc.addImage(this.newgenLogo, 'PNG', x, baselineY - 12, 42, 13);
      return;
    }

    doc.setFont('helvetica', 'bold');
    doc.setFontSize(9);
    doc.setTextColor(243, 111, 33);
    doc.text('newgen', x, baselineY);
  }

  private docApplyFooters(ctx: any): void {
    this.docApplyHeaderAndFooters(ctx);
  }

  // ============================================================
  // 1. USER STORY PDF (Spec 25)
  // ============================================================
  buildUserStoryDoc(items: any | any[], meta?: any): { ctx: any; docName: string; filename: string; list: any[] } | null {
    const list: any[] = Array.isArray(items) ? items : (items ? [items] : []);
    if (!list || list.length === 0) {
      return null;
    }

    const rawDocName = (meta?.documentName || '').trim();
    const docName = rawDocName || 'User Story Specification';
    const ctx = this.newDocCtx('User Story', docName, meta);

    // Title & Aligned Metadata Block
    this.docArtifactHeading(ctx);
    this.docMetaBlock(ctx, [
      { label: 'Project Name',    value: meta?.project || '-' },
      { label: 'Work / Mode',     value: meta?.work    || meta?.inputType || 'User Stories' },
      { label: 'Document Version', value: meta?.version || '-' },
      { label: 'Generated On',    value: new Date().toLocaleDateString() }
    ]);
    this.docRule(ctx);

    // Render each User Story as a clean, structured block (Spec 25)
    list.forEach((story: any, idx: number) => {
      const storyId = story.userStoryId || story.requirementId || `US-${String(idx + 1).padStart(3, '0')}`;
      const storyTitle = story.title || `User Story ${idx + 1}`;

      this.docSubSection(ctx, `${storyId}  ${storyTitle}`);

      // User Story Statement
      if (story.userStory) {
        this.docInlineLabel(ctx, 'User Story', story.userStory);
      }

      // Description / Summary
      const desc = story.description || story.summary;
      if (desc && desc.trim()) {
        this.docInlineLabel(ctx, 'Description', desc);
      }

      // Acceptance Criteria (Numbered list with hanging indent, Spec 13 & 25)
      const acList = story.acceptanceCriteria || story.acceptance_criteria;
      if (acList && acList.length > 0) {
        this.docLabelLine(ctx, 'Acceptance Criteria');
        acList.forEach((ac: any, acIdx: number) => {
          const text = this.toText(ac);
          const defaultId = `AC-${String(acIdx + 1).padStart(3, '0')}`;
          const prefix = text.startsWith('AC-') ? '' : `${defaultId}: `;
          const srcTag = this.formatItemSource(ac);
          this.docNumbered(ctx, acIdx + 1, `${prefix}${text}${srcTag ? ' ' + srcTag : ''}`);
        });
        ctx.addY(4);
      }

      // Business Rules (Bullets)
      if (story.businessRules && story.businessRules.length > 0) {
        this.docLabelLine(ctx, 'Business Rules');
        story.businessRules.forEach((br: any, brIdx: number) => {
          const text = this.toText(br);
          const defaultId = `BR-${String(brIdx + 1).padStart(3, '0')}`;
          const prefix = text.startsWith('BR-') ? '' : `${defaultId}: `;
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
          this.docLabelLine(ctx, 'Source References');
          srcArr.forEach((s: any) => this.docBullet(ctx, this.toText(s)));
        }
      }

      // Thin separator rule between stories
      if (idx < list.length - 1) {
        ctx.addY(8);
        this.docRule(ctx);
      }
    });

    this.docApplyHeaderAndFooters(ctx);

    const firstId = list[0]?.userStoryId || list[0]?.requirementId || 'US-001';
    const filename = this.buildPdfFilename('User_Story', meta, list.length === 1 ? firstId : docName);
    return { ctx, docName, filename, list };
  }

  generateUserStoryPdfBlob(items: any | any[], meta?: any): Blob | null {
    const built = this.buildUserStoryDoc(items, meta);
    if (!built) return null;
    return built.ctx.doc.output('blob');
  }

  downloadUserStoryPdf(items: any | any[], meta?: any): void {
    const list: any[] = Array.isArray(items) ? items : [items];
    if (!list || list.length === 0) {
      alert('No user story data available to export.');
      return;
    }
    const built = this.buildUserStoryDoc(list, meta);
    if (!built) return;
    built.ctx.doc.save(built.filename);
  }

  // ============================================================
  // 2. FUNCTIONAL DESIGN PDF (Spec 26)
  // ============================================================
  buildFunctionalDesignDoc(data: any, meta?: any): { ctx: any; filename: string } | null {
    if (!data) return null;

    const rawFd = data.functionalDesign || (Array.isArray(data.requirements) && data.requirements.length > 0 ? data.requirements[0] : data);
    const fd = { ...rawFd };

    if (!fd.objective && !fd.purpose) {
      fd.objective = fd.summary || fd.description || (typeof fd.userStory === 'string' ? fd.userStory.replace(/^Objective:\s*/i, '') : '');
    }
    if (typeof fd.objective === 'string') {
      if (fd.objective.includes('RequirementResponseDto') || fd.objective.includes('RequirementItemDto')) {
        fd.objective = '';
      } else {
        fd.objective = fd.objective.replace(/^Objective:\s*/i, '').trim();
      }
    }
    if ((!fd.scope || (Array.isArray(fd.scope) && fd.scope.length === 0)) && fd.objective) {
      fd.scope = [fd.objective];
    }
    if (!fd.validations && fd.acceptanceCriteria) {
      fd.validations = fd.acceptanceCriteria;
    }
    if (!fd.errorHandling && fd.edgeCases) {
      fd.errorHandling = fd.edgeCases;
    }
    data = fd;

    const rawDocName = (data.title || meta?.documentName || '').trim();
    const docName = rawDocName || 'Functional Specification';
    const ctx = this.newDocCtx('Functional Design', docName, meta);

    // Title & Aligned Metadata Block
    this.docArtifactHeading(ctx);
    this.docMetaBlock(ctx, [
      { label: 'Project Name',    value: meta?.project || '-' },
      { label: 'Work / Feature',  value: meta?.work    || meta?.inputType || 'Functional Design' },
      { label: 'Document Version', value: meta?.version || '-' },
      { label: 'Generated On',    value: new Date().toLocaleDateString() }
    ]);
    this.docRule(ctx);

    let secIdx = 1;

    // 1. Purpose & Objectives
    if (data.objective || data.purpose) {
      this.docSection(ctx, `${secIdx++}. Purpose & Objectives`);
      this.docParagraph(ctx, data.objective || data.purpose);
    }

    // 2. Scope
    const scopeList = Array.isArray(data.scope) ? data.scope : (data.scope ? [data.scope] : []);
    if (scopeList.length > 0) {
      this.docSection(ctx, `${secIdx++}. Scope`);
      this.docLabelLine(ctx, 'In Scope');
      scopeList.forEach((s: any) => this.docBullet(ctx, this.toText(s)));

      if (data.outOfScope && Array.isArray(data.outOfScope) && data.outOfScope.length > 0) {
        ctx.addY(6);
        this.docLabelLine(ctx, 'Out of Scope');
        data.outOfScope.forEach((s: any) => this.docBullet(ctx, this.toText(s)));
      }
      ctx.addY(6);
    }

    // 3. Actors & User Roles
    if (data.actors && data.actors.length > 0) {
      this.docSection(ctx, `${secIdx++}. Actors & User Roles`);
      data.actors.forEach((act: any, idx: number) => {
        const name = act.name || `Actor ${idx + 1}`;
        const desc = act.description || '';
        this.docSubSection(ctx, `${secIdx - 1}.${idx + 1}  ${name}`);
        if (desc) this.docParagraph(ctx, desc);
      });
    }

    // 4. Preconditions
    if (data.preconditions && data.preconditions.length > 0) {
      this.docSection(ctx, `${secIdx++}. Preconditions`);
      data.preconditions.forEach((p: any, i: number) => this.docNumbered(ctx, i + 1, this.toText(p)));
      ctx.addY(6);
    }

    // 5. Main Functional Flow
    if (data.mainFlow && data.mainFlow.length > 0) {
      this.docSection(ctx, `${secIdx++}. Main Functional Flow`);
      data.mainFlow.forEach((step: any) => {
        const sNum = step.step != null ? `Step ${step.step}` : '';
        const actor = step.actor ? `  [Actor: ${step.actor}]` : '';
        const label = `${sNum}${actor}`;
        if (label) this.docSubSection(ctx, label);
        if (step.action) this.docInlineLabel(ctx, 'Action', step.action);
        if (step.systemResponse) this.docInlineLabel(ctx, 'System Response', step.systemResponse);
      });
    }

    // 6. Alternate Flows
    if (data.alternateFlows && data.alternateFlows.length > 0) {
      this.docSection(ctx, `${secIdx++}. Alternate Flows`);
      data.alternateFlows.forEach((af: any, i: number) => {
        const flowName = af.name || `Alternate Flow ${i + 1}`;
        this.docSubSection(ctx, `${secIdx - 1}.${i + 1}  ${flowName}`);
        if (af.steps && af.steps.length > 0) {
          af.steps.forEach((s: any, si: number) => this.docNumbered(ctx, si + 1, this.toText(s)));
        }
        ctx.addY(4);
      });
    }

    // 7. Validation Rules (Table)
    if (data.validations && data.validations.length > 0) {
      this.docSection(ctx, `${secIdx++}. Validation Rules`);
      const tableRows = data.validations.map((v: any) => ({
        field: v.field || 'General',
        rule: v.rule || this.toText(v),
        grounding: v.grounding || 'Standard'
      }));
      this.docTable(ctx, [
        { header: 'Field / Target', key: 'field', width: 130 },
        { header: 'Validation Rule', key: 'rule', width: 250 },
        { header: 'Source / Grounding', key: 'grounding', width: 100 }
      ], tableRows);
    }

    // 8. Business Rules
    if (data.businessRules && data.businessRules.length > 0) {
      this.docSection(ctx, `${secIdx++}. Business Rules`);
      data.businessRules.forEach((br: any) => this.docBullet(ctx, this.toText(br)));
      ctx.addY(6);
    }

    // 9. Input Specifications (Table)
    if (data.inputs && data.inputs.length > 0) {
      this.docSection(ctx, `${secIdx++}. Input Specifications`);
      this.docTable(ctx, [
        { header: 'Input Field', key: 'name', width: 110 },
        { header: 'Description', key: 'description', width: 210 },
        { header: 'Required', key: 'reqText', width: 70 },
        { header: 'Format', key: 'format', width: 90 }
      ], data.inputs.map((inp: any) => ({
        name: inp.name || '',
        description: inp.description || '',
        reqText: inp.required ? 'Yes' : 'No',
        format: inp.format || 'String'
      })));
    }

    // 10. Output Specifications
    if (data.outputs && data.outputs.length > 0) {
      this.docSection(ctx, `${secIdx++}. Output Specifications`);
      data.outputs.forEach((o: any) => this.docBullet(ctx, this.toText(o)));
      ctx.addY(6);
    }

    // 11. Error Handling Specifications
    if (data.errorHandling && data.errorHandling.length > 0) {
      this.docSection(ctx, `${secIdx++}. Error Handling Specifications`);
      data.errorHandling.forEach((eh: any) => {
        const scenario = eh.scenario || '';
        const behavior = eh.expectedBehavior || eh.handling || this.toText(eh);
        if (scenario) this.docSubSection(ctx, scenario);
        this.docParagraph(ctx, behavior);
      });
    }

    // 12. System Dependencies
    if (data.dependencies && data.dependencies.length > 0) {
      this.docSection(ctx, `${secIdx++}. Dependencies`);
      data.dependencies.forEach((d: any) => this.docBullet(ctx, this.toText(d)));
      ctx.addY(6);
    }

    // 13. Assumptions & Constraints
    if (data.assumptions && data.assumptions.length > 0) {
      this.docSection(ctx, `${secIdx++}. Assumptions`);
      data.assumptions.forEach((a: any) => this.docBullet(ctx, this.toText(a)));
      ctx.addY(6);
    }

    // 14. Edge Cases
    if (data.edgeCases && data.edgeCases.length > 0) {
      this.docSection(ctx, `${secIdx++}. Edge Cases`);
      data.edgeCases.forEach((e: any) => this.docBullet(ctx, this.toText(e)));
      ctx.addY(6);
    }

    // 15. Source References
    if (data.sources) {
      const srcArr = Array.isArray(data.sources) ? data.sources : [data.sources];
      if (srcArr.length > 0) {
        this.docSection(ctx, `${secIdx++}. Source References`);
        srcArr.forEach((s: any) => this.docBullet(ctx, this.toText(s)));
      }
    }

    this.docApplyHeaderAndFooters(ctx);
    const filename = this.buildPdfFilename('Functional_Design', meta, docName);
    return { ctx, filename };
  }

  generateFunctionalDesignPdfBlob(data: any, meta?: any): Blob | null {
    const built = this.buildFunctionalDesignDoc(data, meta);
    if (!built) return null;
    return built.ctx.doc.output('blob');
  }

  downloadFunctionalDesignPdf(data: any, meta?: any): void {
    const built = this.buildFunctionalDesignDoc(data, meta);
    if (!built) {
      alert('No functional design data available to export.');
      return;
    }
    built.ctx.doc.save(built.filename);
  }

  // ============================================================
  // 3. TECHNICAL DESIGN PDF (Specs 27–35: Flowcharts, APIs, DB Schema)
  // ============================================================
  buildTechnicalDesignDoc(data: any, meta?: any): { ctx: any; filename: string } | null {
    if (!data) return null;

    const rawDocName = (data.title || meta?.documentName || '').trim();
    const docName = rawDocName || 'Technical Specification';
    const ctx = this.newDocCtx('Technical Design', docName, meta);

    // Title & Aligned Metadata Block
    this.docArtifactHeading(ctx);
    this.docMetaBlock(ctx, [
      { label: 'Project Name',     value: meta?.project || '-' },
      { label: 'Module / Work',    value: meta?.work    || meta?.inputType || 'Technical Design' },
      { label: 'Document Version', value: meta?.version || '-' },
      { label: 'Generated On',     value: new Date().toLocaleDateString() }
    ]);
    this.docRule(ctx);

    let secIdx = 1;

    // 1. Technical Overview
    const to = data.technicalOverview || {};
    const sysOverview = data.systemOverview || {};
    const hasTechOverview = to.whatIsBeingImplemented || to.technicalObjective || to.highLevelApproach ||
                            to.relationshipToUserStory || (to.scopeOfImplementation && to.scopeOfImplementation.length) ||
                            (to.outOfScope && to.outOfScope.length) || data.objective || data.overview ||
                            sysOverview.highLevelArchitecture || data.requirementSummary;
    if (hasTechOverview) {
      this.docSection(ctx, `${secIdx++}. Technical Overview`);
      if (to.whatIsBeingImplemented) {
        this.docLabelLine(ctx, 'What is Being Implemented:');
        this.docParagraph(ctx, to.whatIsBeingImplemented, 8);
      }
      if (to.technicalObjective || data.objective) {
        this.docLabelLine(ctx, 'Technical Objective:');
        this.docParagraph(ctx, to.technicalObjective || data.objective, 8);
      }
      if (sysOverview.highLevelArchitecture) {
        this.docLabelLine(ctx, 'System Architecture Overview:');
        this.docParagraph(ctx, sysOverview.highLevelArchitecture, 8);
      }
      if (to.highLevelApproach) {
        this.docLabelLine(ctx, 'High-Level Implementation Approach:');
        this.docParagraph(ctx, to.highLevelApproach, 8);
      }
      if (to.relationshipToUserStory) {
        this.docLabelLine(ctx, 'Relationship to Requirement / User Story:');
        this.docParagraph(ctx, to.relationshipToUserStory, 8);
      }
      if (data.requirementSummary) {
        this.docLabelLine(ctx, 'Requirement Summary:');
        this.docParagraph(ctx, data.requirementSummary, 8);
      }
      if (sysOverview.keyPrinciples && Array.isArray(sysOverview.keyPrinciples) && sysOverview.keyPrinciples.length > 0) {
        this.docLabelLine(ctx, 'Architectural Key Principles:');
        sysOverview.keyPrinciples.forEach((kp: any) => this.docBullet(ctx, this.toText(kp)));
      }
      if (to.scopeOfImplementation && to.scopeOfImplementation.length > 0) {
        this.docTable(ctx, [
          { header: 'In-Scope Deliverable', key: 'item', width: 480 }
        ], to.scopeOfImplementation.map((item: any) => ({ item: this.toText(item) })));
      }
      if (to.outOfScope && to.outOfScope.length > 0) {
        this.docTable(ctx, [
          { header: 'Out of Scope', key: 'item', width: 480 }
        ], to.outOfScope.map((item: any) => ({ item: this.toText(item) })));
      }
      if (!to.whatIsBeingImplemented && !to.technicalObjective && !sysOverview.highLevelArchitecture && (data.objective || data.overview)) {
        this.docParagraph(ctx, data.objective || data.overview, 10);
      }
    }

    // 2. Architecture Overview & Flowchart Diagram
    const ao = data.architectureOverview;
    const archFlow: any[] = Array.isArray(data.architectureFlow) ? data.architectureFlow : [];
    const flowchartSteps: any[] = Array.isArray(sysOverview.flowchartSteps) ? sysOverview.flowchartSteps : [];

    if (ao || archFlow.length > 0 || flowchartSteps.length > 0) {
      this.docSection(ctx, `${secIdx++}. Architecture & Component Overview`);
      
      // Visual Flowchart (from architectureFlow OR systemOverview.flowchartSteps)
      if (archFlow.length > 0) {
        const flowSteps = archFlow.map((step: any, i: number) => ({
          label: step.action ? `Step ${step.step || i + 1}` : (step.name || `Process ${i + 1}`),
          desc: step.action || step.details || '',
          component: step.component || ''
        }));
        this.docFlowchart(ctx, 'End-to-End Processing Architecture', flowSteps);
      } else if (flowchartSteps.length > 0) {
        const flowSteps = flowchartSteps.map((step: any, i: number) => ({
          label: `Stage ${i + 1}`,
          desc: this.toText(step),
          component: 'System Architecture Tier'
        }));
        this.docFlowchart(ctx, 'End-to-End Processing Architecture', flowSteps);
      } else if (ao?.textFlowDiagram) {
        this.docLabelLine(ctx, 'Architecture Flow Diagram:');
        this.docParagraph(ctx, ao.textFlowDiagram, 10);
      }

      // Components Involved Table
      const compRows: any[] = [];
      if (ao?.frontendComponents && Array.isArray(ao.frontendComponents)) {
        ao.frontendComponents.forEach((fc: any) => compRows.push({ tier: 'Frontend', component: this.toText(fc) }));
      }
      if (ao?.backendServices && Array.isArray(ao.backendServices)) {
        ao.backendServices.forEach((bs: any) => compRows.push({ tier: 'Backend', component: this.toText(bs) }));
      }
      if (compRows.length > 0) {
        this.docTable(ctx, [
          { header: 'System Tier', key: 'tier', width: 120, align: 'center' },
          { header: 'Component / Service Involved', key: 'component', width: 360 }
        ], compRows);
      }

      if (ao?.communicationFlow) {
        this.docInlineLabel(ctx, 'Communication Flow', ao.communicationFlow);
      }
    }

    // 3. Architecture Flow Steps (Table)
    if (archFlow.length > 0) {
      this.docSection(ctx, `${secIdx++}. Architecture Processing Steps`);
      this.docTable(ctx, [
        { header: 'Step', key: 'stepStr', width: 50, align: 'center' },
        { header: 'Component', key: 'component', width: 150 },
        { header: 'Technical Action & Processing', key: 'action', width: 280 }
      ], archFlow.map((s: any, idx: number) => ({
        stepStr: String(s.step != null ? s.step : idx + 1),
        component: s.component || '',
        action: s.action || s.details || this.toText(s)
      })));
    }

    // 4. Component-Level Detailed Specifications
    const components: any[] = Array.isArray(data.components) ? data.components : [];
    if (components.length > 0) {
      this.docSection(ctx, `${secIdx++}. Component-Level Design`);
      components.forEach((comp: any, idx: number) => {
        const name = comp.name || `Component ${idx + 1}`;
        this.docSubSection(ctx, `${secIdx - 1}.${idx + 1}  ${name}`);
        if (comp.responsibility) this.docInlineLabel(ctx, 'Responsibility', comp.responsibility);

        // Key Processing Logic (Clean vector sub-bullets)
        const logic: string[] = [];
        if (comp.keyLogic && Array.isArray(comp.keyLogic)) logic.push(...comp.keyLogic.map((k: any) => this.toText(k)));
        if (comp.steps && Array.isArray(comp.steps)) logic.push(...comp.steps.map((k: any) => this.toText(k)));
        if (comp.logic) logic.push(this.toText(comp.logic));
        if (comp.details) logic.push(this.toText(comp.details));
        if (comp.notes && Array.isArray(comp.notes)) logic.push(...comp.notes.map((n: any) => this.toText(n)));

        if (logic.length > 0) {
          this.docLabelLine(ctx, 'Key Processing Logic:');
          logic.forEach((line: string) => {
            const trimmed = String(line).trim();
            const isSub = /^[-*\u25e6\u2022]\s*/.test(trimmed);
            const cleanLine = trimmed.replace(/^[-*\u25e6\u2022]+\s*/, '');
            this.docBullet(ctx, cleanLine, isSub ? 1 : 0);
          });
        }

        if (comp.importantMethods && Array.isArray(comp.importantMethods) && comp.importantMethods.length > 0) {
          ctx.addY(4);
          this.docLabelLine(ctx, 'Key Methods & Interfaces:');
          comp.importantMethods.forEach((m: any) => this.docBullet(ctx, this.toText(m)));
        }

        if (comp.dependencies && Array.isArray(comp.dependencies) && comp.dependencies.length > 0) {
          ctx.addY(4);
          this.docLabelLine(ctx, 'Dependencies:');
          this.docParagraph(ctx, comp.dependencies.map((d: any) => this.toText(d)).join(', '), 6);
        }

        if (comp.rules && Array.isArray(comp.rules) && comp.rules.length > 0) {
          ctx.addY(4);
          this.docLabelLine(ctx, 'Component Rules:');
          comp.rules.forEach((r: any) => this.docBullet(ctx, this.toText(r)));
        }

        ctx.addY(6);
      });
    }

    // 5. Frontend Technical Design
    const fd = data.frontendDesign;
    if (fd) {
      this.docSection(ctx, `${secIdx++}. Frontend Technical Design`);
      const feRows: any[] = [];
      if (fd.angularComponents && Array.isArray(fd.angularComponents)) {
        fd.angularComponents.forEach((ac: any) => feRows.push({ type: 'Component', detail: this.toText(ac) }));
      }
      if (fd.services && Array.isArray(fd.services)) {
        fd.services.forEach((s: any) => feRows.push({ type: 'Service', detail: this.toText(s) }));
      }
      if (fd.models && Array.isArray(fd.models)) {
        fd.models.forEach((m: any) => feRows.push({ type: 'Model / Interface', detail: this.toText(m) }));
      }
      if (feRows.length > 0) {
        this.docTable(ctx, [
          { header: 'Frontend Artifact', key: 'type', width: 140 },
          { header: 'Name & Purpose', key: 'detail', width: 340 }
        ], feRows);
      }
      if (fd.formsAndState) this.docInlineLabel(ctx, 'Forms & State Management', fd.formsAndState);
      if (fd.editModeBehavior) this.docInlineLabel(ctx, 'Inline Edit Mode Behavior', fd.editModeBehavior);
      if (fd.loadingAndErrorStates) this.docInlineLabel(ctx, 'Loading & Error States', fd.loadingAndErrorStates);
      if (fd.uiStateTransitions) this.docInlineLabel(ctx, 'UI State Transitions', fd.uiStateTransitions);
      if (fd.validation && Array.isArray(fd.validation) && fd.validation.length > 0) {
        this.docLabelLine(ctx, 'Frontend Validation Rules:');
        fd.validation.forEach((v: any) => this.docBullet(ctx, this.toText(v)));
      }
    }

    // 6. Backend Technical Design
    const bd = data.backendDesign;
    if (bd) {
      this.docSection(ctx, `${secIdx++}. Backend Technical Design`);
      const beRows: any[] = [];
      if (bd.controllers && Array.isArray(bd.controllers)) {
        bd.controllers.forEach((c: any) => beRows.push({ layer: 'Controller', detail: this.toText(c) }));
      }
      if (bd.businessServices && Array.isArray(bd.businessServices)) {
        bd.businessServices.forEach((s: any) => beRows.push({ layer: 'Service', detail: this.toText(s) }));
      }
      if (bd.repositoryLayer && Array.isArray(bd.repositoryLayer)) {
        bd.repositoryLayer.forEach((r: any) => beRows.push({ layer: 'Repository', detail: this.toText(r) }));
      }
      if (beRows.length > 0) {
        this.docTable(ctx, [
          { header: 'Architecture Layer', key: 'layer', width: 130 },
          { header: 'Class / Component Description', key: 'detail', width: 350 }
        ], beRows);
      }
      if (bd.validation && Array.isArray(bd.validation) && bd.validation.length > 0) {
        this.docLabelLine(ctx, 'Server-Side Validation:');
        bd.validation.forEach((v: any) => this.docBullet(ctx, this.toText(v)));
      }
      if (bd.errorHandling && Array.isArray(bd.errorHandling) && bd.errorHandling.length > 0) {
        this.docLabelLine(ctx, 'Backend Error Handling:');
        bd.errorHandling.forEach((eh: any) => this.docBullet(ctx, this.toText(eh)));
      }
      if (bd.security && Array.isArray(bd.security) && bd.security.length > 0) {
        this.docLabelLine(ctx, 'Authentication & Authorization:');
        bd.security.forEach((sec: any) => this.docBullet(ctx, this.toText(sec)));
      }
    }

    // 7. API Contract & External Integrations
    const apis: any[] = Array.isArray(data.apis) ? data.apis : [];
    const apiContracts: any[] = Array.isArray(data.apiContracts) ? data.apiContracts : [];
    const integrationPoints: any[] = Array.isArray(data.integrationPoints) ? data.integrationPoints : [];

    if (apis.length > 0 || apiContracts.length > 0 || integrationPoints.length > 0) {
      this.docSection(ctx, `${secIdx++}. API Specifications & System Integrations`);
      
      if (apis.length > 0) {
        this.docTable(ctx, [
          { header: 'API Name', key: 'name', width: 105 },
          { header: 'Method', key: 'method', width: 55, align: 'center' },
          { header: 'Endpoint', key: 'endpoint', width: 155 },
          { header: 'Purpose', key: 'purpose', width: 115 },
          { header: 'Status', key: 'statusCodes', width: 50, align: 'center' }
        ], apis.map((api: any) => ({
          name: api.name || '',
          method: (api.method || 'GET').toUpperCase(),
          endpoint: api.endpoint || '',
          purpose: api.purpose || '',
          statusCodes: api.statusCodes ? (Array.isArray(api.statusCodes) ? api.statusCodes.join(', ') : api.statusCodes) : '200 OK'
        })));

        apis.forEach((api: any) => {
          if (api.request || api.response || (api.validationRules && api.validationRules.length)) {
            this.docSubSection(ctx, `API Contract: ${(api.method || 'GET').toUpperCase()} ${api.endpoint || api.name}`);
            if (api.request) {
              this.docLabelLine(ctx, 'Request Payload Schema / Example:');
              this.docParagraph(ctx, typeof api.request === 'object' ? JSON.stringify(api.request, null, 2) : String(api.request), 8);
            }
            if (api.response) {
              this.docLabelLine(ctx, 'Response Payload Schema / Example:');
              this.docParagraph(ctx, typeof api.response === 'object' ? JSON.stringify(api.response, null, 2) : String(api.response), 8);
            }
            if (api.validationRules && Array.isArray(api.validationRules) && api.validationRules.length > 0) {
              this.docLabelLine(ctx, 'Validation Rules:');
              api.validationRules.forEach((vr: any) => this.docBullet(ctx, this.toText(vr)));
            }
            if (api.errorScenarios && Array.isArray(api.errorScenarios) && api.errorScenarios.length > 0) {
              this.docLabelLine(ctx, 'Error Scenarios:');
              api.errorScenarios.forEach((es: any) => this.docBullet(ctx, this.toText(es)));
            }
          }
        });
      }

      if (apiContracts.length > 0 && apis.length === 0) {
        this.docTable(ctx, [
          { header: 'Integration Touchpoint', key: 'integration', width: 160 },
          { header: 'Data Flow Direction', key: 'direction', width: 140, align: 'center' },
          { header: 'Technical Specification & Notes', key: 'notes', width: 180 }
        ], apiContracts.map((ac: any) => ({
          integration: ac.integration || '',
          direction: ac.direction || '',
          notes: ac.notes || this.toText(ac)
        })));
      }

      if (integrationPoints.length > 0) {
        this.docSubSection(ctx, 'External Integration Touchpoints');
        integrationPoints.forEach((ip: any) => {
          const ipName = ip.name || 'Integration Point';
          const ipDir = ip.direction ? ` (${ip.direction})` : '';
          this.docLabelLine(ctx, `${ipName}${ipDir}`);
          if (ip.attributes && Array.isArray(ip.attributes) && ip.attributes.length > 0) {
            this.docTable(ctx, [
              { header: 'Integration Attribute', key: 'attribute', width: 150 },
              { header: 'Specification Details', key: 'detail', width: 330 }
            ], ip.attributes);
          }
        });
      }
    }

    // 8. Database Schema & Data Models
    const dataModel: any[] = Array.isArray(data.dataModel) ? data.dataModel : (Array.isArray(data.databaseSchema) ? data.databaseSchema : []);
    if (dataModel.length > 0) {
      this.docSection(ctx, `${secIdx++}. Data Model & Database Design`);
      dataModel.forEach((dm: any, idx: number) => {
        const entity = dm.entity || dm.table || dm.tableName || `Entity ${idx + 1}`;
        this.docSubSection(ctx, `${secIdx - 1}.${idx + 1}  Table: ${entity}`);
        if (dm.databaseChangesSummary) {
          this.docInlineLabel(ctx, 'Schema Changes', dm.databaseChangesSummary);
        }
        if (dm.description) {
          this.docParagraph(ctx, dm.description, 6);
        }
        if (dm.indexes) {
          this.docInlineLabel(ctx, 'Indexes', dm.indexes);
        }
        const fields: any[] = Array.isArray(dm.fields) ? dm.fields : (Array.isArray(dm.columns) ? dm.columns : []);
        if (fields.length > 0) {
          this.docTable(ctx, [
            { header: 'Field / Column', key: 'name', width: 115 },
            { header: 'Data Type', key: 'type', width: 80, align: 'center' },
            { header: 'Key', key: 'key', width: 45, align: 'center' },
            { header: 'Required', key: 'req', width: 60, align: 'center' },
            { header: 'Description / Constraints', key: 'desc', width: 180 }
          ], fields.map((f: any) => {
            const hasPK = f.primaryKey || (f.constraints && String(f.constraints).includes('PK'));
            const hasFK = f.foreignKey || (f.constraints && String(f.constraints).includes('FK'));
            const isReq = f.required || f.nullable === false || (f.constraints && String(f.constraints).includes('NOT NULL'));
            return {
              name: f.name || f.column || '',
              type: f.type || 'VARCHAR',
              key: hasPK ? 'PK' : (hasFK ? 'FK' : '-'),
              req: isReq ? 'Yes' : 'No',
              desc: f.description || f.constraints || ''
            };
          }));
        }
        if (dm.relationships) {
          const relStr = Array.isArray(dm.relationships) ? dm.relationships.join(', ') : dm.relationships;
          this.docInlineLabel(ctx, 'Relationships', relStr);
        }
        if (dm.persistenceBehavior) {
          this.docInlineLabel(ctx, 'Persistence Behavior', dm.persistenceBehavior);
        }
      });
    }

    // 9. End-to-End Data Flow (Flowchart + Table)
    const dataFlow: any[] = Array.isArray(data.dataFlow) ? data.dataFlow : [];
    if (dataFlow.length > 0) {
      this.docSection(ctx, `${secIdx++}. End-to-End Data Flow`);
      
      const dataFlowSteps = dataFlow.map((df: any, i: number) => ({
        label: `Step ${df.step || i + 1}`,
        desc: df.action || df.payload || '',
        component: `${df.source || 'Source'} -> ${df.target || 'Target'}`
      }));
      this.docFlowchart(ctx, 'End-to-End Data Flow Sequence', dataFlowSteps);

      this.docTable(ctx, [
        { header: 'Step', key: 'stepStr', width: 40, align: 'center' },
        { header: 'Source System', key: 'source', width: 95 },
        { header: 'Target System', key: 'target', width: 95 },
        { header: 'Action Performed', key: 'action', width: 130 },
        { header: 'Payload / Transferred Data', key: 'payload', width: 120 }
      ], dataFlow.map((df: any, idx: number) => ({
        stepStr: String(df.step != null ? df.step : idx + 1),
        source: df.source || '',
        target: df.target || '',
        action: df.action || '',
        payload: df.payload || ''
      })));
    }

    // 10. AI / LLM Integration Specifications
    const ai = data.aiLlmIntegration;
    if (ai) {
      this.docSection(ctx, `${secIdx++}. AI & LLM Integration Architecture`);
      if (ai.modelUsed) this.docInlineLabel(ctx, 'Model Employed', ai.modelUsed);
      this.docTable(ctx, [
        { header: 'AI Integration Dimension', key: 'dimension', width: 140 },
        { header: 'Implementation Specification', key: 'spec', width: 340 }
      ], [
        { dimension: 'Prompt Construction', spec: ai.promptConstruction || 'Standardized system prompt with zero-shot context' },
        { dimension: 'Input Context & Retrieval', spec: ai.inputContext || 'RAG semantic search and active knowledge store' },
        { dimension: 'Response Parsing', spec: ai.responseParsing || 'Strict JSON regex extraction and schema validation' },
        { dimension: 'Validation & Sanitization', spec: ai.validationAndSanitization || 'Sanitization against markdown artifacts and format schema' },
        { dimension: 'Error & Retry Handling', spec: ai.errorAndRetryHandling || 'Exponential backoff with circuit breaker pattern' },
        { dimension: 'Fallback Behavior', spec: ai.fallbackBehavior || 'Deterministic rule-based default response' }
      ].filter(r => r.spec && r.spec.length > 0));
    }

    // 11. Security Design (Existing & Recommended Controls Table)
    const secDesign = data.securityDesign;
    const secList: any[] = Array.isArray(data.security) ? data.security : [];
    const secConsiderations: any[] = Array.isArray(data.securityConsiderations) ? data.securityConsiderations : [];

    if (secDesign || secList.length > 0 || secConsiderations.length > 0) {
      this.docSection(ctx, `${secIdx++}. Security Design & Controls`);
      
      if (secConsiderations.length > 0) {
        this.docTable(ctx, [
          { header: 'ID', key: 'id', width: 55, align: 'center' },
          { header: 'Security Area', key: 'consideration', width: 115 },
          { header: 'Security Control Specification', key: 'detail', width: 220 },
          { header: 'Source Standard', key: 'source', width: 90 }
        ], secConsiderations.map((sc: any, idx: number) => ({
          id: sc.id || `SEC-${String(idx + 1).padStart(2, '0')}`,
          consideration: sc.consideration || '',
          detail: sc.detail || this.toText(sc),
          source: sc.source || 'Security Policy'
        })));
      } else {
        const secRows: any[] = [];
        if (secDesign?.existingControls && Array.isArray(secDesign.existingControls)) {
          secDesign.existingControls.forEach((ec: any) => secRows.push({ type: 'Existing Control', control: this.toText(ec) }));
        }
        if (secDesign?.recommendedControls && Array.isArray(secDesign.recommendedControls)) {
          secDesign.recommendedControls.forEach((rc: any) => secRows.push({ type: 'Recommended Control', control: this.toText(rc) }));
        }
        if (secList.length > 0 && secRows.length === 0) {
          secList.forEach((s: any) => secRows.push({ type: 'Security Measure', control: s.consideration || this.toText(s) }));
        }
        if (secRows.length > 0) {
          this.docTable(ctx, [
            { header: 'Control Category', key: 'type', width: 140 },
            { header: 'Security Control Specification', key: 'control', width: 340 }
          ], secRows);
        }
      }

      if (secDesign?.inputValidation) this.docInlineLabel(ctx, 'Input Validation', secDesign.inputValidation);
      if (secDesign?.secretsManagement) this.docInlineLabel(ctx, 'Secrets Management', secDesign.secretsManagement);
      if (secDesign?.loggingSecurity) this.docInlineLabel(ctx, 'Logging Security', secDesign.loggingSecurity);
    }

    // 12. Validation Rules (Frontend, Backend, Database Tables)
    const vr = data.validationRules;
    if (vr) {
      this.docSection(ctx, `${secIdx++}. Validation Rules`);
      if (vr.frontend && Array.isArray(vr.frontend) && vr.frontend.length > 0) {
        this.docSubSection(ctx, 'Frontend Validation Rules');
        this.docTable(ctx, [
          { header: 'Field', key: 'field', width: 120 },
          { header: 'Validation Rule', key: 'rule', width: 180 },
          { header: 'User Error Message', key: 'errorMsg', width: 180 }
        ], vr.frontend);
      }
      if (vr.backend && Array.isArray(vr.backend) && vr.backend.length > 0) {
        this.docSubSection(ctx, 'Backend Server-Side Validation');
        this.docTable(ctx, [
          { header: 'Field / Parameter', key: 'field', width: 120 },
          { header: 'Validation Rule', key: 'rule', width: 180 },
          { header: 'API Error Response', key: 'errorMsg', width: 180 }
        ], vr.backend);
      }
      if (vr.database && Array.isArray(vr.database) && vr.database.length > 0) {
        this.docSubSection(ctx, 'Database Constraints');
        this.docTable(ctx, [
          { header: 'Constraint Name', key: 'constraint', width: 150 },
          { header: 'Description', key: 'description', width: 330 }
        ], vr.database);
      }
    }

    // 13. Error Handling & Resilience (Table)
    const errorHandling: any[] = Array.isArray(data.errorHandling) ? data.errorHandling : [];
    if (errorHandling.length > 0) {
      this.docSection(ctx, `${secIdx++}. Error Handling & System Resilience`);
      this.docTable(ctx, [
        { header: 'Error Scenario', key: 'scenario', width: 110 },
        { header: 'Layer', key: 'whereItOccurs', width: 65, align: 'center' },
        { header: 'Handling Logic', key: 'handling', width: 140 },
        { header: 'Response', key: 'responseReturned', width: 75, align: 'center' },
        { header: 'User Experience', key: 'userExperience', width: 90 }
      ], errorHandling.map((eh: any) => ({
        scenario: eh.scenario || '',
        whereItOccurs: eh.whereItOccurs || 'Backend',
        handling: eh.handling || eh.expectedBehavior || this.toText(eh),
        responseReturned: eh.responseReturned || 'HTTP 500',
        userExperience: eh.userExperience || 'Toast alert'
      })));
    }

    // 14. Edge Cases & Technical Mitigations (Table)
    const edgeCases: any[] = Array.isArray(data.edgeCases) ? data.edgeCases : [];
    if (edgeCases.length > 0) {
      this.docSection(ctx, `${secIdx++}. Edge Cases & Technical Mitigations`);
      this.docTable(ctx, [
        { header: 'Scenario', key: 'scenario', width: 130 },
        { header: 'Impact', key: 'impact', width: 70, align: 'center' },
        { header: 'Technical Mitigation & Handling', key: 'handling', width: 280 }
      ], edgeCases.map((ec: any) => ({
        scenario: ec.scenario || '',
        impact: ec.impact || 'Medium',
        handling: ec.handling || ''
      })));
    }

    // 15. Business Rule Mappings (Table)
    const brm: any[] = Array.isArray(data.businessRuleMappings) ? data.businessRuleMappings : [];
    if (brm.length > 0) {
      this.docSection(ctx, `${secIdx++}. Business Rule to Technical Mappings`);
      this.docTable(ctx, [
        { header: 'Business Rule', key: 'businessRule', width: 180 },
        { header: 'Technical Implementation Details', key: 'technicalImplementation', width: 300 }
      ], brm);
    }

    // 16. Acceptance Criteria Mappings (Table)
    const acm: any[] = Array.isArray(data.acceptanceCriteriaMappings) ? data.acceptanceCriteriaMappings : [];
    if (acm.length > 0) {
      this.docSection(ctx, `${secIdx++}. Acceptance Criteria to Technical Mappings`);
      this.docTable(ctx, [
        { header: 'Acceptance Criterion', key: 'acceptanceCriterion', width: 180 },
        { header: 'Technical Implementation Details', key: 'technicalImplementation', width: 300 }
      ], acm);
    }

    // 17. Hard Constraints & Architectural Invariants (Table)
    const hardConstraints: any[] = Array.isArray(data.hardConstraints) ? data.hardConstraints : [];
    if (hardConstraints.length > 0) {
      this.docSection(ctx, `${secIdx++}. Hard Technical Constraints`);
      this.docTable(ctx, [
        { header: 'ID', key: 'id', width: 60, align: 'center' },
        { header: 'Hard Constraint Specification', key: 'constraint', width: 310 },
        { header: 'Source / Rule', key: 'source', width: 110 }
      ], hardConstraints.map((c: any, idx: number) => ({
        id: c.id || `C-${String(idx + 1).padStart(2, '0')}`,
        constraint: c.constraint || this.toText(c),
        source: c.source || 'BRD Constraint'
      })));
    }

    // 18. Dependencies & Assumptions (Tables)
    const deps = data.dependencies;
    const assumptions: any[] = Array.isArray(data.assumptions) ? data.assumptions : [];
    if (deps || assumptions.length > 0) {
      this.docSection(ctx, `${secIdx++}. Dependencies & Assumptions`);
      if (deps) {
        this.docSubSection(ctx, 'System Dependencies');
        const depRows: any[] = [];
        if (typeof deps === 'object' && !Array.isArray(deps)) {
          Object.keys(deps).forEach(k => {
            const arr = Array.isArray(deps[k]) ? deps[k] : [deps[k]];
            depRows.push({ category: k.toUpperCase(), items: arr.join(', ') });
          });
        } else if (Array.isArray(deps)) {
          deps.forEach((d: any) => depRows.push({ category: 'General', items: d.dependency || this.toText(d) }));
        }
        if (depRows.length > 0) {
          this.docTable(ctx, [
            { header: 'Dependency Tier', key: 'category', width: 120 },
            { header: 'Dependencies', key: 'items', width: 360 }
          ], depRows);
        }
      }
      if (assumptions.length > 0) {
        this.docSubSection(ctx, 'Technical Assumptions');
        this.docTable(ctx, [
          { header: 'Assumption', key: 'assumption', width: 370 },
          { header: 'Status', key: 'status', width: 110, align: 'center' }
        ], assumptions.map((a: any) => ({
          assumption: a.assumption || a.text || this.toText(a),
          status: a.status || 'CONFIRMED'
        })));
      }
    }

    // 19. Open Technical Questions (Table)
    const openQuestions: any[] = Array.isArray(data.openQuestions) ? data.openQuestions : [];
    if (openQuestions.length > 0) {
      this.docSection(ctx, `${secIdx++}. Open Technical Questions & Clarifications`);
      this.docTable(ctx, [
        { header: 'ID', key: 'id', width: 60, align: 'center' },
        { header: 'Technical Question / Unknown', key: 'question', width: 220 },
        { header: 'Architecture Impact', key: 'impact', width: 120 },
        { header: 'Source Section', key: 'source', width: 80 }
      ], openQuestions.map((oq: any, idx: number) => ({
        id: oq.id || `OQ-${String(idx + 1).padStart(2, '0')}`,
        question: oq.question || this.toText(oq),
        impact: oq.impact || 'Implementation Decision Required',
        source: oq.source || 'BRD Review'
      })));
    }

    // 20. Implementation Plan (Table)
    const implementationPlan: any[] = Array.isArray(data.implementationPlan) ? data.implementationPlan : [];
    if (implementationPlan.length > 0) {
      this.docSection(ctx, `${secIdx++}. Implementation Plan`);
      this.docTable(ctx, [
        { header: 'Step', key: 'stepStr', width: 40, align: 'center' },
        { header: 'Phase', key: 'phase', width: 85 },
        { header: 'Action Performed', key: 'action', width: 165 },
        { header: 'Deliverable', key: 'deliverable', width: 100 },
        { header: 'Verification', key: 'verification', width: 90 }
      ], implementationPlan.map((ip: any, idx: number) => ({
        stepStr: String(ip.step != null ? ip.step : idx + 1),
        phase: ip.phase || 'General',
        action: ip.action || '',
        deliverable: ip.deliverable || '',
        verification: ip.verification || ''
      })));
    }

    // 21. Testing Strategy (Table)
    const ts = data.testingStrategy;
    if (ts) {
      this.docSection(ctx, `${secIdx++}. Testing Strategy`);
      const testRows: any[] = [];
      if (ts.unitTesting && Array.isArray(ts.unitTesting)) {
        testRows.push({ level: 'Unit Testing', scope: ts.unitTesting.map((ut: any) => this.toText(ut)).join('; ') });
      }
      if (ts.integrationTesting && Array.isArray(ts.integrationTesting)) {
        testRows.push({ level: 'Integration Testing', scope: ts.integrationTesting.map((it: any) => this.toText(it)).join('; ') });
      }
      if (ts.functionalTesting && Array.isArray(ts.functionalTesting)) {
        testRows.push({ level: 'Functional E2E Testing', scope: ts.functionalTesting.map((ft: any) => this.toText(ft)).join('; ') });
      }
      if (ts.negativeTesting && Array.isArray(ts.negativeTesting)) {
        testRows.push({ level: 'Negative & Error Testing', scope: ts.negativeTesting.map((nt: any) => this.toText(nt)).join('; ') });
      }
      if (testRows.length > 0) {
        this.docTable(ctx, [
          { header: 'Testing Level', key: 'level', width: 130 },
          { header: 'Test Scope & Verification Details', key: 'scope', width: 350 }
        ], testRows);
      }
    }

    // 22. Performance, Logging & Configuration (Tables)
    const pcList: any[] = Array.isArray(data.performanceConsiderations) ? data.performanceConsiderations : [];
    const lmList: any[] = Array.isArray(data.loggingAndMonitoring) ? data.loggingAndMonitoring : [];
    const cfgList: any[] = Array.isArray(data.configuration) ? data.configuration : [];
    const fileImpact = data.fileImpact;
    if (pcList.length > 0 || lmList.length > 0 || cfgList.length > 0 || fileImpact) {
      this.docSection(ctx, `${secIdx++}. Performance, Logging & Configuration`);
      if (pcList.length > 0) {
        this.docSubSection(ctx, 'Performance Considerations');
        this.docTable(ctx, [
          { header: 'Area', key: 'area', width: 130 },
          { header: 'Consideration & Optimization', key: 'consideration', width: 350 }
        ], pcList.map((pc: any) => ({
          area: pc.area || 'General',
          consideration: pc.consideration || this.toText(pc)
        })));
      }
      if (lmList.length > 0) {
        this.docSubSection(ctx, 'Logging & Monitoring');
        this.docTable(ctx, [
          { header: 'Level', key: 'level', width: 60, align: 'center' },
          { header: 'Event', key: 'event', width: 140 },
          { header: 'Logging Details', key: 'details', width: 280 }
        ], lmList.map((lm: any) => ({
          level: lm.level || 'INFO',
          event: lm.event || '',
          details: lm.details || ''
        })));
      }
      if (cfgList.length > 0) {
        this.docSubSection(ctx, 'Configuration Variables');
        this.docTable(ctx, [
          { header: 'Variable Name', key: 'name', width: 160 },
          { header: 'Purpose & Description', key: 'purpose', width: 320 }
        ], cfgList.map((c: any) => ({
          name: c.name || '',
          purpose: c.purpose || ''
        })));
      }
      if (fileImpact) {
        this.docSubSection(ctx, 'Code File Impact');
        const fileRows: any[] = [];
        if (fileImpact.frontend && Array.isArray(fileImpact.frontend)) {
          fileImpact.frontend.forEach((f: any) => fileRows.push({ tier: 'Frontend', file: this.toText(f) }));
        }
        if (fileImpact.backend && Array.isArray(fileImpact.backend)) {
          fileImpact.backend.forEach((b: any) => fileRows.push({ tier: 'Backend', file: this.toText(b) }));
        }
        if (fileRows.length > 0) {
          this.docTable(ctx, [
            { header: 'Tier', key: 'tier', width: 100, align: 'center' },
            { header: 'Impacted File Path', key: 'file', width: 380 }
          ], fileRows);
        }
      }
    }

    // 23. Technical Risks & Decisions (Tables)
    const techRisks: any[] = Array.isArray(data.technicalRisks) ? data.technicalRisks : [];
    const techDecisions: any[] = Array.isArray(data.technicalDecisions) ? data.technicalDecisions : [];
    if (techRisks.length > 0 || techDecisions.length > 0) {
      this.docSection(ctx, `${secIdx++}. Technical Risks & Decisions`);
      if (techRisks.length > 0) {
        this.docSubSection(ctx, 'Technical Risks & Mitigations');
        this.docTable(ctx, [
          { header: 'Risk Description', key: 'risk', width: 160 },
          { header: 'Impact', key: 'impact', width: 65, align: 'center' },
          { header: 'Mitigation Strategy', key: 'mitigation', width: 255 }
        ], techRisks.map((tr: any) => ({
          risk: tr.risk || '',
          impact: tr.impact || 'Medium',
          mitigation: tr.mitigation || ''
        })));
      }
      if (techDecisions.length > 0) {
        this.docSubSection(ctx, 'Architecture & Technical Decisions');
        this.docTable(ctx, [
          { header: 'Decision', key: 'decision', width: 140 },
          { header: 'Rationale & Justification', key: 'reason', width: 200 },
          { header: 'Why Selected', key: 'whySelected', width: 140 }
        ], techDecisions.map((tdDec: any) => ({
          decision: tdDec.decision || '',
          reason: tdDec.reason || '',
          whySelected: tdDec.whySelected || ''
        })));
      }
    }

    // 24. Source References
    if (data.sources) {
      const srcArr = Array.isArray(data.sources) ? data.sources : [data.sources];
      if (srcArr.length > 0) {
        this.docSection(ctx, `${secIdx++}. Source References`);
        srcArr.forEach((s: any, sIdx: number) => this.docNumbered(ctx, sIdx + 1, this.toText(s)));
      }
    }

    this.docApplyHeaderAndFooters(ctx);
    const filename = this.buildPdfFilename('Technical_Design', meta, docName);
    return { ctx, filename };
  }

  generateTechnicalDesignPdfBlob(data: any, meta?: any): Blob | null {
    const built = this.buildTechnicalDesignDoc(data, meta);
    if (!built) return null;
    return built.ctx.doc.output('blob');
  }

  downloadTechnicalDesignPdf(data: any, meta?: any): void {
    const built = this.buildTechnicalDesignDoc(data, meta);
    if (!built) {
      alert('No technical design data available to export.');
      return;
    }
    built.ctx.doc.save(built.filename);
  }

  // ============================================================
  // 4. SOFTWARE REQUIREMENT SPECIFICATION PDF (Specs 7 & 24)
  // ============================================================
  downloadRequirementPdf(data: any, baseFilename = 'requirement', meta?: any): void {
    if (!data) { alert('No requirement data available to export.'); return; }

    const rawDocName = (data.title || meta?.documentName || '').trim();
    const docName = rawDocName || 'Requirement Specification';
    const ctx = this.newDocCtx('Requirement Assistant', docName, meta);

    // Title & Aligned Metadata Block
    this.docArtifactHeading(ctx);
    this.docMetaBlock(ctx, [
      { label: 'Project Name',    value: meta?.project || '-' },
      { label: 'Source Document', value: meta?.documentName || meta?.brd || '-' },
      { label: 'Document Version', value: meta?.version || '-' },
      { label: 'Generated On',    value: new Date().toLocaleDateString() }
    ]);
    this.docRule(ctx);

    // 1. Executive Summary
    if (data.summary) {
      this.docSection(ctx, '1. Executive Summary');
      this.docParagraph(ctx, data.summary);
    }

    // 2. Requirement Details
    this.docSection(ctx, '2. Requirement Specification');
    if (data.requirementId) this.docInlineLabel(ctx, 'Requirement ID', data.requirementId);
    if (data.title) this.docInlineLabel(ctx, 'Title', data.title);
    if (data.priority) this.docInlineLabel(ctx, 'Priority', data.priority);
    if (data.userStory) {
      this.docLabelLine(ctx, 'User Story');
      this.docParagraph(ctx, data.userStory, 10);
    }

    // 3. Acceptance Criteria (Numbered list, Spec 13)
    if (data.acceptanceCriteria && data.acceptanceCriteria.length > 0) {
      this.docSection(ctx, '3. Acceptance Criteria');
      data.acceptanceCriteria.forEach((ac: any, i: number) => {
        this.docNumbered(ctx, i + 1, this.toText(ac));
      });
      ctx.addY(4);
    }

    // 4. Business Rules
    if (data.businessRules && data.businessRules.length > 0) {
      this.docSection(ctx, '4. Business Rules');
      data.businessRules.forEach((br: any) => this.docBullet(ctx, this.toText(br)));
      ctx.addY(4);
    }

    // 5. Assumptions
    if (data.assumptions && data.assumptions.length > 0) {
      this.docSection(ctx, '5. Assumptions');
      data.assumptions.forEach((a: any) => this.docBullet(ctx, this.toText(a)));
      ctx.addY(4);
    }

    // 6. Dependencies
    if (data.dependencies && data.dependencies.length > 0) {
      this.docSection(ctx, '6. Dependencies');
      data.dependencies.forEach((d: any) => this.docBullet(ctx, this.toText(d)));
      ctx.addY(4);
    }

    // 7. Edge Cases
    if (data.edgeCases && data.edgeCases.length > 0) {
      this.docSection(ctx, '7. Edge Cases');
      data.edgeCases.forEach((e: any) => this.docBullet(ctx, this.toText(e)));
      ctx.addY(4);
    }

    this.docApplyHeaderAndFooters(ctx);
    ctx.doc.save(this.buildPdfFilename('Requirements', meta, baseFilename));
  }

  buildAllRequirementsDoc(requirements: any[], baseFilename = 'requirements', meta?: any): { ctx: any; filename: string } | null {
    if (!requirements || requirements.length === 0) {
      return null;
    }

    const rawDocName = (meta?.documentName || '').trim();
    const docName = rawDocName || 'Requirements Document';
    const ctx = this.newDocCtx('Requirement Assistant', docName, meta);

    // Title & Aligned Metadata Block
    this.docArtifactHeading(ctx);
    this.docMetaBlock(ctx, [
      { label: 'Project Name',    value: meta?.project || '-' },
      { label: 'Source Document', value: meta?.documentName || meta?.brd || '-' },
      { label: 'Total Requirements', value: String(requirements.length) },
      { label: 'Generated On',    value: new Date().toLocaleDateString() }
    ]);
    this.docRule(ctx);

    // 1. Requirements Summary Table (Spec 14–23)
    this.docSection(ctx, '1. Requirements Matrix Summary');
    const tableRows = requirements.map((r: any, idx: number) => ({
      reqId: r.requirementId || `REQ-${String(idx + 1).padStart(3, '0')}`,
      title: r.title || `Requirement ${idx + 1}`,
      priority: (r.priority || 'MEDIUM').toUpperCase(),
      acCount: String(r.acceptanceCriteria?.length || 0)
    }));
    this.docTable(ctx, [
      { header: 'Requirement ID', key: 'reqId', width: 110, align: 'center' },
      { header: 'Title / Scope', key: 'title', width: 230 },
      { header: 'Priority', key: 'priority', width: 75, align: 'center' },
      { header: 'AC Count', key: 'acCount', width: 65, align: 'center' }
    ], tableRows);

    // 2. Detailed Requirements Specifications
    this.docSection(ctx, '2. Detailed Requirements');
    requirements.forEach((req: any, idx: number) => {
      const reqId = req.requirementId || `REQ-${String(idx + 1).padStart(3, '0')}`;
      const title = req.title || `Requirement ${idx + 1}`;

      this.docSubSection(ctx, `2.${idx + 1}  [${reqId}] ${title}`);
      if (req.priority) this.docInlineLabel(ctx, 'Priority', req.priority);

      if (req.summary) {
        this.docLabelLine(ctx, 'Summary');
        this.docParagraph(ctx, req.summary, 10);
      }

      if (req.userStory) {
        this.docLabelLine(ctx, 'User Story');
        this.docParagraph(ctx, req.userStory, 10);
      }

      if (req.acceptanceCriteria && req.acceptanceCriteria.length > 0) {
        this.docLabelLine(ctx, 'Acceptance Criteria');
        req.acceptanceCriteria.forEach((ac: any, aci: number) => {
          this.docNumbered(ctx, aci + 1, this.toText(ac));
        });
        ctx.addY(4);
      }

      if (req.businessRules && req.businessRules.length > 0) {
        this.docLabelLine(ctx, 'Business Rules');
        req.businessRules.forEach((br: any) => this.docBullet(ctx, this.toText(br)));
        ctx.addY(4);
      }

      if (req.assumptions && req.assumptions.length > 0) {
        this.docLabelLine(ctx, 'Assumptions');
        req.assumptions.forEach((a: any) => this.docBullet(ctx, this.toText(a)));
        ctx.addY(4);
      }

      if (req.dependencies && req.dependencies.length > 0) {
        this.docLabelLine(ctx, 'Dependencies');
        req.dependencies.forEach((d: any) => this.docBullet(ctx, this.toText(d)));
        ctx.addY(4);
      }

      if (req.edgeCases && req.edgeCases.length > 0) {
        this.docLabelLine(ctx, 'Edge Cases');
        req.edgeCases.forEach((e: any) => this.docBullet(ctx, this.toText(e)));
        ctx.addY(4);
      }

      if (idx < requirements.length - 1) {
        ctx.addY(8);
        this.docRule(ctx);
      }
    });

    this.docApplyHeaderAndFooters(ctx);
    const filename = this.buildPdfFilename('Requirements', meta, baseFilename);
    return { ctx, filename };
  }

  generateAllRequirementsPdfBlob(requirements: any[], baseFilename = 'requirements', meta?: any): Blob | null {
    const built = this.buildAllRequirementsDoc(requirements, baseFilename, meta);
    if (!built) return null;
    return built.ctx.doc.output('blob');
  }

  downloadAllRequirementsPdf(requirements: any[], baseFilename = 'requirements', meta?: any): void {
    const built = this.buildAllRequirementsDoc(requirements, baseFilename, meta);
    if (!built) {
      alert('No requirements available to export.');
      return;
    }
    built.ctx.doc.save(built.filename);
  }

  // ============================================================
  // 5. TEST CASE PDF (Spec 36)
  // ============================================================
  buildTestCaseDoc(items: any[], meta?: any): { ctx: any; filename: string } | null {
    if (!items || items.length === 0) {
      return null;
    }

    const rawDocName = (meta?.documentName || '').trim();
    const docName = rawDocName || 'Test Case Specification';
    const ctx = this.newDocCtx('Test Generator', docName, meta);

    // Title & Aligned Metadata Block
    this.docArtifactHeading(ctx);
    this.docMetaBlock(ctx, [
      { label: 'Project Name',    value: meta?.project || '-' },
      { label: 'Work / Feature',  value: meta?.work    || meta?.inputType || 'Test Cases' },
      { label: 'Document Version', value: meta?.version || '-' },
      { label: 'Generated On',    value: new Date().toLocaleDateString() }
    ]);
    this.docRule(ctx);

    // Section 1: Execution Metrics Summary
    const totalCount = items.length;
    const highCount  = items.filter(i => (i.priority || '').toUpperCase() === 'HIGH').length;
    const negCount   = items.filter(i => (i.type || '').toUpperCase().includes('NEG')).length;
    const posCount   = totalCount - negCount;

    this.docSection(ctx, '1. Test Execution Summary');
    this.docTable(ctx, [
      { header: 'Test Execution Metric', key: 'metric', width: 240 },
      { header: 'Count / Value',         key: 'value',  width: 240, align: 'center' }
    ], [
      { metric: 'Total Test Cases Generated', value: String(totalCount) },
      { metric: 'Positive / Functional Cases', value: String(posCount) },
      { metric: 'Negative / Boundary Cases',  value: String(negCount) },
      { metric: 'High Priority Cases',        value: String(highCount) }
    ]);

    // Section 2: Comprehensive Test Case Table (Spec 36)
    this.docSection(ctx, '2. Test Case Matrix');
    const tableData = items.map((item: any, idx: number) => ({
      tcId: item.tcId || `TC-${String(idx + 1).padStart(3, '0')}`,
      scenario: item.scenario || item.title || `Test Case ${idx + 1}`,
      type: (item.type || 'POSITIVE').toUpperCase(),
      priority: (item.priority || 'MEDIUM').toUpperCase(),
      expectedResult: item.expectedResult || ''
    }));

    this.docTable(ctx, [
      { header: 'TC ID', key: 'tcId', width: 60, align: 'center' },
      { header: 'Scenario / Objective', key: 'scenario', width: 180 },
      { header: 'Type', key: 'type', width: 65, align: 'center' },
      { header: 'Priority', key: 'priority', width: 55, align: 'center' },
      { header: 'Expected Result', key: 'expectedResult', width: 120 }
    ], tableData);

    // Section 3: Detailed Test Case Specifications
    this.docSection(ctx, '3. Detailed Test Case Specifications');
    items.forEach((item: any, idx: number) => {
      const tcId     = item.tcId || `TC-${String(idx + 1).padStart(3, '0')}`;
      const reqId    = item.requirementId || item.sourceReference || '';
      const scenario = item.scenario || item.title || `Test Case ${idx + 1}`;
      const type     = (item.type || 'POSITIVE').toUpperCase();
      const priority = (item.priority || 'MEDIUM').toUpperCase();

      this.docSubSection(ctx, `${tcId}  ${scenario}`);
      this.docInlineLabel(ctx, 'Type', type);
      this.docInlineLabel(ctx, 'Priority', priority);
      if (reqId) this.docInlineLabel(ctx, 'Requirement Ref', reqId);

      // Preconditions
      const preconds: string[] = Array.isArray(item.preconditions)
        ? item.preconditions
        : (item.preconditions ? [String(item.preconditions)] : []);
      if (preconds.length > 0) {
        this.docLabelLine(ctx, 'Preconditions');
        preconds.forEach((pc: string) => this.docBullet(ctx, pc, 1));
      }

      // Test Steps (Numbered list, Spec 13 & 36)
      const steps: string[] = Array.isArray(item.steps)
        ? item.steps
        : (item.steps ? [String(item.steps)] : []);
      if (steps.length > 0) {
        this.docLabelLine(ctx, 'Execution Steps');
        steps.forEach((s: string, si: number) => this.docNumbered(ctx, si + 1, s));
      }

      // Expected Result
      if (item.expectedResult) {
        this.docLabelLine(ctx, 'Expected Result');
        this.docParagraph(ctx, item.expectedResult, 12);
      }

      if (idx < items.length - 1) {
        ctx.addY(6);
        this.docRule(ctx);
      }
    });

    this.docApplyHeaderAndFooters(ctx);
    const filename = this.buildPdfFilename('Test_Cases', meta, docName);
    return { ctx, filename };
  }

  generateTestCasePdfBlob(items: any[], meta?: any): Blob | null {
    const built = this.buildTestCaseDoc(items, meta);
    if (!built) return null;
    return built.ctx.doc.output('blob');
  }

  downloadTestCasePdf(items: any[], meta?: any): void {
    const built = this.buildTestCaseDoc(items, meta);
    if (!built) {
      alert('No test case data available to export.');
      return;
    }
    built.ctx.doc.save(built.filename);
  }

  // ============================================================
  // 6. DEFECT TRIAGE PDF (Spec 37)
  // ============================================================
  private buildDefectTriageDoc(data: any, baseFilename = 'defect-triage', meta?: any): { ctx: any; filename: string } | null {
    const defects: any[] = Array.isArray(data?.defects)
      ? data.defects
      : (data ? [data] : []);

    if (defects.length === 0) {
      return null;
    }

    const rawDocName = (meta?.documentName || '').trim();
    const docName = rawDocName || 'Defect Triage Report';
    const ctx = this.newDocCtx('Defect Triage', docName, meta);

    // Title & Aligned Metadata Block
    this.docArtifactHeading(ctx);
    this.docMetaBlock(ctx, [
      { label: 'Project Name',    value: meta?.project || '-' },
      { label: 'Work / Module',   value: meta?.work    || meta?.inputType || 'Defect Triage' },
      { label: 'Total Defects',   value: String(defects.length) },
      { label: 'Generated On',    value: new Date().toLocaleDateString() }
    ]);
    this.docRule(ctx);

    // 1. Executive Summary
    if (data.executiveSummary || data.summary) {
      this.docSection(ctx, '1. Executive Summary');
      this.docParagraph(ctx, data.executiveSummary || data.summary);
    }

    // 2. Defect Summary Table (Spec 37)
    this.docSection(ctx, '2. Defect Summary');
    this.docTable(ctx, [
      { header: 'Defect ID',  key: 'defectId',  width: 70, align: 'center' },
      { header: 'Title / Summary', key: 'title', width: 170 },
      { header: 'Severity',   key: 'severity',  width: 60, align: 'center' },
      { header: 'Priority',   key: 'priority',  width: 55, align: 'center' },
      { header: 'Status',     key: 'status',    width: 65, align: 'center' },
      { header: 'Component',  key: 'component', width: 60 }
    ], defects.map((d: any, i: number) => ({
      defectId:  d.defectId  || `DEF-${String(i + 1).padStart(3, '0')}`,
      title:     d.title     || d.summary || '',
      severity:  d.severity  || 'MEDIUM',
      priority:  d.priority  || 'P2',
      status:    d.status    || 'OPEN',
      component: d.component || 'Core'
    })));

    // 3. Detailed Defect Analysis (Spec 37)
    this.docSection(ctx, '3. Detailed Defect Analysis');
    defects.forEach((defect: any, idx: number) => {
      const defId = defect.defectId || `DEF-${String(idx + 1).padStart(3, '0')}`;
      const defTitle = defect.title || defect.summary || `Defect ${idx + 1}`;

      this.docSubSection(ctx, `3.${idx + 1}  [${defId}] ${defTitle}`);
      this.docInlineLabel(ctx, 'Severity',   defect.severity   || 'MEDIUM');
      this.docInlineLabel(ctx, 'Priority',   defect.priority   || 'P2');
      this.docInlineLabel(ctx, 'Status',     defect.status     || 'OPEN');
      this.docInlineLabel(ctx, 'Component',  defect.component  || '');
      if (defect.location) this.docInlineLabel(ctx, 'Location', defect.location);

      // Probable Root Cause
      const rc = defect.probableRootCause || defect.rootCause || '';
      if (rc) {
        this.docLabelLine(ctx, 'Probable Root Cause');
        this.docParagraph(ctx, rc, 10);
      }

      // Impact
      if (defect.impact) {
        this.docLabelLine(ctx, 'Impact');
        this.docParagraph(ctx, defect.impact, 10);
      }

      // Steps to Reproduce / Trigger (Numbered list, Spec 13)
      const trigger = defect.trigger || defect.stepsToReproduce || '';
      if (trigger) {
        this.docLabelLine(ctx, 'Trigger / Steps to Reproduce');
        const steps = Array.isArray(trigger) ? trigger : [trigger];
        steps.forEach((s: any, si: number) => this.docNumbered(ctx, si + 1, this.toText(s)));
      }

      // Suggested Fix (Monospace code block, Spec 33)
      const fix = defect.fix || defect.suggestedFix || '';
      if (fix) {
        this.docCodeBlock(ctx, fix, 'Recommended Fix');
      }

      // Evidence & Stack Trace (Monospace block, Spec 33 & 37)
      const evidence = defect.evidence || defect.stackTrace || '';
      if (evidence) {
        this.docCodeBlock(ctx, evidence, 'Evidence & Stack Trace Analysis');
      }

      if (idx < defects.length - 1) {
        ctx.addY(8);
        this.docRule(ctx);
      }
    });

    this.docApplyHeaderAndFooters(ctx);
    return { ctx, filename: this.buildPdfFilename('Defect_Triage', meta, baseFilename) };
  }

  generateDefectPdfBlob(data: any, baseFilename = 'defect-triage', meta?: any): Blob | null {
    const built = this.buildDefectTriageDoc(data, baseFilename, meta);
    return built ? built.ctx.doc.output('blob') : null;
  }

  downloadDefectPdf(data: any, baseFilename = 'defect-triage', meta?: any): void {
    const built = this.buildDefectTriageDoc(data, baseFilename, meta);
    if (!built) {
      alert('No defect triage data available to export.');
      return;
    }
    built.ctx.doc.save(built.filename);
  }

  // ============================================================
  // 7. RELEASE NOTES PDF (Spec 38)
  // ============================================================
  private buildReleaseNoteDoc(data: any, baseFilename = 'release-notes', meta?: any): { ctx: any; filename: string } | null {
    const rawDocName = (meta?.documentName || data?.productName || '').trim();
    const version = data?.version || data?.releaseVersion || '1.0.0';
    const docName = rawDocName || `Release Notes v${version}`;
    const ctx = this.newDocCtx('Release Notes', docName, meta);

    // Title & Aligned Metadata Block
    this.docArtifactHeading(ctx);
    const { doc, margin } = ctx;
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(10.5);
    doc.setTextColor(30, 41, 59);
    doc.text('Generated and Approved by Newgen', margin, ctx.getY() + 4);
    ctx.addY(18);
    this.docMetaBlock(ctx, [
      { label: 'Project Name',    value: meta?.project || data?.productName || '-' },
      { label: 'Release Version', value: version },
      { label: 'Release Date',    value: data?.releaseDate || new Date().toLocaleDateString() },
      { label: 'Generated On',    value: new Date().toLocaleDateString() }
    ]);
    this.docRule(ctx);

    let secIdx = 1;

    // 1. Release Overview
    const summary = data?.summary || data?.executiveSummary || data?.overview || '';
    if (summary) {
      this.docSection(ctx, `${secIdx++}. Release Overview`);
      this.docParagraph(ctx, summary);
    }

    // 2. New Features (Spec 38: Title & Description per feature)
    const newFeatures: any[] = Array.isArray(data?.newFeatures) ? data.newFeatures : [];
    if (newFeatures.length > 0) {
      this.docSection(ctx, `${secIdx++}. New Features`);
      newFeatures.forEach((feat: any, fi: number) => {
        if (typeof feat === 'object' && feat !== null) {
          const fTitle = feat.title || feat.name || `Feature ${fi + 1}`;
          const fDesc = feat.description || feat.desc || '';
          this.docSubSection(ctx, `${fi + 1}. ${fTitle}`);
          if (fDesc) this.docParagraph(ctx, `Description: ${fDesc}`, 12);
        } else {
          this.docNumbered(ctx, fi + 1, this.toText(feat));
        }
      });
      ctx.addY(6);
    }

    // 3. Enhancements & Improvements
    const improvements: any[] = Array.isArray(data?.improvements) ? data.improvements : [];
    if (improvements.length > 0) {
      this.docSection(ctx, `${secIdx++}. Enhancements & Improvements`);
      improvements.forEach((imp: any) => this.docBullet(ctx, this.toText(imp)));
      ctx.addY(6);
    }

    // 4. Bug Fixes
    const bugFixes: any[] = Array.isArray(data?.bugFixes) ? data.bugFixes : [];
    if (bugFixes.length > 0) {
      this.docSection(ctx, `${secIdx++}. Bug Fixes`);
      bugFixes.forEach((bf: any) => this.docBullet(ctx, this.toText(bf)));
      ctx.addY(6);
    }

    // 5. Breaking Changes
    const breakingChanges: any[] = Array.isArray(data?.breakingChanges) ? data.breakingChanges : [];
    if (breakingChanges.length > 0) {
      this.docSection(ctx, `${secIdx++}. Breaking Changes`);
      breakingChanges.forEach((bc: any) => this.docBullet(ctx, this.toText(bc)));
      ctx.addY(6);
    }

    // 6. Known Issues & Workarounds
    const knownIssues: any[] = Array.isArray(data?.knownIssues) ? data.knownIssues : [];
    if (knownIssues.length > 0) {
      this.docSection(ctx, `${secIdx++}. Known Issues & Workarounds`);
      knownIssues.forEach((ki: any) => this.docBullet(ctx, this.toText(ki)));
      ctx.addY(6);
    }

    // 7. Dependencies & Environmental Impact
    const impact = data?.impact || data?.dependencies || '';
    if (impact) {
      this.docSection(ctx, `${secIdx++}. System Impact & Dependencies`);
      if (Array.isArray(impact)) {
        impact.forEach((item: any) => this.docBullet(ctx, this.toText(item)));
      } else {
        this.docParagraph(ctx, String(impact));
      }
      ctx.addY(6);
    }

    // Technical Notes, Deployment, and Migration Guidance
    if (data?.technicalNotes) {
      this.docSection(ctx, `${secIdx++}. Technical Notes & Operational Guidance`);
      this.docParagraph(ctx, String(data.technicalNotes));
      ctx.addY(6);
    }

    // 8. Deployment & Migration Notes
    const deploySteps: any[] = Array.isArray(data?.deploymentNotes)
      ? data.deploymentNotes
      : (data?.migrationSteps ? (Array.isArray(data.migrationSteps) ? data.migrationSteps : [data.migrationSteps]) : []);
    if (deploySteps.length > 0) {
      this.docSection(ctx, `${secIdx++}. Deployment & Migration Notes`);
      deploySteps.forEach((ds: any, di: number) => this.docNumbered(ctx, di + 1, this.toText(ds)));
      ctx.addY(6);
    }

    this.docApplyHeaderAndFooters(ctx);
    return { ctx, filename: this.buildPdfFilename('Release_Notes', meta, data?.version || version) };
  }

  generateReleaseNotePdfBlob(data: any, baseFilename = 'release-notes', meta?: any): Blob | null {
    const built = this.buildReleaseNoteDoc(data, baseFilename, meta);
    return built ? built.ctx.doc.output('blob') : null;
  }

  downloadReleaseNotePdf(data: any, baseFilename = 'release-notes', meta?: any): void {
    const built = this.buildReleaseNoteDoc(data, baseFilename, meta);
    if (!built) {
      alert('No release notes data available to export.');
      return;
    }
    built.ctx.doc.save(built.filename);
  }

  // ============================================================
  // 8. AUDIT HISTORY PDF (Spec 39: Client-ready, No raw objects)
  // ============================================================
  downloadAuditHistoryPdf(logs: any[], meta?: any): void {
    if (!logs || logs.length === 0) {
      alert('No audit logs available to export.');
      return;
    }

    const ctx = this.newDocCtx('Audit History', 'Audit & History Report', meta);

    // Title & Aligned Metadata Block (Spec 7 & 39)
    this.docTitle(ctx, 'AUDIT & HISTORY REPORT');
    this.docMetaBlock(ctx, [
      { label: 'Project Scope',   value: meta?.projectFilter && meta.projectFilter !== 'ALL' ? meta.projectFilter : 'All Projects' },
      { label: 'User Filter',     value: meta?.userFilter && meta.userFilter !== 'ALL' ? meta.userFilter : 'All Users' },
      { label: 'Exported By',     value: meta?.currentUser || 'System' },
      { label: 'Total Logs',      value: String(logs.length) },
      { label: 'Generated On',    value: new Date().toLocaleString() }
    ]);
    this.docRule(ctx);

    // Section 1: Executive Overview
    this.docSection(ctx, '1. Executive Overview');
    const successCount = logs.filter(l => ['SUCCESS', 'ACCEPTED', 'COMPLETED'].includes((l.status || '').toUpperCase())).length;
    const failCount = logs.length - successCount;
    this.docParagraph(ctx, `This document provides an official audit trail of user activities, AI generations, and feature executions across the platform. Total recorded transactions: ${logs.length}. Completed/Accepted: ${successCount}. Non-success/Failed: ${failCount}.`);

    // Section 2: Audit Activity Summary Table (Spec 39: S.No, Date, User, Module, Action/Feature, Status)
    this.docSection(ctx, '2. Activity Summary Matrix');
    const tableRows = logs.map((log: any, idx: number) => {
      const d = log.timestamp ? new Date(log.timestamp) : null;
      const dateStr = d ? `${d.toLocaleDateString()} ${d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}` : '—';
      const projDoc = log.projectName ? `${log.projectName}${log.documentName ? ' / ' + log.documentName : ''}` : (log.documentName || '—');
      return {
        sno: String(idx + 1),
        date: dateStr,
        user: log.userName || 'System',
        module: log.feature || 'General',
        project: projDoc,
        status: log.status || 'COMPLETED',
        execTime: `${log.executionTimeMs || 0} ms`
      };
    });

    this.docTable(ctx, [
      { header: 'S.No', key: 'sno', width: 30, align: 'center' },
      { header: 'Date & Time', key: 'date', width: 80, align: 'center' },
      { header: 'User', key: 'user', width: 55, align: 'center' },
      { header: 'Module / Feature', key: 'module', width: 85 },
      { header: 'Project / Document', key: 'project', width: 120 },
      { header: 'Status', key: 'status', width: 60, align: 'center' },
      { header: 'Exec Time', key: 'execTime', width: 50, align: 'center' }
    ], tableRows);

    // Section 3: Detailed Activity Logs (Spec 39: Human-readable, NO raw dumps)
    this.docSection(ctx, '3. Detailed Transaction Logs');
    logs.forEach((log: any, idx: number) => {
      const d = log.timestamp ? new Date(log.timestamp).toLocaleString() : 'N/A';
      const feature = log.feature || 'Feature Execution';

      this.docSubSection(ctx, `3.${idx + 1}  ${feature} — ${d}`);
      this.docInlineLabel(ctx, 'User', log.userName || 'System');
      this.docInlineLabel(ctx, 'Status', log.status || 'COMPLETED');
      this.docInlineLabel(ctx, 'Execution Duration', `${log.executionTimeMs || 0} ms`);
      if (log.projectName) this.docInlineLabel(ctx, 'Project', log.projectName);
      if (log.documentName) this.docInlineLabel(ctx, 'Document', `${log.documentName} (v${log.documentVersion || '1'})`);

      // Input Prompt
      if (log.input) {
        this.docLabelLine(ctx, 'Input Context / Query');
        this.docParagraph(ctx, this.cleanMarkdown(log.input), 10);
      }

      // Generated AI Result (Formatted cleanly, never raw backend dump!)
      if (log.parsedOutput) {
        this.docLabelLine(ctx, 'AI Generation Summary');
        const po = log.parsedOutput;
        if (po.summary) this.docParagraph(ctx, `Summary: ${this.cleanMarkdown(po.summary)}`, 10);
        if (po.userStory) this.docParagraph(ctx, `User Story: ${this.cleanMarkdown(po.userStory)}`, 10);
        if (po.probableRootCause) this.docParagraph(ctx, `Probable Root Cause: ${this.cleanMarkdown(po.probableRootCause)}`, 10);
        if (po.suggestedFix) this.docCodeBlock(ctx, po.suggestedFix, 'Suggested Fix');
        if (Array.isArray(po)) {
          this.docParagraph(ctx, `Generated Array Output: ${po.length} structured records produced.`, 10);
        }
      } else if (log.output) {
        this.docLabelLine(ctx, 'Output Details');
        this.docParagraph(ctx, this.cleanMarkdown(log.output).substring(0, 350) + '...', 10);
      }

      if (idx < logs.length - 1) {
        ctx.addY(6);
        this.docRule(ctx);
      }
    });

    this.docApplyHeaderAndFooters(ctx);
    ctx.doc.save(`Audit_History_Report_${this.getTimestampSuffix()}.pdf`);
  }

  // ==========================================
  // UNIFIED DOCUMENT PDF ROUTER
  // ==========================================
  generateDocumentPdf(
    type: 'USER_STORY' | 'FUNCTIONAL_DESIGN' | 'TECHNICAL_DESIGN' | 'REQUIREMENT' | 'TEST_CASE' | 'DEFECT' | 'RELEASE_NOTE' | 'AUDIT_HISTORY',
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
      this.downloadAllRequirementsPdf(items, 'requirements', meta);
    } else if (type === 'TEST_CASE') {
      const items = Array.isArray(data) ? data : (data.items || [data]);
      this.downloadTestCasePdf(items, meta);
    } else if (type === 'DEFECT') {
      this.downloadDefectPdf(data, 'defect-triage', meta);
    } else if (type === 'RELEASE_NOTE') {
      this.downloadReleaseNotePdf(data, 'release-notes', meta);
    } else if (type === 'AUDIT_HISTORY') {
      const logs = Array.isArray(data) ? data : (data.logs || [data]);
      this.downloadAuditHistoryPdf(logs, meta);
    }
  }

  // ============================================================
  // PRIVATE UTILITIES
  // ============================================================

  private sanitizeFilename(name: string): string {
    if (!name) return 'document';
    return name.replace(/[^a-zA-Z0-9_\-]/g, '_').substring(0, 50);
  }

  private buildPdfFilename(outputType: string, meta: any, fallbackDocument: string): string {
    const parts = [meta?.project, outputType, meta?.documentName || fallbackDocument, meta?.version]
      .filter((part) => part !== null && part !== undefined && String(part).trim())
      .map((part) => this.sanitizeFilename(String(part)));
    return `${parts.length ? parts.join('_') : this.sanitizeFilename(outputType)}.pdf`;
  }

  private toText(item: any): string {
    if (!item && item !== 0) return '';
    if (typeof item === 'string') return item;
    if (typeof item === 'number' || typeof item === 'boolean') return String(item);
    return item.text || item.scenario || item.rule || item.description || item.name ||
           item.handling || item.change || item.purpose || item.note ||
           item.consideration || item.dependency || JSON.stringify(item);
  }

  private formatItemSource(item: any): string {
    if (!item || typeof item === 'string') return '';
    const parts: string[] = [];
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
