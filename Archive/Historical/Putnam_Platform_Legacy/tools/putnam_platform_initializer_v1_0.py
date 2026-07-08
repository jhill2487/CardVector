from pathlib import Path
from datetime import datetime
import os

VERSION = "v1.0"

def write_if_missing(path: Path, content: str):
    if not path.exists():
        path.write_text(content, encoding="utf-8")
        return "created"
    return "exists"

def main():
    root_env = os.environ.get("USERENVIRONMENT")
    if not root_env:
        raise SystemExit("USERENVIRONMENT is not set.")

    root = Path(root_env)
    root.mkdir(parents=True, exist_ok=True)

    folders = [
        "Archive",
        "config",
        "docs",
        "Shared",
        "Putnam_Platform",
        "Putnam_Platform/tools",
        "Putnam_Platform/docs",
        "Putnam_Standards",
        "Putnam_Content",
        "TCG_Automation",
        "Pokemon_Live_Price_Lookup",
        "Putnam_Scanner",
        "Putnam_Listing_Optimizer",
    ]

    created = []
    for folder in folders:
        p = root / folder
        p.mkdir(parents=True, exist_ok=True)
        created.append(str(p))

    write_if_missing(root / ".putnam_root", "Putnam Collectibles platform root\n")

    project_index = f"""# Putnam Project Index

Root:
%USERENVIRONMENT%

Last Updated:
{datetime.now().strftime('%Y-%m-%d %H:%M')}

## Active

| Project | Status | Notes |
|---|---|---|
| Putnam_Platform | Active | Maintains root structure and standards |
| Putnam_Content | Active | Build-in-public YouTube/content operation |
| TCG_Automation | Active | Existing automation workspace |

## Shelved

| Project | Status | Notes |
|---|---|---|
| Pokemon_Live_Price_Lookup | Shelved | Shelved due to eBay-first strategy |
| Putnam_Scanner | Shelved | CardUploader currently handles recognition |
| Putnam_Listing_Optimizer | Shelved / Review | Not needed as title generator; possible future audit role |

## Planned

| Project | Status | Notes |
|---|---|---|
| Warehouse_System | Planned | Physical inventory / ETB location system |
| Economics_Dashboard | Planned | eBay-first business analytics |
"""
    write_if_missing(root / "PROJECT_INDEX.md", project_index)

    readme = """# Putnam Collectibles Platform

This folder is the root source of truth for Putnam Collectibles projects.

All tools should resolve paths from USERENVIRONMENT or locate this folder by finding `.putnam_root`.

Current priority:
1. eBay listing volume
2. CardUploader workflow
3. Warehouse / inventory system
4. Content documentation
5. Business analytics
"""
    write_if_missing(root / "README.md", readme)

    standards = """# Putnam Standards

## Current Core Standards

1. USERENVIRONMENT portability
2. Standard project folders
3. Script save/run instructions
4. Versioning and changelogs
5. Production-first tools
6. Constructive pushback
7. Project state files
8. Master project index
9. Project files are source of truth
10. Systems before scale
11. Business before content
12. Equipment purchases must remove bottlenecks
13. Documentary authenticity
14. Consistency over perfection
15. Repeatable workflows
16. Modular architecture
17. Authenticity advantage
18. Decision logs
19. No duplicate code
20. Installable projects
21. AI-friendly documentation
22. Integrate before reinventing
23. Business strategy drives software priorities
24. No sunk cost development
25. Build around the bottleneck
26. Opportunity cost first
27. Work first, document always
28. Every session ends with a business deliverable
"""
    write_if_missing(root / "Putnam_Standards" / "PUTNAM_STANDARDS.md", standards)

    report = root / "Putnam_Platform" / "docs" / f"platform_initializer_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    report.write_text(
        "Putnam Platform Initializer v1.0 completed.\n\n"
        f"Root: {root}\n\n"
        "Folders verified:\n" + "\n".join(created),
        encoding="utf-8"
    )

    print("Putnam Platform Initializer v1.0 complete.")
    print(f"Root: {root}")
    print(f"Report: {report}")

if __name__ == "__main__":
    main()
