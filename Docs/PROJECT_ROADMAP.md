# PROJECT_ROADMAP.md

**Status:** Canonical

# Purpose

This roadmap defines the future direction of CardVector.

It tracks planned work only. Architectural decisions belong in PROJECT_MANUAL.md.

---

# Guiding Principles

All roadmap items should:

- Respect the established architecture.
- Improve measurable business value.
- Reduce operator effort.
- Preserve workflow stability.
- Be validated in production.

Current desktop direction:

- CardVector OS is a workflow conductor, not a replacement for CardUploader or eBay.
- The production path is Capture -> CardUploader -> Processing -> eBay.
- Home remains limited to actionable pending work and active-listings freshness.

---

# Active Epic 1 — Order Fulfillment Foundation

Priority: Highest

Objectives:

- Order import
- Pick workflow
- ETB/Location lookup
- Occupancy updates
- Pick verification
- Packing workflow support

Status:
Planned

---

# Active Epic 2 — Marketplace Integration

Objectives:

- eBay improvements
- TCGplayer improvements
- Reconciliation
- Future marketplace providers

Status:
In Progress

---

# Active Epic 3 — Mobile Platform

Objectives:

- QR workflows
- Mobile inventory lookup
- Mobile fulfillment support
- Mobile inventory movement

Status:
In Progress

Current production capability:

- Mobile Capture can submit authenticated phone captures to Supabase.
- CardVector OS includes a Capture Queue workspace for reviewing,
  claiming, staging, retrying, and completing Mobile Capture sessions through
  the existing Physical Inventory Conversion workflow.
- Mobile entry supports direct location QR, main ETB QR, and no-QR capture
  setup through one shared capture implementation. Cloud location creation
  remains pending production migration activation and live mobile validation.
- Both mobile capture types support explicit Front only and Front + back photo
  modes. Paired sessions stage into the existing desktop capture-pair format.

Known limitations:

- Card recognition and CardUploader automation remain future work.
- Completion remains an explicit operator action after downstream conversion.
- Supabase Realtime is not used; desktop refresh is manual or conservative
  polling.

---

# Active Epic 4 — Reporting & Analytics

Objectives:

- Acquisition ROI
- Inventory aging
- ETB utilization
- Sell-through metrics
- Business dashboards

Status:
Planned

---

# Active Epic 5 — Automation

Objectives:

- Recognition improvements
- Import automation
- Operational automation
- Background processing

Status:
Ongoing

---

# Future Enhancements

Future work may include:

- Multi-user support
- Role-based permissions
- Additional hardware support
- Additional marketplace integrations
- Quality-of-life improvements
- ETB creation and broader storage-management redesign

These items should be implemented only when driven by demonstrated operational need.

---

# Roadmap Maintenance

The roadmap is a living document.

Completed work moves to DEVELOPMENT_LOG.md.

Architectural decisions move to PROJECT_MANUAL.md.

Historical roadmaps belong in Docs/Archive.
