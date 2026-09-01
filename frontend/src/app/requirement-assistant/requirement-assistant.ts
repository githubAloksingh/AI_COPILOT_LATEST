import { Component, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../core/api';

@Component({
  selector: 'app-requirement-assistant',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './requirement-assistant.html',
  styleUrl: './requirement-assistant.scss'
})
export class RequirementAssistant {
  title = '';
  description = '';
  priority = 'Medium';
  
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

    this.api.generateRequirement({
      title: this.title,
      description: this.description,
      priority: this.priority
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
        this.error = 'We couldn\'t generate the response. Please try again.';
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
