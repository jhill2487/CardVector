# Extracted Workflows

## Extraction Summary

Phase 2 extracts only the coordination around the existing workflow-context
implementation. `workflow_context.py` retains current job discovery, state
derivation, and file persistence behavior.

| Previous `putnam_os.py` orchestration | Application API | Existing implementation called |
| --- | --- | --- |
| local workflow cache and refresh interval | `WorkflowApplication.snapshot` | `discover_workflow_jobs` |
| queue-row conversion | `WorkflowApplication.snapshot` | `jobs_from_queue_rows` |
| active/local/completed job merge | `WorkflowApplication.snapshot` | `merge_job_lists` |
| completed-job query | `WorkflowApplication.snapshot` | `recent_completed_jobs` |
| job lookup by ID | `WorkflowApplication.job_by_id` | list lookup only |
| Processing queue grouping | `WorkflowApplication.group_processing_jobs` | `group_processing_jobs` |
| Home active-listing summary | `WorkflowApplication.active_listings_summary` | `active_listings_summary` |
| workflow handoff persistence | `WorkflowApplication.update_context` | `update_workflow_context` |
| force local workflow refresh | `WorkflowApplication.invalidate` | invalidates facade cache only |

## Updated Putnam OS Call Sites

- `workflow_job_snapshot`
- `workflow_job_by_id`
- `home_page`
- `processing_page`
- `capture_queue_zero_touch_finished`
- `open_carduploader`
- `finish_carduploader_import`
- `set_current_pricing_job`

Each call site delegates to `self.workflow_application`. The UI rendering,
operator action mapping, background threads, queue processing, browser/folder
opening, pricing, capture, and inventory code remain in their prior owners.

## Behavior-Preservation Rules

- Cache duration remains eight seconds.
- Local discovery limit remains 60.
- Merged result limit remains 65.
- Completed-job limit remains 5.
- Existing job dictionaries and output shapes remain unchanged.
- Existing context JSON location and keys remain unchanged.
- Existing action strings and UI-visible states remain unchanged.
- Context persistence still uses the existing atomic temporary-file replace.

## Not Extracted

- Tkinter widgets or views
- `run_workflow_action` UI routing
- mobile queue thread/polling implementation
- Capture, Inventory, Marketplace Intelligence, Listings, or Shipping logic
- filesystem/persistence implementation
- configuration and path resolution
- production startup

These remain future, separately authorized migration work.
