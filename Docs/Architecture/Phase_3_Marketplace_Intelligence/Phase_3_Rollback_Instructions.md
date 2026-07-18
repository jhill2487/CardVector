# Phase 3 Rollback Instructions

## Baseline

Starting commit:
`c289a979ac3ee251d729fa9f288a06afb4d51573`

Recovery reference:
`cardvector-pre-price-vector-integration`

## Preferred Rollback

After Phase 3 commits exist, use normal Git reverts in reverse commit order.
Do not reset shared history.

```powershell
git revert <phase-3-docs-commit>
git revert <phase-3-tests-commit>
git revert <phase-3-implementation-commit>
```

If commits are combined, revert the single Phase 3 commit.

## Verification After Rollback

1. Confirm `putnam_os.py`, `main.py`, and the bulk engine import the historical
   pricing path.
2. Confirm `Platform/cardvector/marketplace_intelligence` and
   `Platform/cardvector/application/pricing.py` are absent.
3. Run FMV separation and pricing consolidation tests.
4. Run application, Marketplace Intelligence, and desktop workflow smoke tests.
5. Confirm production launcher SHA-256 is
   `AD5044D8D439CE6B321951E85A335DE86927AAA9453FE05DF0A23C1327006EE7`.
6. Run the architecture checker in strict mode.

No data rollback is required: Phase 3 did not write production databases or
change runtime data formats.
