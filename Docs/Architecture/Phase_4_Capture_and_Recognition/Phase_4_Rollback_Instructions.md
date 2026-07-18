# Phase 4 Rollback Instructions

Phase 4 is delegation-first and does not move or delete the proven Capture
implementations.

## Before Commit

Review only the files listed by:

```powershell
git status --short
git diff -- Platform/Putnam_OS/System/app/putnam_os.py
```

Do not use destructive reset commands. Preserve unrelated work if any appears.

## After Commit

Create revert commits for the Phase 4 commits in reverse order:

```powershell
git revert <phase-4-docs-commit>
git revert <phase-4-test-commit>
git revert <phase-4-production-commit>
```

Then rerun:

```powershell
py Platform\Putnam_OS\System\app\test_capture_studio_v1.py
py Platform\Putnam_OS\System\app\test_auto_capture_v2_1.py
py -m unittest Platform.Putnam_OS.System.tools.test_mobile_capture_queue
```

Reversion restores direct construction and embedded helper logic in
`putnam_os.py`. The unchanged Capture Studio, mobile queue, OBS manager,
standalone tools, mobile site, Supabase migrations, and launcher remain
available throughout rollback.
