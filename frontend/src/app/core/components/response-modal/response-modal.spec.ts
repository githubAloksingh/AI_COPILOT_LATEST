import '@angular/compiler';
import { describe, it, expect, beforeEach } from 'vitest';
import { ResponseModal } from './response-modal';
import { ChangeDetectorRef } from '@angular/core';

describe('ResponseModal - Acceptance Criteria + Add functionality', () => {
  let modal: ResponseModal;
  let mockCdr: ChangeDetectorRef;

  beforeEach(() => {
    mockCdr = {
      markForCheck: () => {},
      detectChanges: () => {},
      checkNoChanges: () => {},
      detach: () => {},
      reattach: () => {}
    } as any;

    const mockExportService = {} as any;
    modal = new ResponseModal(mockExportService, mockCdr);

    modal.data = {
      userStories: [
        {
          requirementId: 'US-001',
          title: 'User Logout Functionality',
          userStory: 'As a user, I want to logout securely',
          summary: 'Logs user out and removes tokens',
          acceptanceCriteria: [
            { text: 'AuthService must remove the JWT', grounding: 'EXPLICIT', source: [] },
            { text: 'AuthService must clear current user', grounding: 'EXPLICIT', source: [] }
          ]
        },
        {
          requirementId: 'US-002',
          title: 'Authentication Guard for Protected Pages',
          userStory: 'As a user, I want protected pages to be guarded',
          summary: 'Guards protected routes',
          acceptanceCriteria: [
            { text: 'AuthGuard must check if user is logged in', grounding: 'EXPLICIT', source: [] }
          ]
        }
      ]
    };
    modal.type = 'userstory';
    modal.selectedReqIndex = 0;
    modal.initEditableCopy();
  });

  it('1. should add a new empty criterion to US-001 when + Add is clicked and put it into edit mode', () => {
    const us1 = modal.requirementList[0];
    expect(us1.acceptanceCriteria.length).toBe(2);

    modal.addNewAcceptanceCriterion(us1);

    expect(us1.acceptanceCriteria.length).toBe(3);
    expect(modal.isNewCriterion).toBe(true);
    expect(modal.editingSectionTarget).toBe(us1.acceptanceCriteria);
    expect(modal.editingSectionKey).toBe(2);
    expect(modal.sectionDraft).toBe('');
    expect(modal.isEdited).toBe(true);
  });

  it('2. should fail empty value validation if user saves a blank criterion', () => {
    const us1 = modal.requirementList[0];
    modal.addNewAcceptanceCriterion(us1);

    modal.sectionDraft = '   ';
    modal.saveCriterion(us1, 2);

    expect(modal.criterionValidationError).toBe('Acceptance criterion cannot be empty.');
    expect(modal.isNewCriterion).toBe(true);
    expect(modal.editingSectionTarget).toBe(us1.acceptanceCriteria); // still in edit mode
  });

  it('3. should save valid criterion text, exit edit mode, and trim whitespace', () => {
    const us1 = modal.requirementList[0];
    modal.addNewAcceptanceCriterion(us1);

    modal.sectionDraft = '  The system must display a successful logout confirmation.  ';
    modal.saveCriterion(us1, 2);

    expect(modal.criterionValidationError).toBe('');
    expect(modal.isNewCriterion).toBe(false);
    expect(modal.editingSectionTarget).toBeNull();
    expect(us1.acceptanceCriteria.length).toBe(3);
    expect(modal.getItemText(us1.acceptanceCriteria[2])).toBe('The system must display a successful logout confirmation.');
  });

  it('4. should isolate added criterion to US-001 without leaking into US-002', () => {
    const us1 = modal.requirementList[0];
    const us2 = modal.requirementList[1];

    modal.addNewAcceptanceCriterion(us1);
    modal.sectionDraft = 'The system must display a successful logout confirmation.';
    modal.saveCriterion(us1, 2);

    // Switch to US-002
    modal.selectRequirement(1);
    expect(modal.currentRequirement.requirementId).toBe('US-002');
    expect(us2.acceptanceCriteria.length).toBe(1);
    expect(modal.getItemText(us2.acceptanceCriteria[0])).not.toContain('logout confirmation');

    // Switch back to US-001
    modal.selectRequirement(0);
    expect(modal.currentRequirement.requirementId).toBe('US-001');
    expect(us1.acceptanceCriteria.length).toBe(3);
    expect(modal.getItemText(us1.acceptanceCriteria[2])).toBe('The system must display a successful logout confirmation.');
  });

  it('5. should allow editing an existing criterion and saving changes', () => {
    const us1 = modal.requirementList[0];
    modal.editExistingCriterion(us1, 0);

    expect(modal.isNewCriterion).toBe(false);
    expect(modal.sectionDraft).toBe('AuthService must remove the JWT');

    modal.sectionDraft = 'AuthService must completely revoke and delete the JWT token';
    modal.saveCriterion(us1, 0);

    expect(modal.editingSectionTarget).toBeNull();
    expect(modal.getItemText(us1.acceptanceCriteria[0])).toBe('AuthService must completely revoke and delete the JWT token');
  });

  it('6. should cancel a new unsaved criterion and remove it from the list', () => {
    const us1 = modal.requirementList[0];
    expect(us1.acceptanceCriteria.length).toBe(2);

    modal.addNewAcceptanceCriterion(us1);
    expect(us1.acceptanceCriteria.length).toBe(3);

    modal.cancelCriterion(us1, 2);
    expect(us1.acceptanceCriteria.length).toBe(2);
    expect(modal.isNewCriterion).toBe(false);
    expect(modal.editingSectionTarget).toBeNull();
  });

  it('7. should delete only the targeted criterion using deleteCriterion', () => {
    const us1 = modal.requirementList[0];
    expect(us1.acceptanceCriteria.length).toBe(2);

    const textToKeep = modal.getItemText(us1.acceptanceCriteria[1]);
    modal.deleteCriterion(us1, 0);

    expect(us1.acceptanceCriteria.length).toBe(1);
    expect(modal.getItemText(us1.acceptanceCriteria[0])).toBe(textToKeep);
  });

  it('8. should return empty string from getItemText when item.text is empty string', () => {
    const emptyItem = { text: '', grounding: 'DERIVED', source: [] };
    expect(modal.getItemText(emptyItem)).toBe('');
    expect(modal.getItemText('')).toBe('');
    expect(modal.getItemText(null)).toBe('');
  });

  it('9. should correctly add string item to string arrays with addStringItemSafe', () => {
    const obj: any = { bugFixes: ['Fix 1'] };
    modal.addStringItemSafe(obj, 'bugFixes');
    expect(obj.bugFixes.length).toBe(2);
    expect(obj.bugFixes[1]).toBe('');
  });

  it('10. should sync all requirements back to data on saveAllEdits', () => {
    modal.mode = 'EDIT_ALL';
    modal.editableRequirements[0].title = 'Updated Title';
    modal.saveAllEdits();

    expect(modal.mode).toBe('VIEW');
    expect(modal.data.userStories[0].title).toBe('Updated Title');
  });

  it('11. Exact User Flow: Add -> Validate -> Save -> Switch US-002 -> Switch back US-001 -> Edit -> Save -> Add -> Cancel -> Delete', () => {
    // 1. Open Generated User Stories (modal initialized with US-001 active)
    expect(modal.selectedReqIndex).toBe(0);
    const us1 = modal.requirementList[0];
    const initialAcCountUs1 = us1.acceptanceCriteria.length; // 2

    // 2. Select US-001 (active)
    expect(modal.currentRequirement.requirementId).toBe('US-001');

    // 3 & 4. Scroll to Acceptance Criteria & Click + Add
    modal.addNewAcceptanceCriterion(us1);

    // 5. Verify a new criterion appears immediately
    expect(us1.acceptanceCriteria.length).toBe(initialAcCountUs1 + 1);

    // 6. Verify it is editable
    expect(modal.isNewCriterion).toBe(true);
    expect(modal.editingSectionTarget).toBe(us1.acceptanceCriteria);
    expect(modal.editingSectionKey).toBe(initialAcCountUs1);

    // 7. Validation test: Empty Save fails
    modal.sectionDraft = '';
    modal.saveCriterion(us1, initialAcCountUs1);
    expect(modal.criterionValidationError).toBe('Acceptance criterion cannot be empty.');

    // 8. Type: "The system must display a successful logout confirmation."
    modal.sectionDraft = 'The system must display a successful logout confirmation.';

    // 9. Click Save
    modal.saveCriterion(us1, initialAcCountUs1);

    // 10. Verify the criterion appears normally
    expect(modal.editingSectionTarget).toBeNull();
    expect(modal.criterionValidationError).toBe('');
    expect(modal.getItemText(us1.acceptanceCriteria[initialAcCountUs1])).toBe('The system must display a successful logout confirmation.');

    // 11. Switch to US-002
    modal.selectRequirement(1);
    expect(modal.currentRequirement.requirementId).toBe('US-002');
    const us2 = modal.requirementList[1];

    // 12. Verify the new criterion is NOT under US-002
    const us2HasNewCriterion = us2.acceptanceCriteria.some((ac: any) =>
      modal.getItemText(ac).includes('successful logout confirmation')
    );
    expect(us2HasNewCriterion).toBe(false);

    // 13. Switch back to US-001
    modal.selectRequirement(0);
    expect(modal.currentRequirement.requirementId).toBe('US-001');

    // 14. Verify the new criterion is still present
    const us1HasNewCriterion = us1.acceptanceCriteria.some((ac: any) =>
      modal.getItemText(ac) === 'The system must display a successful logout confirmation.'
    );
    expect(us1HasNewCriterion).toBe(true);

    // 17. Edit the newly created criterion
    modal.editExistingCriterion(us1, initialAcCountUs1);
    expect(modal.isNewCriterion).toBe(false);
    expect(modal.sectionDraft).toBe('The system must display a successful logout confirmation.');

    // 18. Change the text
    modal.sectionDraft = 'The system must display a successful logout confirmation and redirect to login.';

    // 19. Save again
    modal.saveCriterion(us1, initialAcCountUs1);

    // 20. Verify the updated text
    expect(modal.getItemText(us1.acceptanceCriteria[initialAcCountUs1])).toBe('The system must display a successful logout confirmation and redirect to login.');

    // 21. Add another criterion
    const countBeforeCancel = us1.acceptanceCriteria.length;
    modal.addNewAcceptanceCriterion(us1);
    expect(us1.acceptanceCriteria.length).toBe(countBeforeCancel + 1);

    // 22. Click Cancel without entering anything
    modal.cancelCriterion(us1, countBeforeCancel);

    // 23. Verify the empty criterion disappears
    expect(us1.acceptanceCriteria.length).toBe(countBeforeCancel);
    expect(modal.isNewCriterion).toBe(false);

    // 24. Delete one existing criterion using X
    const firstItemText = modal.getItemText(us1.acceptanceCriteria[0]);
    modal.deleteCriterion(us1, 0);

    // 25. Verify only the selected criterion is removed
    expect(us1.acceptanceCriteria.length).toBe(countBeforeCancel - 1);
    expect(modal.getItemText(us1.acceptanceCriteria[0])).not.toBe(firstItemText);
    expect(us1.acceptanceCriteria.some((ac: any) => modal.getItemText(ac).includes('successful logout confirmation and redirect'))).toBe(true);
  });
});
