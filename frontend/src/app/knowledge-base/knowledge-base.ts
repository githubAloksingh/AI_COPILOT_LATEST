import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ApiService } from '../core/api';

@Component({
  selector: 'app-knowledge-base',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './knowledge-base.html',
  styleUrls: ['./knowledge-base.scss']
})
export class KnowledgeBase implements OnInit {
  projects: any[] = [];
  loading = true;
  error = '';
  submitting = false;

  // Create Project Modal state
  showCreateModal = false;
  newProject = {
    projectName: '',
    department: '',
    projectOwner: '',
    status: 'ACTIVE',
    createdBy: 'System'
  };
  formError = '';

  constructor(
    private api: ApiService,
    private router: Router,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit() {
    this.loadProjects();
  }

  loadProjects() {
    this.loading = true;
    this.error = '';
    this.cdr.markForCheck();

    this.api.getProjects().subscribe({
      next: (res) => {
        if (res.success) {
          this.projects = res.data || [];
        } else {
          this.error = res.message || 'Failed to load projects';
        }
        this.loading = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.loading = false;
        this.error = 'Failed to load projects. Please try again.';
        this.cdr.markForCheck();
      }
    });
  }

  openCreateModal() {
    this.newProject = {
      projectName: '',
      department: '',
      projectOwner: '',
      status: 'ACTIVE',
      createdBy: 'System'
    };
    this.formError = '';
    this.showCreateModal = true;
  }

  closeCreateModal() {
    this.showCreateModal = false;
    this.formError = '';
  }

  createProject() {
    if (!this.newProject.projectName.trim()) {
      this.formError = 'Project Name is required.';
      return;
    }
    if (!this.newProject.department.trim()) {
      this.formError = 'Department is required.';
      return;
    }
    if (!this.newProject.projectOwner.trim()) {
      this.formError = 'Project Owner is required.';
      return;
    }

    this.submitting = true;
    this.formError = '';
    this.cdr.markForCheck();

    this.api.createProject(this.newProject).subscribe({
      next: (res) => {
        if (res.success) {
          this.closeCreateModal();
          this.loadProjects();
        } else {
          this.formError = res.message || 'Failed to create project';
        }
        this.submitting = false;
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.formError = err.error?.message || 'Failed to create project.';
        this.submitting = false;
        this.cdr.markForCheck();
      }
    });
  }

  navigateToProject(projectId: number) {
    this.router.navigate(['/knowledge-base/projects', projectId]);
  }

  deleteProject(event: Event, projectId: number) {
    event.stopPropagation(); // Prevent row click navigation
    if (confirm('Are you sure you want to delete this project and all associated documents?')) {
      this.api.deleteProject(projectId).subscribe({
        next: (res) => {
          if (res.success) {
            this.loadProjects();
          } else {
            this.error = res.message || 'Failed to delete project';
          }
        },
        error: (err) => {
          this.error = err.error?.message || 'Failed to delete project';
        }
      });
    }
  }
}
