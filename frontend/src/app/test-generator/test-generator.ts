import { Component, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../core/api';

@Component({
  selector: 'app-test-generator',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './test-generator.html',
  styleUrl: './test-generator.scss'
})
export class TestGenerator {
  requirement = '';
  acceptanceCriteria = '';
  testTypes = {
    functional: true,
    edgeCases: true,
    security: false,
    performance: false
  };

  loading = false;
  error = '';
  result: any[] = [];

  constructor(private api: ApiService, private cdr: ChangeDetectorRef) {}

  generate() {
    if (!this.requirement) return;

    this.loading = true;
    this.error = '';
    this.result = [];
    this.cdr.markForCheck();

    const selectedTypes: string[] = [];
    if (this.testTypes.functional) selectedTypes.push('Functional');
    if (this.testTypes.edgeCases) selectedTypes.push('Edge Cases');
    if (this.testTypes.security) selectedTypes.push('Security');
    if (this.testTypes.performance) selectedTypes.push('Performance');

    this.api.generateTestCases({
      requirement: this.requirement,
      acceptanceCriteria: this.acceptanceCriteria,
      testTypes: selectedTypes
    }).subscribe({
      next: (res) => {
        if (res.success) {
          this.result = res.data;
        } else {
          this.error = res.message || 'Generation failed';
        }
        this.loading = false;
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.error = 'Failed to generate test cases. Please try again.';
        this.loading = false;
        this.cdr.markForCheck();
      }
    });
  }

  copy() {
    navigator.clipboard.writeText(JSON.stringify(this.result, null, 2));
    alert('Copied to clipboard');
  }
}
