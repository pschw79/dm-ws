# Context map — Dunder Mifflin package manager agent

> **Part 2 deliverable.** Classify every candidate fact the agent might use.
> Each item must be marked **include**, **retrieve on demand**, or **exclude**.

| # | Candidate fact | Classification | Reason |
|---|---------------|----------------|--------|
| 1 | Current package status (in_transit, delivered, exception ...) | include | Needed in almost every answer |
| 2 | Package condition (OK, damaged, missing label ...) | include | Safety-critical; always relevant |
| 3 | Active route and driver for a package | include | Core operational data |
| 4 | Full history of all past deliveries (all time) | retrieve on demand | Too large for every call; only needed for trend questions |
| 5 | Other packages on the same route | retrieve on demand | Only relevant when a route problem is suspected |
| 6 | Customer name and contact details | exclude | PII — agent must never surface this |
| 7 | Employee salary or HR records | exclude | Out of scope; safety and privacy |
| 8 | Real-time GPS coordinates of drivers | retrieve on demand | Only needed for live tracking questions |
| 9 | Fragile flag on package | include | Affects handling decisions |
| 10 | Shipping policy rules (conditions, approvals) | include | Agent must follow these rules |

## Open questions for Part 3 (memory)

- Should a user's display preferences (e.g. Stanley collapsing old deliveries) be remembered?
- Should the agent remember which order a user was just looking at within a session?
- Who should be allowed to mark a preference? (role-based)
