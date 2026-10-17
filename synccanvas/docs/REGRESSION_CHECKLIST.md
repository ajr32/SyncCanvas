# Regression and hands-on verification

Run from project root:

```powershell
python -m pytest -q
```

Previous Batch 8 baseline: **216 passed, 0 failed**. This is a historical result; the documentation package does not rerun the suite or change code.

| Area | Positive test | Edge/failure test |
|---|---|---|
| Quick capture | Save short note to right class | Reject blank details |
| School review | Persist each class outcome | Leave unreviewed class visible |
| Paper checks | Persist pocket/backpack state | Optional note may be blank |
| Follow-up | Save unresolved question | Resolve explicitly only |
| Parent planning | Future task shown once later | Reject invalid planned date |
| Canvas link | Same-class link and unlink | Reject cross-class link |
| Recurrence | Daily task instance | Paused rule doesn't add new work |
| Completion | Student done, parent confirms | Returned work not confirmed |
| Display | Readable dates, clear class names | HTML in notes is escaped |

## Real-world acceptance still needed
Student speed of entry, parent afternoon review, actual Chromebook keyboard/touch experience, school policy, and authorized live Canvas data. Log page, steps, expected/actual, device, and sanitized evidence for failures.
