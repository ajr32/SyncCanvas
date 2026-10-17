# SyncCanvas — Feature verification checklist

This checklist documents how to verify current local workflows. It does **not** claim that family acceptance or school-device testing has occurred.

## Automated regression tests
From the project root run:

```powershell
python -m pytest -q
```

The most recently verified Batch 8 working tree passed **216 tests**. Re-run after integrating the current files; a passing suite does not substitute for manual browser checks or authentication testing.

## Manual browser checks

| Area | Success case | Error or edge case |
|---|---|---|
| Student quick entry `/add` | Choose a class, add a short note, see it in the class review | No active classes: prompt parent to configure classes |
| School check-out `/review` | Save review for each active class and see count update | Class with no notes still appears and needs review |
| Questions `/review` | Save an unresolved question, then mark resolved | Do not mark resolved before answer is obtained |
| Paper check `/review` | Save pocket and backpack checks | Optional note may be empty |
| Parent planning `/parent` | Add a task and set its work date | Invalid date rejected; future item shown separately |
| Canvas linking `/parent` | Link related manual work to Canvas assignment | Cross-class link rejected; unlink does not delete Canvas data |
| My Afternoon `/afternoon` | Today's work and related tasks are grouped | Future work is in Planned for later, not duplicated in today's list |
| Recurring expectations `/settings` | Add and toggle an expectation | Disabled expectation should not be treated as active |
| Date formatting | Human-readable work date appears | Distant future dates, such as Jan 1, 2099, display correctly |

## What remains outside this checklist
Real school Chromebook compatibility; actual Canvas credentials and live school data; accessibility audit; secure roles and authenticated staff verification; backup/restore; production release. Do not close GitMap issues requiring these on the strength of the local tests alone.
