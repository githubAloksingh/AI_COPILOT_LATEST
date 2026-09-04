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

  currentUser = 'User A';
  currentRole: 'ADMIN' | 'USER' = 'USER';

  getCurrentUser(): string {
    if (typeof window !== 'undefined' && localStorage.getItem('CURRENT_USER')) {
      return localStorage.getItem('CURRENT_USER')!;
    }
    return this.currentUser;
  }

  getCurrentRole(): 'ADMIN' | 'USER' {
    if (typeof window !== 'undefined' && localStorage.getItem('CURRENT_ROLE')) {
      return localStorage.getItem('CURRENT_ROLE') as any;
    }
    return this.currentRole;
  }

  setCurrentSession(user: string, role: 'ADMIN' | 'USER'): void {
    this.currentUser = user;
    this.currentRole = role;
    if (typeof window !== 'undefined') {
      localStorage.setItem('CURRENT_USER', user);
      localStorage.setItem('CURRENT_ROLE', role);
    }
  }

  getAuthHeaders(): { [header: string]: string } {
    return {
      'X-User-Name': this.getCurrentUser(),
      'X-User-Role': this.getCurrentRole()
    };
  }

  constructor(private http: HttpClient) {}


  // Dashboard
  getStats(): Observable<ApiResponse<any>> {
    return this.http.get<ApiResponse<any>>(`${this.baseUrl}/dashboard/stats`);
  }

  getRecentActivity(): Observable<ApiResponse<any[]>> {
    return this.http.get<ApiResponse<any[]>>(`${this.baseUrl}/dashboard/recent-activity`);
  }

  // Projects
  getProjects(): Observable<ApiResponse<any[]>> {
    return this.http.get<ApiResponse<any[]>>(`${this.baseUrl}/projects`);
  }

  getProject(id: number): Observable<ApiResponse<any>> {
    return this.http.get<ApiResponse<any>>(`${this.baseUrl}/projects/${id}`);
  }

  createProject(data: any): Observable<ApiResponse<any>> {
    return this.http.post<ApiResponse<any>>(`${this.baseUrl}/projects`, data);
  }

  deleteProject(id: number): Observable<ApiResponse<void>> {
    return this.http.delete<ApiResponse<void>>(`${this.baseUrl}/projects/${id}`);
  }

  // Documents
  getDocuments(): Observable<ApiResponse<any[]>> {
    return this.http.get<ApiResponse<any[]>>(`${this.baseUrl}/documents`);
  }

  getProjectDocuments(projectId: number): Observable<ApiResponse<any[]>> {
    return this.http.get<ApiResponse<any[]>>(`${this.baseUrl}/projects/${projectId}/documents`);
  }

  uploadDocument(file: File): Observable<ApiResponse<any>> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<ApiResponse<any>>(`${this.baseUrl}/documents`, formData);
  }

  uploadProjectDocument(projectId: number, file: File, title?: string, customType?: string, uploadedBy = 'System', version = 'v1'): Observable<ApiResponse<any>> {
    const formData = new FormData();
    formData.append('file', file);
    if (title) formData.append('title', title);
    if (customType) formData.append('customType', customType);
    formData.append('uploadedBy', uploadedBy);
    formData.append('version', version);
    return this.http.post<ApiResponse<any>>(`${this.baseUrl}/projects/${projectId}/documents`, formData);
  }

  getDocumentContent(id: number): Observable<ApiResponse<string>> {
    return this.http.get<ApiResponse<string>>(`${this.baseUrl}/documents/${id}/content`);
  }

  deleteDocument(id: number): Observable<ApiResponse<void>> {
    return this.http.delete<ApiResponse<void>>(`${this.baseUrl}/documents/${id}`);
  }

  // AI Copilot features - Preview Generation
  generateRequirement(data: any): Observable<ApiResponse<any>> {
    return this.http.post<ApiResponse<any>>(`${this.baseUrl}/copilot/requirements`, data);
  }

  generateUserStory(data: any): Observable<ApiResponse<any>> {
    return this.http.post<ApiResponse<any>>(`${this.baseUrl}/copilot/requirements/user-story`, data);
  }

  generateFunctionalDesign(data: any): Observable<ApiResponse<any>> {
    return this.http.post<ApiResponse<any>>(`${this.baseUrl}/copilot/requirements/functional-design`, data);
  }

  generateTechnicalDesign(data: any): Observable<ApiResponse<any>> {
    return this.http.post<ApiResponse<any>>(`${this.baseUrl}/copilot/requirements/technical-design`, data);
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
  getAuditLogs(userFilter?: string): Observable<ApiResponse<any[]>> {
    let url = `${this.baseUrl}/audit-logs`;
    if (userFilter && userFilter !== 'ALL') {
      url += `?user=${encodeURIComponent(userFilter)}`;
    }
    return this.http.get<ApiResponse<any[]>>(url, { headers: this.getAuthHeaders() });
  }

  recordAuditLog(logData: any): Observable<ApiResponse<any>> {
    return this.http.post<ApiResponse<any>>(`${this.baseUrl}/audit-logs`, logData, { headers: this.getAuthHeaders() });
  }
}

