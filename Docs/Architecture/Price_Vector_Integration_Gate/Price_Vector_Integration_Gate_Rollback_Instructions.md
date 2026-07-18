# Price Vector Integration Gate Rollback Instructions

## Recovery Reference

The pre-integration `main` state is preserved by the local lightweight tag:

```text
cardvector-pre-price-vector-integration
  -> bc67c72f2765b4dfe0bf5eaaf51d58764960a1a1
```

The integrated implementation commit is:

```text
aaf9a0f49b779a02f720fd99610183a5026b5ef9
```

## Safe Inspection Or Recovery Branch

To inspect the exact pre-integration source without changing `main`:

```powershell
git switch -c codex/recover-pre-price-vector `
  cardvector-pre-price-vector-integration
```

This creates a new recovery branch at the protected baseline and leaves all
existing commits intact.

## Revert On Main

If the integration must be removed after further commits or after publication,
use a normal revert rather than resetting or rewriting history:

```powershell
git switch main
git status
git revert aaf9a0f49b779a02f720fd99610183a5026b5ef9
```

If the separate integration-gate documentation commit must also be removed,
revert that documentation commit first, then revert `aaf9a0f`.

## Validation After Rollback

1. Confirm the official production launcher still targets `putnam_os.py`.
2. Compile `main.py` and `putnam_os.py`.
3. Run the Phase 2 application-layer tests.
4. Run the pricing compatibility smoke test.
5. Run architecture warning and strict checks.
6. Confirm `git status` is clean.
7. Confirm the expected prior commit is an ancestor of `HEAD`.

## Data And External Systems

The gate did not migrate production data, execute the pricing migration against
a production database, publish marketplace changes, upload captures, or change
external systems. Rollback therefore requires no database or marketplace
reversal.

The recovery tag is local and has not been pushed. Preserve it until the
integration has been reviewed and published successfully.
