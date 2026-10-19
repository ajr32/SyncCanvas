# SyncCanvas Parent Guide

SyncCanvas (also called CeeEss) is a family-first student planner. The current version is a **local prototype** and should not be exposed on the public internet.

## Start and open the planner
Once the application is running locally, open the student home page at `http://127.0.0.1:8000/`. Open the parent preview at `http://127.0.0.1:8000/parent`. The parent preview is **not access-controlled**; do not treat it as a secure private account.

## Set up classes and periods
Add or review the student's classes in the parent area. Set up bell periods, their start and end times, and the weekdays when they meet. Assign classes to their appropriate periods. Scheduled classes should appear before unscheduled ones in the student view.

## Adjust the school calendar
Use the parent school-day controls to record days when school is closed or has a shortened schedule. A closure should hide the normal class periods for that date. For a shortened day, review any changed period start and end times. Return to the student view to check that the day looks right.

## Lunch Buddies and related tasks
Set up Lunch Buddies activities with the appropriate lunch period and meeting days. You can add notes or tasks for the student. A student can mark a task done; review the result and confirm it or return it for more work as appropriate.

## Homework and task review
Help the student keep task descriptions clear and connected to the correct class. Review optional deadlines, student progress, and completed work. If an assignment is linked to Canvas information, verify the details before relying on them.

## Saving and duplicate submissions
After selecting Save or Submit, wait for the page to respond before pressing the button again. Repeated clicks can create confusion. If a form reports an error, correct the indicated information and try once more. If the page is unresponsive, check whether the item already appears before entering it again.

## Sync status
Open **Parent Review** or **Settings** and select **Check for updates** to import the latest Canvas information. SyncCanvas returns to the same page and shows progress while an update runs. **Settings** also shows the last successful update time when available; this in-memory status resets after restarting the server. The student home update button remains available.

The planner may display a school-update or synchronization status. **Not connected** means an external school connection is not configured. **Updating** means a synchronization is in progress; **Up to date** indicates a successful reported update. Check the displayed information rather than assuming all school data is complete.

## Privacy and limitations
The current local prototype does not provide secure student/parent logins or safe public deployment. Do not enter sensitive student information or publish the local server online. SyncCanvas is separate from the older CanvasSync calendar-sync application.

## Quick family check
Open the student view and confirm that today's classes, any closure or shortened-day times, Lunch Buddies activities, and tasks appear as expected. Add a harmless sample task if needed, check the student completion flow, and remove the sample when finished.

## Reusable class materials and supportive attention cues

In **School Check-Out**, each active class has **Materials for this class**. Materials stay on the list across days; packed/unpacked checks apply to the current day. Remove obsolete items as needed. The separate daily packing list remains available.

The **Parent Review** page shows **Work that may need attention**. **Past due — check together** includes unfinished manual tasks and unfinished Canvas assignments with due dates before today. **Needs help — ask what is blocking progress** includes unfinished manual tasks explicitly marked stuck. A task may appear in both categories. Completed work is excluded. These are supportive reminders, not grades, scores, or evidence of misconduct.

### Reviewing submitted Canvas assignments

After **Check for updates**, assignments reported submitted in Canvas count as complete and do not appear as overdue. On **Parent Review**, the **Canvas submissions to review** section displays a small **Needs review** reminder. Click the assignment title to open Canvas in a new tab, then select **Reviewed** to clear the reminder. No grade is required. SyncCanvas never submits or changes anything in Canvas. Existing manual completion is preserved.
