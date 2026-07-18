# Phase 5 Recognition/Inventory Handoff

The verified production flow remains:

```text
CardVector Capture
  -> CardUploader recognition handoff
    -> CardUploader recognition and managed inventory
      -> CardUploader export
        -> CardVector snapshot/reconciliation/pricing views
```

CardVector does not implement recognition-to-inventory matching, duplicate
creation policy, image attachment, quantity mutation, or location assignment.
Existing capture metadata and CardUploader CSV fields are unchanged. No second
handoff was added.
