# Phase 6 Status Transitions

## Step Statuses

`not_started`, `in_progress`, `complete`, `failed`, `blocked`,
`not_required`, and `needs_review`.

## Legal Transitions

| From | To |
| --- | --- |
| `not_started` | `in_progress`, `complete`, `failed`, `blocked`, `not_required`, `needs_review` |
| `in_progress` | `complete`, `failed`, `blocked`, `needs_review` |
| `failed` | `in_progress` |
| `blocked` | `in_progress`, `failed` |
| `needs_review` | `in_progress`, `complete`, `failed`, `blocked` |
| `complete` | no different status |
| `not_required` | no different status |

Repeating the same status is idempotent. Marketplace confirmation may update
its confirmation values while remaining complete. A failed price review may be
retried by returning to `in_progress`.

## Overall Status

Failure wins, then blocked, then needs review. All five steps complete or not
required yields complete. Any other started step yields in progress. Otherwise
the batch is not started.

Invalid transitions raise `InvalidStatusTransitionError`; they do not write a
record.
