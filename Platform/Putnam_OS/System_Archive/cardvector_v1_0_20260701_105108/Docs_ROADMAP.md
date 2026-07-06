# Putnam Roadmap

`ROADMAP.md` defines tomorrow: planned direction, accepted future work, and
success criteria.

Current state belongs in `Docs/PROJECT_STATUS.md`.

## Phase 1 - Listing Pipeline Integration

### Objective

Create a seamless workflow from CardUploader into Putnam OS and then into eBay.

### Workflow

```text
Card
v
CardUploader
v
Putnam OS
v
Listing Optimizer
v
eBay Ready CSV
v
eBay Upload
```

### Deliverables

- Reliable CardUploader import
- Inventory record generation
- SKU assignment
- ETB location assignment
- Batch management
- Pricing engine
- Shipping policy validation
- Export validation
- Export logging
- Error reporting

### Success Criteria

A CardUploader export can be converted into an eBay-ready CSV with zero manual
spreadsheet editing.

Every imported card receives a valid inventory record, SKU, and location.

The export process is repeatable, reliable, and auditable.

### Scope Note

Card recognition and OCR are intentionally outside the scope of Putnam OS.

CardUploader is the current card recognition solution.

Putnam OS begins after card identification.
