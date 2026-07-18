# Phase 0 Change Classification

## A. Architecture Audit and Planning Package

Scope:

- 16 files under `Docs/Architecture/`
- 8 audit reports under `Docs/Reports/`
- The Phase 0 baseline documents in this directory

Assessment:

- Intentional and internally consistent.
- Cleanly separable from application feature work.
- Contains no detected token, key, private key, JWT, or literal credential.
- Three audit reports contain four absolute `C:\Users\...` path references.
  These are machine-specific documentation references, not credentials. A
  later documentation-only cleanup should make them portable.
- Safe to preserve in a documentation-only commit.

## B. Price Vector / eBay Work

Scope:

- 11 modified Python files across Marketplace Intelligence and Putnam OS
- 1 modified JSON configuration file
- 1 new pricing repository
- 1 new SQL migration
- 2 new pricing tests
- 4 Price Vector planning/audit documents

Assessment:

- The work is intentional and connected: Marketplace Intelligence becomes the
  canonical calculator, Putnam OS delegates to it, FMV/recommendation/final
  price become distinct values, and active-listing CSV compatibility is added.
- `main.py` currently has an unterminated f-string at line 650.
- The consolidation test imports `main.py` and therefore cannot run.
- The feature work is not safe to label as complete or commit to `main` as a
  validated feature checkpoint.
- Preserve it unchanged as WIP using a named recovery base plus a binary Git
  patch and archive of untracked feature files.

## C. Other Unrelated Work

### Configuration

`putnam_os_config.json` changes seven keys:

- `putnam_os.carduploader_url`
- `putnam_os.ebay_seller_hub_url`
- `putnam_os.ebay_upload_url`
- `putnam_os.mobile_capture_url`
- `putnam_os.pricing_auto_apply_threshold`
- `putnam_os.pricing_review_threshold`
- `putnam_os.pricing_strategy`

No absolute local path or secret pattern was detected. The values appear
related to active feature work, but the file is user configuration and requires
owner review before source control treatment.

### Business Evidence

Three insurance-claim JPG files are intentional-looking operator data, not
source. They must remain untracked and preserved in place.

### Developer Artifacts

Three timestamped `.bak` files and one root patch script are evidence of the
active eBay patch process. They are useful for recovery but violate the target
production-file standards. Preserve them in the WIP recovery archive; do not
include them in a production source commit.

## Sensitive and Machine-Specific Scan

Scanned changed and untracked text files for:

- private keys
- GitHub/OpenAI-style tokens
- JWTs
- bearer credentials
- credential assignments
- absolute Windows user paths

Results:

- No private key, PAT, API token, JWT, bearer value, or literal credential was
  detected.
- `putnam_os.py:8209` was a false positive: it reads the password field from
  the existing OBS settings UI and contains no password value.
- Machine-specific absolute paths occur in:
  - `Docs/PriceVector/current_code_audit.md`
  - `Docs/Reports/Architecture_Audit.md`
  - `Docs/Reports/Dead_Code_Report.md`
  - `Docs/Reports/Entry_Point_Report.md`
- The three JPG files are potentially sensitive business evidence based on
  their folder and filenames.

## Proposed Disposition

| Group | Immediate action | Eventual action |
| --- | --- | --- |
| Architecture package | Commit separately | Keep as governed documentation |
| Price Vector/eBay tracked changes | Preserve by patch; do not feature-commit while syntax is invalid | Repair and validate in a separately approved feature task |
| Price Vector untracked files | Preserve in local WIP archive | Commit with coherent feature after validation |
| Configuration | Preserve in patch and working tree | Owner decides commit vs local config |
| Business JPGs | Leave in place; record hashes | Define business-data ignore/retention policy |
| `.bak` and patch script | Preserve in WIP archive | Archive outside production source or ignore after owner review |
