# CardVector Roadmap

`ROADMAP.md` defines tomorrow: planned direction, accepted future work, and
success criteria.

Current state belongs in `Docs/PROJECT_STATUS.md`.

## Highest Priority

1. CardVector Platform Rebrand
2. Capture Studio v2
3. CardVector Pricing Engine Marketplace Intelligence
4. Workflow Polish
5. Inventory Improvements
6. Mobile Companion
7. Inventory Transactions

## Phase 1 - Listing Pipeline Integration

### Objective

Create a seamless workflow from CardUploader into CardVector OS and then into eBay.

### Workflow

```text
Card
v
CardUploader
v
CardVector OS
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

Card recognition and OCR are intentionally outside the scope of CardVector OS.

CardUploader is the current card recognition solution.

CardVector OS begins after card identification.
