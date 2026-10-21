import '@angular/compiler';
import { describe, expect, it, vi } from 'vitest';
import { of, throwError } from 'rxjs';
import { HttpClient } from '@angular/common/http';
import { ApiService } from '../core/api';
import { MockScreens } from './mock-screens';

function createComponent(apiOverrides: Partial<ApiService> = {}) {
  const api = {
    getProjects: vi.fn(() => of({ success: true, data: [] })),
    getProjectDocuments: vi.fn(() => of({ success: true, data: [] })),
    generateMockScreens: vi.fn(() => of({ success: true, data: { jobId: 'JOB-1', status: 'QUEUED' } })),
    getMockScreenJob: vi.fn(() => of({ success: true, data: { status: 'QUEUED', screens: [] } })),
    ...apiOverrides
  } as unknown as ApiService;
  const cdr = { markForCheck: vi.fn() };
  return { component: new MockScreens(api, cdr as any), api };
}

describe('MockScreens project-scoped BRD selection', () => {
  it('only accepts completed BRD documents and PDFs', () => {
    const { component } = createComponent();

    expect(component.isEligibleBrd({ fileName: 'requirements.docx', fileType: 'BRD', status: 'COMPLETED' })).toBe(true);
    expect(component.isEligibleBrd({ fileName: 'spec.pdf', fileType: 'application/pdf', status: 'COMPLETED' })).toBe(true);
    expect(component.isEligibleBrd({ fileName: 'requirements.pdf', status: 'PROCESSING' })).toBe(false);
    expect(component.isEligibleBrd({ fileName: 'project.zip', fileType: 'BRD', status: 'COMPLETED' })).toBe(false);
    expect(component.isEligibleBrd({ fileName: 'notes.docx', fileType: 'OTHER', status: 'COMPLETED' })).toBe(false);
  });

  it('loads only eligible documents for the selected project and clears the prior BRD', () => {
    const documents = [
      { id: 10, fileName: 'signed-brd.pdf', fileType: 'PDF', status: 'COMPLETED' },
      { id: 11, fileName: 'pending.pdf', fileType: 'PDF', status: 'PROCESSING' },
      { id: 12, fileName: 'source.zip', fileType: 'ZIP', status: 'COMPLETED' }
    ];
    const { component, api } = createComponent({
      getProjectDocuments: vi.fn(() => of({ success: true, message: '', data: documents }))
    });

    component.projects = [{ id: 7, projectName: 'Claims Portal' }];
    component.selectedDocumentId = 99;
    component.selectedDocument = { id: 99, fileName: 'old.pdf' };
    component.onProjectChange(7);

    expect(api.getProjectDocuments).toHaveBeenCalledWith(7);
    expect(component.selectedDocumentId).toBeNull();
    expect(component.selectedDocument).toBeNull();
    expect(component.brdDocuments.map(document => document.id)).toEqual([10]);
  });

  it('surfaces project request failures and validates incomplete selections', () => {
    const { component, api } = createComponent({
      getProjects: vi.fn(() => throwError(() => ({ error: { message: 'Service unavailable' } })))
    });

    component.loadProjects();
    expect(component.projectsError).toBe('Service unavailable');

    component.startGeneration();
    expect(component.selectionError).toContain('Select a project');
    expect(api.generateMockScreens).not.toHaveBeenCalled();
  });

  it('submits the selected document ID and starts polling', () => {
    const { component, api } = createComponent();
    component.selectedProjectId = 7;
    component.selectedProject = { id: 7, projectName: 'Claims Portal' };
    component.selectedDocumentId = 10;
    component.selectedDocument = { id: 10, fileName: 'signed-brd.pdf' };

    component.startGeneration();

    expect(api.generateMockScreens).toHaveBeenCalledWith(10);
    expect(component.currentJobId).toBe('JOB-1');
    expect(api.getMockScreenJob).toHaveBeenCalledWith('JOB-1');
    component.stopPolling();
  });
});

describe('Mock Screens Pipeline A API', () => {
  it('uses the active generate, polling, screens, image, retry, history, and PDF endpoints', () => {
    const http = {
      get: vi.fn((_url: string, _options?: unknown) => of(new Blob())),
      post: vi.fn((_url: string, _body: unknown, _options?: unknown) => of({}))
    };
    const api = new ApiService(http as unknown as HttpClient);
    api.baseUrl = 'http://localhost:8080/api';

    api.generateMockScreens(42);
    api.getMockScreenJob('JOB-42');
    api.getMockScreenScreens('JOB-42');
    expect(api.getMockScreenImageUrl(7)).toBe('http://localhost:8080/api/mock-screens/7/image');
    api.retryMockScreen(7);
    api.getMockScreenHistory();
    api.downloadMockScreenPdf('JOB-42');

    expect(http.post.mock.calls.map(([url]) => url)).toEqual([
      'http://localhost:8080/api/mock-screens/generate',
      'http://localhost:8080/api/mock-screens/7/retry'
    ]);
    expect(http.get.mock.calls.map(([url]) => url)).toEqual([
      'http://localhost:8080/api/mock-screens/jobs/JOB-42',
      'http://localhost:8080/api/mock-screens/jobs/JOB-42/screens',
      'http://localhost:8080/api/mock-screens/history',
      'http://localhost:8080/api/mock-screens/jobs/JOB-42/pdf'
    ]);
    expect(http.get.mock.calls[3][1]).toEqual({ responseType: 'blob' });
    expect('createMockScreensJob' in api).toBe(false);
  });

  it('finishes polling when Pipeline A reports a completed job', () => {
    const { component, api } = createComponent({
      getMockScreenJob: vi.fn(() => of({
        success: true,
        data: { jobId: 'JOB-1', status: 'COMPLETED', screens: [] }
      }))
    });
    component.startingGeneration = true;

    component.pollJobStatus('JOB-1');

    expect(api.getMockScreenJob).toHaveBeenCalledWith('JOB-1');
    expect(component.showResultModal).toBe(true);
    expect(component.startingGeneration).toBe(false);
  });

  it('retries a failed screen and refreshes its Pipeline A job', () => {
    const { component, api } = createComponent({
      retryMockScreen: vi.fn(() => of({
        success: true,
        data: { status: 'COMPLETED', imageUrl: '/api/mock-screens/7/image' }
      }))
    });
    component.currentJobId = 'JOB-1';
    const screen = { id: 7, sequence: 1, status: 'FAILED', errorMessage: 'Render failed' };

    component.retryScreen(screen);

    expect(api.retryMockScreen).toHaveBeenCalledWith(7);
    expect(screen.status).toBe('COMPLETED');
    expect(screen.imageUrl).toBe('/api/mock-screens/7/image');
    expect(api.getMockScreenJob).toHaveBeenCalledWith('JOB-1');
  });
});
