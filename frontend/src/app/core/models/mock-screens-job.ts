export type MockScreensJobStatus =
  | 'QUEUED'
  | 'PROCESSING'
  | 'READY_FOR_PDF'
  | 'PDF_GENERATING'
  | 'COMPLETED'
  | 'FAILED';

export interface MockScreensJobRequest {
  projectId: number;
  brdId: number;
}

export interface MockScreensPdfResponse {
  pdfArtifactId: number | null;
  pdfFileName: string | null;
  pdfContentType: string | null;
  pdfSizeBytes: number | null;
  pdfCreatedAt: string | null;
  pdfPreviewUrl: string | null;
  pdfDownloadUrl: string | null;
}

export interface MockScreensJobResponse extends MockScreensPdfResponse {
  jobId: string;
  projectId: number;
  brdId: number;
  status: MockScreensJobStatus;
  errorCode: string | null;
  errorMessage: string | null;
  failedSequence: number | null;
  statusUrl: string;
  createdAt: string;
  updatedAt: string;
}