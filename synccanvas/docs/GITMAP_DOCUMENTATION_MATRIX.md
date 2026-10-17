# GitMap documentation reconciliation — proposals only

This package **does not modify GitHub issues or GitMap IDs**. Review original issue checkboxes before changing state.

| GitHub | Documentation support | Status recommendation |
|---|---|---|
| [#203](https://github.com/ajr32/SyncCanvas/issues/203) Student quick start | Prior Batch 1 `STUDENT_QUICK_START.md`; `FAMILY_ACCEPTANCE_SCRIPTS.md` | Review guide against UI before checking (d) |
| [#204](https://github.com/ajr32/SyncCanvas/issues/204) Parent check-out/troubleshooting | `SCHOOL_AIDE_CHECKOUT.md`, `PARENT_PLANNING.md`, `CANVAS_DATA_POLICY.md` | Candidate for documentation check-off after review |
| [#148](https://github.com/ajr32/SyncCanvas/issues/148) Link rather than overwrite | `PARENT_PLANNING.md`, `CANVAS_DATA_POLICY.md` | Review implementation/tests and documentation separately |
| [#88](https://github.com/ajr32/SyncCanvas/issues/88) Unresolved follow-up | `SCHOOL_AIDE_CHECKOUT.md`, `FAMILY_ACCEPTANCE_SCRIPTS.md` | Candidate for (d), keep acceptance separate |
| [#90](https://github.com/ajr32/SyncCanvas/issues/90) Missing class entries | `SCHOOL_AIDE_CHECKOUT.md`, `REGRESSION_CHECKLIST.md` | Verify (c) before closing |
| [#180](https://github.com/ajr32/SyncCanvas/issues/180) Date edge cases | `REGRESSION_CHECKLIST.md` | Review automated cases; don't infer all edge cases pass |
| [#194](https://github.com/ajr32/SyncCanvas/issues/194) Parent alternative to staff login | `SCHOOL_AIDE_CHECKOUT.md`, `PRIVACY_AND_LIMITATIONS.md` | Keep open for acceptance |
| [#205](https://github.com/ajr32/SyncCanvas/issues/205) Costs/backup/rotation | `LOCAL_BACKUP_AND_RECOVERY.md` | Partial only; not a cloud/billing/secrets guide |

**Rule:** (a) design/ownership, (b) implementation, (c) successful plus boundary verification, (d) accurate documentation. Close only when all acceptance requirements are satisfied. Do not close authentication, school-approval, or deployment issues on the basis of local documentation.
