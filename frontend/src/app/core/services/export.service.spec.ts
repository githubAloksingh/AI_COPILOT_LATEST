import { describe, it, expect, beforeEach, vi } from 'vitest';
import { jsPDF } from 'jspdf';
import { ExportService } from './export.service';

describe('ExportService - Master PDF Specification Compliance', () => {
  let service: ExportService;

  beforeEach(() => {
    service = new ExportService();
  });

  it('1. cleanMarkdown removes raw markdown markers and emojis', () => {
    const raw = '### Heading 3 with **bold** and *italic* and `code` and 🚀 rocket';
    const cleaned = service.cleanMarkdown(raw);
    expect(cleaned).not.toContain('###');
    expect(cleaned).not.toContain('**');
    expect(cleaned).not.toContain('*');
    expect(cleaned).not.toContain('`');
    expect(cleaned).not.toContain('🚀');
    expect(cleaned).toBe('Heading 3 with bold and italic and code and  rocket');
  });

  it('2. removes grounding metadata from exported user story source tags', () => {
    const result = (service as any).formatItemSource({ grounding: 'DERIVED', source: ['BRD §4.2'] });

    expect(result).toBe('[Source: BRD §4.2]');
    expect(result).not.toContain('Grounding');
  });

  it('3. generates User Story PDF without error', () => {
    const mockStories = [
      {
        userStoryId: 'US-001',
        title: 'Project Query Processing',
        userStory: 'As a developer, I want to query the system so that I receive AI responses.',
        acceptanceCriteria: ['AC-001: Accept query', 'AC-002: Return response'],
        businessRules: ['BR-001: Query must not be empty'],
        dependencies: ['Core Service']
      }
    ];

    expect(() => {
      service.downloadUserStoryPdf(mockStories, { project: 'Test Project', work: 'US', version: '1.0' });
    }).not.toThrow();
  });

  it('3. generates Functional Design PDF without error', () => {
    const mockFd = {
      title: 'Functional Specification',
      objective: 'Define system functional workflows.',
      scope: ['User authentication', 'Document upload'],
      actors: [{ name: 'Admin', description: 'System administrator' }],
      mainFlow: [{ step: 1, actor: 'User', action: 'Login', systemResponse: 'Dashboard loaded' }],
      validations: [{ field: 'Email', rule: 'Must be valid format', grounding: 'RFC 5322' }]
    };

    expect(() => {
      service.downloadFunctionalDesignPdf(mockFd, { project: 'Test Project' });
    }).not.toThrow();
  });

  it('4. generates Technical Design PDF with Flowchart and full tables without error', () => {
    const mockTd = {
      title: 'Technical Design Specification',
      objective: 'Define system technical architecture and data flow.',
      architectureFlow: [
        { step: 1, component: 'Frontend', action: 'Submit query to API gateway' },
        { step: 2, component: 'Backend', action: 'Process request and query vector DB' },
        { step: 3, component: 'AI Model', action: 'Generate response and store in database' }
      ],
      components: [
        {
          name: 'Feed Ingestion Component',
          responsibility: 'Receive and process incoming daily data feeds.',
          keyLogic: [
            'Parse incoming feed file.',
            'For each account/record in the feed:',
            '- If account balance is negative -> create new Overdraft record.',
            '◦ If account has un-invested cash -> create new Cash record.'
          ]
        }
      ],
      apis: [
        { name: 'Upload BRD', method: 'POST', endpoint: '/api/documents/upload', purpose: 'Upload BRD file' }
      ],
      dataModel: [
        { entity: 'Document', fields: [{ name: 'id', type: 'UUID', required: true, description: 'PK' }] }
      ],
      dataFlow: [
        { step: 1, source: 'Upstream Feed', target: 'Feed Handler', action: 'Transmit daily settlement file', payload: 'CSV Record Feed' }
      ],
      validationRules: {
        frontend: [{ field: 'accountNumber', rule: 'Must be 10 numeric digits', errorMsg: 'Invalid Account Number' }],
        backend: [{ field: 'amount', rule: 'Must be non-negative float', errorMsg: 'Invalid Amount' }],
        database: [{ constraint: 'UQ_ACCOUNT_NUM', description: 'Unique index on account number' }]
      },
      errorHandling: [
        { scenario: 'Feed Timeout', whereItOccurs: 'Ingestion Layer', handling: 'Retry with backoff', responseReturned: 'HTTP 504', userExperience: 'Alert banner' }
      ],
      edgeCases: [
        { scenario: 'Negative Cash Balance with Missing Profile', impact: 'High', handling: 'Quarantine record to Exception Queue' }
      ],
      securityConsiderations: [
        { id: 'SEC-01', consideration: 'SSO Authentication', detail: 'SAML 2.0 / OAuth2 with JWT validation', source: 'Enterprise Security' }
      ],
      hardConstraints: [
        { id: 'C-01', constraint: 'Aging must be calculated strictly in calendar days', source: 'BRD Section 4' }
      ],
      openQuestions: [
        { id: 'OQ-01', question: 'Confirm feed delivery mechanism', impact: 'Ingestion Architecture', source: 'BRD Review' }
      ]
    };

    expect(() => {
      service.downloadTechnicalDesignPdf(mockTd, { project: 'Test Project' });
    }).not.toThrow();
  });

  it('5. generates Requirements PDF without error', () => {
    const mockReq = {
      requirementId: 'REQ-001',
      title: 'Upload Document',
      summary: 'Users must be able to upload documents.',
      acceptanceCriteria: ['Upload succeeds', 'Validation passes']
    };

    expect(() => {
      service.downloadRequirementPdf(mockReq, 'req-001', { project: 'Test Project' });
    }).not.toThrow();
  });

  it('6. generates Test Case PDF with metrics & tables without error', () => {
    const mockTc = [
      {
        tcId: 'TC-001',
        scenario: 'Verify valid login credentials',
        type: 'POSITIVE',
        priority: 'HIGH',
        steps: ['Open login page', 'Enter credentials', 'Click submit'],
        expectedResult: 'Dashboard is displayed'
      }
    ];

    expect(() => {
      service.downloadTestCasePdf(mockTc, { project: 'Test Project' });
    }).not.toThrow();
  });

  it('7. generates Defect Triage PDF with code blocks without error', () => {
    const mockDefect = {
      defects: [
        {
          defectId: 'DEF-001',
          title: 'Null pointer in parser',
          severity: 'HIGH',
          priority: 'P1',
          status: 'OPEN',
          rootCause: 'Unchecked null value in document payload',
          suggestedFix: 'if (doc != null) { return doc.getName(); }',
          evidence: 'NullPointerException at DocumentParser.java:42'
        }
      ]
    };

    expect(() => {
      service.downloadDefectPdf(mockDefect, 'defect-triage', { project: 'Test Project' });
    }).not.toThrow();
  });

  it('8. generates Release Notes PDF without error and includes the fixed approval text', () => {
    const mockRn = {
      version: '2.0.0',
      summary: 'Major release containing PDF presentation overhaul.',
      newFeatures: [
        { title: 'PDF Export', description: 'Export client-ready documentation PDFs' }
      ],
      bugFixes: ['Fixed text clipping in wide tables']
    };

    const originalNewDocCtx = (service as any).newDocCtx.bind(service);
    const textSpy = vi.fn();
    (service as any).newDocCtx = (...args: any[]) => {
      const ctx = originalNewDocCtx(...args);
      const originalText = ctx.doc.text.bind(ctx.doc);
      ctx.doc.text = (...callArgs: any[]) => {
        textSpy(...callArgs);
        return originalText(...callArgs);
      };
      return ctx;
    };

    expect(() => {
      service.downloadReleaseNotePdf(mockRn, 'release-notes', { project: 'Test Project' });
    }).not.toThrow();

    expect(textSpy.mock.calls.some(call => call.some(arg => typeof arg === 'string' && arg.includes('Generated and Approved by Newgen')))).toBe(true);
    (service as any).newDocCtx = originalNewDocCtx;
  });

  it('9. generates Audit History PDF without raw backend objects', () => {
    const mockLogs = [
      {
        timestamp: '2026-09-14T18:30:00Z',
        userName: 'AdminUser',
        feature: 'User Story Generation',
        projectName: 'AI Work Copilot',
        documentName: 'BRD1.pdf',
        documentVersion: '1.0',
        status: 'SUCCESS',
        executionTimeMs: 1420,
        input: 'Generate user story for user authentication',
        parsedOutput: {
          summary: 'User authentication specification',
          userStory: 'As a user, I want to authenticate...',
          acceptanceCriteria: ['Valid login succeeds']
        }
      }
    ];

    expect(() => {
      service.downloadAuditHistoryPdf(mockLogs, {
        projectFilter: 'AI Work Copilot',
        userFilter: 'AdminUser',
        currentUser: 'AdminUser'
      });
    }).not.toThrow();
  });
});
