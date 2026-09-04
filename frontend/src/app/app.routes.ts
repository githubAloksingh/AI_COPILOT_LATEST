import { Routes } from '@angular/router';
import { Dashboard } from './dashboard/dashboard';
import { KnowledgeBase } from './knowledge-base/knowledge-base';
import { ProjectDetails } from './project-details/project-details';
import { UserStoryComponent } from './knowledge-base/user-story/user-story';
import { FunctionalDesignComponent } from './knowledge-base/functional-design/functional-design';
import { TechnicalDesignComponent } from './knowledge-base/technical-design/technical-design';
import { RequirementAssistant } from './requirement-assistant/requirement-assistant';
import { TestGenerator } from './test-generator/test-generator';
import { DefectTriage } from './defect-triage/defect-triage';
import { ReleaseNotes } from './release-notes/release-notes';
import { AuditHistory } from './audit-history/audit-history';

// Authentication has been removed — every route is publicly accessible.
export const routes: Routes = [
  { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
  { path: 'dashboard', component: Dashboard },
  { path: 'knowledge-base', component: KnowledgeBase },
  { path: 'knowledge-base/projects/:id', component: ProjectDetails },
  { path: 'user-story', component: UserStoryComponent },
  { path: 'functional-design', component: FunctionalDesignComponent },
  { path: 'technical-design', component: TechnicalDesignComponent },
  { path: 'knowledge-base/user-story', component: UserStoryComponent },
  { path: 'knowledge-base/functional-design', component: FunctionalDesignComponent },
  { path: 'knowledge-base/technical-design', component: TechnicalDesignComponent },
  { path: 'requirements', component: RequirementAssistant },
  { path: 'test-generator', component: TestGenerator },
  { path: 'defect-triage', component: DefectTriage },
  { path: 'release-notes', component: ReleaseNotes },
  { path: 'audit-history', component: AuditHistory },
  { path: '**', redirectTo: 'dashboard' }
];

