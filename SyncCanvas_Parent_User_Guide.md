# SyncCanvas — Parent User Guide

*Working guide · October 2026 · Update as the app changes*

## Purpose and current limits

SyncCanvas is a family-first student planner. It combines student check-ins, parent-managed plans, school schedule information, and—when configured—Canvas assignment information. The reviewed prototype is **local-only** and **does not yet enforce separate parent and student accounts**. Keep it private; do not publish it to the internet or enter sensitive student information.

This guide explains the visible family workflow. It is not a developer or deployment manual.

## 1. Set up classes

1. Open the **Parent Page** and choose **Manage Classes and Canvas course links**.
2. Add or configure the student's active classes, including their display order where offered.
3. Check that the student home page shows the intended classes.
4. If Canvas is configured, verify that the correct courses are linked. A Canvas assignment and a manually added SyncCanvas task are distinct unless explicitly linked.

## 2. Set the bell schedule

1. From the Parent Page, open **Bell Schedule**.
2. Choose **Add a bell period**.
3. Enter a label, start time, end time, and meeting weekdays.
4. Save, then assign active classes or activities to the period as appropriate.
5. Edit the period if times or meeting days change.

Times can be entered in familiar AM/PM form, such as `8:15 AM` and `1:30 PM`. The end must be later than the start, and at least one meeting day must be selected. Bell periods may include weekend days if the family chooses them; Monday–Friday is merely the initial selection.

## 3. Record holidays, snow days, and special schedules

1. From **Bell Schedule**, select **Manage closures and shortened days**, or open **School Days** from the parent settings.
2. Pick a date and a type: **No school** or **Shortened / special schedule**.
3. Optionally add a reason, such as “Snow day” or “Early dismissal,” then save.
4. For a shortened day, enter new start and end times for only the periods that change. Both times are required for an override; clearing both removes it.
5. Use **Remove exception** when the special date is no longer needed.

These are **date-specific exceptions**. They do not rewrite the normal bell schedule. A no-school notice does not automatically delete student tasks or Canvas assignments.

## 4. Add recurring study expectations

1. Open **Settings → Recurring expectations**.
2. Choose an active class.
3. Enter a specific instruction, such as “Read for 15 minutes.”
4. Choose **Every day** or **Monday–Friday** and save.
5. Confirm the expectation is **Active** and appears in the afternoon plan on applicable days.
6. Use **Pause** to suspend it and **Resume** to start it again.

The current interface supports these two repeat patterns; it does not expose an arbitrary custom recurrence calendar. Each day's generated work is separate so a previous day's completion is preserved.

## 5. Review the student's daily check-ins

On the student home page, a class may be **Not checked yet**, **Checked today**, or **Nothing tonight**. “Nothing tonight” means the student reported no work for that class; it is not a guarantee that Canvas or the teacher has nothing assigned. Use the Parent Page to review entries, missing information, and questions together.

## 6. Add and plan tasks

On the Parent Page, add a task to an active class, select its type, and enter a clear description. Where available, set a **planned work date**. Keep this separate from the assignment's **due date**. For imported Canvas assignments, Canvas remains authoritative for due information; changing a local work plan should not rewrite Canvas.

## 7. Review progress and completion

The student's task progress can be **Not started**, **In progress**, or **Done**. A task marked Done may still await parent confirmation.

Suggested check-out routine:

1. Review each class and any student questions.
2. Open the homework plan and ask the student to explain unfinished or in-progress work.
3. Confirm completed tasks after checking them, or choose **Needs another look** if more work is required.
4. Add a short parent note when useful.
5. Check Canvas directly for teacher requirements and submission status.

Reopening a completed local task returns it to unfinished work. In the reviewed code, completion is timestamped when a task is marked Done, and that timestamp is cleared when progress returns to Not started or In progress. This timestamp is internal; the family interface may not display it.

## 8. Canvas updates and troubleshooting

Where Canvas integration is configured, use **Check for updates** to request a refresh. SyncCanvas does not replace Canvas as the teacher's assignment and submission system. If assignments are missing, first confirm the course link and check the assignment in Canvas itself. If an update fails, do not delete local student work as a first response.

## 9. Common problems

| Problem | First thing to check |
|---|---|
| Class missing | Is the class enabled and not archived? |
| Incorrect school hours | Check the normal bell period and any dated exception. |
| Snow day not shown | Check the saved date and whether it is marked **No school**. |
| Recurring practice missing | Is the expectation Active? Does its Every day / Monday–Friday pattern apply today? |
| Task marked Done accidentally | Change progress back to In progress or Not started, then review it. |
| Canvas assignment missing | Check the Canvas course link and the assignment in Canvas. |
| No-school notice but homework remains | This is expected: closures do not automatically remove assignments. |

## 10. Keep the guides current

When a feature changes, update the relevant section of this guide and the Student User Guide. For GitHub documentation requirements, link to the section that describes the real workflow; verify the behavior before marking a feature complete. Avoid creating a separate document for every issue.

---

*Guide maintenance: This draft is based on the reviewed GitHub `main` branch in October 2026. Local changes may be newer. Review UI wording and any integration setup steps against the installed application before publishing.*

## Family timezone and daylight saving time (issue #70)

SyncCanvas uses the computer's local timezone for the family's calendar day unless `SYNCCANVAS_TIMEZONE` is explicitly configured. The family does not need to adjust clocks when daylight saving time begins or ends. Canvas timestamps with a timezone are converted to the family's calendar date before being shown as a due date; the original Canvas due timestamp is retained.

If the planner is running on a computer or server in another timezone, its operator can set `SYNCCANVAS_TIMEZONE` to the family's IANA timezone (for example `America/New_York`) before starting the app. This is a setup setting, not a student-facing control. On Windows, named timezones may require the Python `tzdata` package.

**Check:** Compare a Canvas assignment near midnight with its date in the family's timezone. Confirm that a date across a daylight-saving change is shown correctly. Check that the daily plan and school-day exceptions use the same local date.

**Note:** Previously imported Canvas due dates may need a new Canvas refresh to recalculate their local calendar dates. No task times or due-time editing are introduced.


## Family workflow reference — issue group #387

This section collects family-facing instructions and **how to verify them** for the work grouped in [GitHub issue #387](https://github.com/ajr32/SyncCanvas/issues/387). A written check is not proof that a test was performed. Use the installed app to confirm results before signing off an issue.

### School profile and timezone (#50, #70)

Where the parent-facing **School Profile** page is installed, set the school's IANA timezone and optional term start/end dates. Term dates must be in chronological order. Keep the saved timezone consistent with the family's intended calendar. If the School Profile page is not available in your working copy, check whether its code has been installed; do not claim the feature is available based only on this guide.

**Verify:** Save a valid timezone and term-date range, refresh, and confirm they persist. Try a reversed date range and an invalid timezone; neither should replace the saved values. For #70, check a Canvas due timestamp close to midnight and across both daylight-saving changes. Confirm the family-local due **date** is correct and the original Canvas timestamp is not rewritten. A Canvas refresh may be required for previously imported dates.

### Task types and class check-ins (#58)

Student tasks can describe Homework, Study, Finish Classwork, Prepare for Quiz, or Ask Teacher where the interface offers them. **Nothing Tonight** is a class check-in and must not create an ordinary task or falsely mark one Done.

**Verify:** Add a Study task to an active class and confirm it appears once. Record Nothing Tonight for another class and confirm it shows as a check-in, not a completed task. Try an empty description and check the form's validation. Verify an imported Canvas assignment remains unchanged.

### Progress and reopening (#59–60)

Students can change local task progress between Not started, In progress, and Done. Reopening a Done task makes it unfinished again; parent confirmation may need to be repeated.

**Verify:** Create a test task, save each state, refresh, and confirm it persists. Mark it Done and reopen it. Check that completion is cleared internally when reopened and recorded again on recompletion, without claiming the timestamp is visible in the UI. Confirm the parent review state is consistent.

### Planned work versus due date (#61–62)

Keep **planned work date** separate from **due date**. A Canvas due date is teacher-controlled and is not changed by moving work to another day. #61 was closed with a deliberately limited scope: optional due **date**, not due times or priorities. #62 remains open: a dedicated due-at-school/do-at-home workflow is not established by the current guides.

**Verify before #62 closure:** Demonstrate the intended student and parent workflow for work due at school versus work planned at home, including an assignment with a Canvas due date and one with no due date. Verify the two concepts cannot be accidentally confused or overwritten. Documentation cannot substitute for missing interface behavior.

### Notes, links, and subtasks (#63)

The current guide can explain the task description and the Canvas source link. It does **not** establish that separate editable notes, arbitrary links, and checkable subtasks have all been implemented.

**Verify before closure:** Create and edit a task note, open a stored link, add and complete subtasks, refresh to check persistence, and check invalid/empty input. If the installed app does not support one of these, keep #63 open and update this section after implementation.

### Today and tonight views (#65)

The student home page supports class check-ins, and the afternoon plan shows local tasks and relevant Canvas assignments. Do not treat an empty class check-in as proof there is no teacher-assigned work.

**Verify:** With a test class, check a day containing a local task and an imported Canvas assignment. Check an empty day and a missing check-in. Refresh to ensure tasks and progress persist. Confirm any outstanding hands-on acceptance checks before marking #65 complete.

### Recurring study and school-day rules (#69, #71–72)

Parents can create an **Every day** or **Monday–Friday** Study expectation, pause/resume it, and manage normal bell periods plus dated No school and Shortened / special schedule exceptions. The larger repeating-task feature #69 is recorded as deferred 2.0 work; this does not invalidate the smaller recurring Study control currently available.

**Verify #71:** Add a future No school date and confirm the student notice; add a shortened day with a valid bell-period override; try an invalid override; remove both exceptions and check that the regular schedule is unchanged. Existing local and Canvas assignments must not be deleted.

**Verify #72:** Add and edit a bell period with valid weekdays and times; try invalid times or no meeting days; create a weekday Study expectation; verify it appears on an applicable day; pause and resume it. Check that an earlier day's completed task remains completed.

### Deferred features (#64, #66–69)

Safe undo/edit history, seven-day assignment view, month/upcoming agenda views, class/status filters, and full repeating study/routine task support are **closed as deferred 2.0 items**, not delivered features. Do not mark them implemented or tell families to use them. Revisit these guide sections only if the features are brought into a future release.

### Sign-off rule for #387

For each original GitMap issue, record the application version or commit, test date, test result, and any outstanding failures. Only mark its documentation step complete when these instructions match the installed app; close an issue only after **all** its requirements have been satisfied. #387 is an organizational work group, not a single implementation task.


## School Check-Out — family workflow (issues #82–#86, #88)

**Purpose:** At the end of school, the student briefly revisits the last few minutes of **every class** to catch anything not written down and remember what needs to come home. This is a double-check of existing class entries, **not** another homework or approval process.

The student opens **School Check-Out**, reviews each class's recorded work and any displayed Canvas assignments, adds forgotten work through the normal **Add Information** flow, and checks that needed papers, books, binder, and devices are coming home. An optional class note can capture something missing or unclear. The **✓ I reviewed this class** action appears near the top of each class card, minimizing scrolling. The page displays the number of classes reviewed and, once all are checked, reminds the student to check the bag.

**At home:** Use the regular Parent Review to discuss homework and any missing-material or unclear-instruction notes. A reviewed class does not mean its assignments are completed, teacher-confirmed, or submitted to Canvas.

**How the six issues were simplified:** #82 (unresolved work) and #88 (follow-up) use ordinary class entries and optional notes; #83 (required materials) and #84 (ready-to-go) are a brief mental bag check, not a separate itemized inventory; #85 (family-use verification) and #86 (who reviewed) are satisfied in the family workflow by the student's class-by-class review action, without requiring a teacher or separate reviewer identity form. These are **design decisions for the simplified workflow**, not claims that the original, more elaborate forms remain in the UI.

**Family check:** Open School Check-Out with several active classes. Confirm the review button is at the top of each card, an overlooked task can be entered through Add Information, an optional missing-material note can be saved, the reviewed count updates, and the all-classes-reviewed message appears after every class is checked. Confirm the parent can still review the underlying work separately.

## Verification and support: issues #20, #29, #32, #37, #38

### #20 — Who reads and writes what

Students create class check-ins, notes, and progress updates in the local planner. Parents configure classes, schedules, and expectations and review/confirm work. Imported Canvas assignment fields originate from Canvas; local student notes, progress, and work dates are separate. SyncCanvas must not write assignment changes or submissions back to Canvas. **Check:** create a local task, import or inspect a Canvas assignment, change local progress, and confirm the Canvas assignment's source fields remain unchanged. Check that a rejected/invalid edit leaves existing data intact. This describes expected ownership; #20's test checklist still needs separate confirmation.

### #29 — Development quality checks (not a family-facing feature)

From the project root, install the optional development tools with `python -m pip install -e ".[test,dev]"`. Run `python -m ruff check synccanvas/seed_demo.py synccanvas/tests/test_seed_demo.py`, `python -m ruff format --diff synccanvas/seed_demo.py synccanvas/tests/test_seed_demo.py`, `python -m mypy synccanvas/seed_demo.py --follow-imports=skip`, and `python -m pytest -q`. The GitHub Python checks workflow runs these commands. Formatting is currently reported as a diff rather than enforced; the checks are an initial, deliberately narrow adoption, not a claim that the entire codebase is fully typed or formatted. A failed check needs investigation before sign-off.

### #32 — Fictional development examples

To create a **separate fictional** sample database for development, run `python -m synccanvas.seed_demo --output synccanvas_demo.sqlite3` from the project root. It creates two example classes and two sample tasks. The tool refuses an existing output file and refuses the configured live planner database path. Do not use the sample file as the family's database, and do not put real student details into test data. **Check:** run once, inspect the demo records, run again and confirm it refuses to overwrite, and verify the real family database remains untouched.

### #37 — Saving and loading indicators

When a family member submits a form on a page using the shared SyncCanvas layout, the button should switch to **Working…** and a **Saving or loading… Please wait.** status should appear until navigation finishes. This is a busy indicator, not proof that saving succeeded. The app's existing server validation/error responses still apply. **Check:** submit a valid form, then a deliberately invalid one; confirm the invalid request is rejected, no duplicate action is created by a rapid second click, and navigation/back does not leave an unusable disabled button. This is not a full in-page error-message system.

### #38 — Avoiding duplicate task entries

A single form submission should create one task. A repeat of the same submission token should not create a second copy. A fresh form submission with a new token may create a separate task even if its wording matches. **Check:** submit a task, replay the identical request, verify only one entry exists, and try an invalid token to confirm it is rejected. Check both student task creation and parent review afterward.

**Documentation versus completion:** These are verification procedures, not evidence that all tests ran successfully. Confirm the current code and user-observed behavior before marking implementation or testing complete in GitHub.


## Accessible progressive enhancement (issue #24)

The **Add Information** page now uses a standard HTML POST form: the selected class is submitted as a named field, and the server validates it using the existing task-saving workflow. This means the essential quick-entry action does not require JavaScript, and the same duplicate-submission protection applies.

**Family verification:** With two active classes, open **Add Information**, choose the second class, save a short task, and confirm it appears under that class in the planner and Parent Review. Repeat with JavaScript disabled if convenient. Check that a missing or invalid class is rejected and that resubmitting the same form does not create a duplicate task. This is a focused improvement to quick entry, not a claim that every feature has been independently audited for accessibility.



## Classroom check-out and corrections (issues #74–#78)

The student can choose Homework, Study, or Finish Classwork in My Classes, record details and an optional due date, and mark each class Checked, Nothing to do, or Needs clarification during School Check-Out. Unreviewed classes remain Unchecked. A shared end-of-day packing list lets the student add books, papers, devices, and other materials and mark them packed.

If a checkout status was entered incorrectly, change it using **Change checkout status**. Changes between different saved statuses appear under **Earlier corrections**, with timestamps shown in UTC. Saving the same status again does not add a correction. The existing task, Canvas, and parent review flows remain separate.

**Verification:** Add a Finish Classwork task with a due date; verify it appears in School Check-Out. Set a class to Needs clarification, then Checked, and verify Earlier corrections records the change. Add a workbook to the packing list and mark it Packed. Check that blank packing descriptions and invalid class statuses are rejected. If no materials are needed, leave the packing list empty.


## Navigation, responsive layout, and form accessibility

The shared page layout adapts to phone, tablet, and Chromebook widths. Navigation has a named landmark and a keyboard-accessible skip link. Inputs use explicit labels where the shared field helper is used, and keyboard focus is visible. Browser requests for missing pages show a return-home link; API clients continue receiving JSON errors.

**Verification:** Resize the browser to narrow-phone, tablet, and Chromebook widths. Check that navigation wraps and that buttons and fields remain reachable. Tab through the page, including the skip link. Test `/missing-page` in the browser for a 404 page with a return link. Submit an invalid form and verify the status is 422. Run `python -m pytest -q` for the automated checks.
