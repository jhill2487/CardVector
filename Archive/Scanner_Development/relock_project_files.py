from __future__ import annotations
# Re-baselines the lock after a deliberate, verified geometry/layout change.
# For normal OCR/server patches, do NOT run this. Use verify_project_locks.py instead.
import install_project_locks

if __name__ == "__main__":
    install_project_locks.main()
