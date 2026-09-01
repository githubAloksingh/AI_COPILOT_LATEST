import { Component, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../core/api';

@Component({
  selector: 'app-defect-triage',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './defect-triage.html',
  styleUrl: './defect-triage.scss'
})
export class DefectTriage {
  title = '';
  environment = 'Production';
  description = '';
  logs = '';
  stepsToReproduce = '';
  expectedBehavior = '';
  actualBehavior = '';

  loading = false;
  error = '';
  result: any = null;

  constructor(private api: ApiService, private cdr: ChangeDetectorRef) {}

  generate() {
    if (!this.title || !this.description) return;

    this.loading = true;
    this.error = '';
    this.result = null;
    this.cdr.markForCheck();

    this.api.analyzeDefect({
      title: this.title,
      environment: this.environment,
      description: this.description,
      logs: this.logs,
      stepsToReproduce: this.stepsToReproduce,
      expectedBehavior: this.expectedBehavior,
      actualBehavior: this.actualBehavior
    }).subscribe({
      next: (res) => {
        if (res.success) {
          this.result = res.data;
        } else {
          this.error = res.message || 'Analysis failed';
        }
        this.loading = false;
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.error = 'Failed to analyze defect. Please try again.';
        this.loading = false;
        this.cdr.markForCheck();
      }
    });
  }

  copy() {
    navigator.clipboard.writeText(JSON.stringify(this.result, null, 2));
    alert('Report copied to clipboard');
  }
}
