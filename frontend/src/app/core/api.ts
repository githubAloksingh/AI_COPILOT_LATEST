import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  message: string;
  error?: {
    code: string;
    message: string;
  };
}

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private baseUrl = this.resolveBaseUrl();

  private resolveBaseUrl(): string {
    if (typeof window !== 'undefined' && localStorage.getItem('BACKEND_URL')) {
      return localStorage.getItem('BACKEND_URL')!;
    }
    return (environment && environment.apiUrl) ? environment.apiUrl : 'http://localhost:8080/api';
  }

  constructor(private http: HttpClient) {}


  // Dashboard
  getStats(): Observable<ApiResponse<any>> {
    return this.http.get<ApiResponse<any>>(`${this.baseUrl}/dashboard/stats`);
  }

  getRecentActivity(): Observable<ApiResponse<any[]>> {
    return this.http.get<ApiResponse<any[]>>(`${this.baseUrl}/dashboard/recent-activity`);
  }

  // Documents
  getDocuments(): Observable<ApiResponse<any[]>> {
    return this.http.get<ApiResponse<any[]>>(`${this.baseUrl}/documents`);
  }

  uploadDocument(file: File): Observable<ApiResponse<any>> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<ApiResponse<any>>(`${this.baseUrl}/documents`, formData);
  }

  deleteDocument(id: number): Observable<ApiResponse<void>> {
    return this.http.delete<ApiResponse<void>>(`${this.baseUrl}/documents/${id}`);
  }

  // AI Copilot features - Preview Generation
  generateRequirement(data: any): Observable<ApiResponse<any>> {
    return this.http.post<ApiResponse<any>>(`${this.baseUrl}/copilot/requirements`, data);
  }

  acceptRequirement(data: any): Observable<ApiResponse<any>> {
    return this.http.post<ApiResponse<any>>(`${this.baseUrl}/copilot/requirements/accept`, data);
  }

  /** Bulk accept — saves all N requirements as separate DB rows */
  acceptAllRequirements(data: any): Observable<ApiResponse<any>> {
    return this.http.post<ApiResponse<any>>(`${this.baseUrl}/copilot/requirements/accept-all`, data);
  }

  generateTestCases(data: any): Observable<ApiResponse<any>> {
    return this.http.post<ApiResponse<any>>(`${this.baseUrl}/copilot/testcases`, data);
  }

  acceptTestCases(data: any): Observable<ApiResponse<any>> {
    return this.http.post<ApiResponse<any>>(`${this.baseUrl}/copilot/testcases/accept`, data);
  }

  uploadDefectFile(file: File): Observable<ApiResponse<any>> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<ApiResponse<any>>(`${this.baseUrl}/copilot/defects/upload-triage`, formData);
  }

  analyzeDefect(data: any): Observable<ApiResponse<any>> {
    return this.http.post<ApiResponse<any>>(`${this.baseUrl}/copilot/defects/triage`, data);
  }

  acceptDefect(data: any): Observable<ApiResponse<any>> {
    return this.http.post<ApiResponse<any>>(`${this.baseUrl}/copilot/defects/accept`, data);
  }

  generateReleaseNotes(data: any): Observable<ApiResponse<any>> {
    return this.http.post<ApiResponse<any>>(`${this.baseUrl}/copilot/release-notes`, data);
  }

  acceptReleaseNotes(data: any): Observable<ApiResponse<any>> {
    return this.http.post<ApiResponse<any>>(`${this.baseUrl}/copilot/release-notes/accept`, data);
  }

  generateDailyStatus(data: any): Observable<ApiResponse<any>> {
    return this.http.post<ApiResponse<any>>(`${this.baseUrl}/copilot/status`, data);
  }

  // Audit
  getAuditLogs(): Observable<ApiResponse<any[]>> {
    return this.http.get<ApiResponse<any[]>>(`${this.baseUrl}/audit-logs`);
  }
}

