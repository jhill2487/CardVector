"""Read-only CardVector architecture guardrail scanner.

Default mode reports all findings and exits zero. Strict mode exits one when a
finding is not present in the approved baseline snapshot. Scanner/configuration
errors exit two. The checker never modifies repository files.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import subprocess
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence


DEFAULT_MANIFEST = Path("Docs/Architecture/cardvector_architecture_manifest.json")
SEVERITY_ORDER = {"info": 0, "warning": 1, "error": 2, "critical": 3}
SKIP_DIR_NAMES = {
    ".git",
    ".idea",
    ".pytest_cache",
    ".venv",
    ".vscode",
    "__pycache__",
    "node_modules",
}
LAUNCHER_SUFFIXES = {".bat", ".cmd", ".ps1", ".vbs"}
RUNTIME_IMPORT_ROOTS = {
    "Business",
    "Capture",
    "Data",
    "MobileCapture",
    "Work_Sessions",
}
REQUIRED_OWNERS = {
    "application_startup",
    "desktop_shell",
    "workflow_orchestration",
    "shared_domain_models",
    "capture",
    "scanner_recognition",
    "inventory",
    "marketplace_intelligence",
    "fair_market_value",
    "price_vector",
    "listings",
    "orders",
    "shipping",
    "reporting",
    "configuration",
    "paths",
    "logging",
    "persistence",
    "external_integrations",
    "compatibility",
}


@dataclass
class Finding:
    rule: str
    path: str
    severity: str
    message: str
    pre_existing: bool = False
    blocks_migration: bool = False
    remediation_phase: str = "future architecture migration"
    false_positive_status: str = "not reviewed"
    notes: str = ""
    fingerprint: str = ""

    def finalize(self) -> "Finding":
        material = f"{self.rule}\0{self.path}\0{self.message}"
        self.fingerprint = hashlib.sha256(material.encode("utf-8")).hexdigest()[:20]
        return self


class ArchitectureChecker:
    """Inspect a repository against its CardVector architecture manifest."""

    def __init__(
        self,
        root: Path,
        manifest_path: Path | None = None,
        establish_baseline: bool = False,
    ) -> None:
        self.root = root.resolve()
        candidate = manifest_path or DEFAULT_MANIFEST
        self.manifest_path = (
            candidate if candidate.is_absolute() else self.root / candidate
        )
        self.manifest = self._load_manifest()
        self.establish_baseline = establish_baseline
        self.errors: list[str] = []
        self._baseline_fingerprints = self._load_baseline_fingerprints()
        self._tracked_cache: list[str] | None = None

    def _load_manifest(self) -> dict[str, Any]:
        try:
            content = self.manifest_path.read_text(encoding="utf-8")
            manifest = json.loads(content)
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(
                f"Unable to load architecture manifest {self.manifest_path}: {exc}"
            ) from exc
        if not isinstance(manifest, dict):
            raise ValueError("Architecture manifest root must be a JSON object.")
        return manifest

    def _load_baseline_fingerprints(self) -> set[str]:
        baseline_value = self.manifest.get("baseline_violation_snapshot")
        if not baseline_value:
            return set()
        baseline_path = self.root / str(baseline_value)
        if not baseline_path.exists():
            return set()
        try:
            payload = json.loads(baseline_path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            return set()
        return {
            item.get("fingerprint", "")
            for item in payload.get("findings", [])
            if isinstance(item, dict) and item.get("fingerprint")
        }

    def _relative(self, path: Path) -> str:
        try:
            return path.resolve().relative_to(self.root).as_posix()
        except (OSError, ValueError):
            return path.as_posix()

    def _finding(
        self,
        rule: str,
        path: str,
        severity: str,
        message: str,
        *,
        blocks_migration: bool = False,
        remediation_phase: str = "future architecture migration",
        notes: str = "",
    ) -> Finding:
        finding = Finding(
            rule=rule,
            path=path,
            severity=severity,
            message=message,
            blocks_migration=blocks_migration,
            remediation_phase=remediation_phase,
            notes=notes,
        ).finalize()
        if path.replace("\\", "/").startswith("Archive/") and rule.startswith(
            "tracked."
        ):
            finding.false_positive_status = "contextual archive exception candidate"
            finding.notes = (
                "The rule is accurate, but this item is inside the historical "
                "archive rather than an active production package."
            )
        finding.pre_existing = (
            self.establish_baseline
            or finding.fingerprint in self._baseline_fingerprints
        )
        return finding

    def _iter_files(self, roots: Iterable[str], suffixes: set[str] | None = None):
        seen: set[Path] = set()
        for value in roots:
            base = self.root / value
            if not base.exists():
                continue
            if base.is_file():
                candidates = [base]
            else:
                candidates = []
                for current, dirs, files in os.walk(base):
                    dirs[:] = [
                        name
                        for name in dirs
                        if name not in SKIP_DIR_NAMES
                        and not name.lower().endswith((".egg-info", ".dist-info"))
                    ]
                    candidates.extend(Path(current) / name for name in files)
            for path in candidates:
                if path in seen:
                    continue
                seen.add(path)
                if suffixes is None or path.suffix.lower() in suffixes:
                    yield path

    def _production_python_files(self) -> list[Path]:
        roots = self.manifest.get("approved_production_package_roots", [])
        return list(self._iter_files(roots, {".py"}))

    def _tracked_files(self) -> list[str]:
        if self._tracked_cache is not None:
            return self._tracked_cache
        try:
            completed = subprocess.run(
                ["git", "ls-files", "-z"],
                cwd=self.root,
                check=True,
                capture_output=True,
                text=False,
            )
            values = completed.stdout.decode("utf-8", errors="replace").split("\0")
            tracked = [value.replace("\\", "/") for value in values if value]
        except (OSError, subprocess.CalledProcessError):
            tracked = [
                self._relative(path)
                for path in self._iter_files(["."], suffixes=None)
            ]
        self._tracked_cache = tracked
        return tracked

    @staticmethod
    def _read_text(path: Path) -> str | None:
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None

    @staticmethod
    def _parse_tree(path: Path, text: str) -> ast.AST | None:
        try:
            return ast.parse(text, filename=str(path))
        except SyntaxError:
            return None

    def scan(self) -> list[Finding]:
        findings: list[Finding] = []
        checks = (
            self._check_manifest,
            self._check_required_documents,
            self._check_top_level_folders,
            self._check_python_sources,
            self._check_entry_points,
            self._check_launcher_targets,
            self._check_forbidden_filenames,
            self._check_tracked_runtime_files,
        )
        for check in checks:
            try:
                findings.extend(check())
            except Exception as exc:  # The audit should continue after one rule fails.
                self.errors.append(f"{check.__name__}: {type(exc).__name__}: {exc}")
        return sorted(
            findings,
            key=lambda item: (
                -SEVERITY_ORDER.get(item.severity, 0),
                item.rule,
                item.path.lower(),
                item.message,
            ),
        )

    def _check_manifest(self) -> list[Finding]:
        findings: list[Finding] = []
        required_keys = {
            "schema_version",
            "architecture_version",
            "approval_status",
            "current_migration_phase",
            "current_production_launcher",
            "current_production_python_target",
            "canonical_subsystem_ownership",
            "approved_top_level_folders",
            "approved_production_package_roots",
        }
        for key in sorted(required_keys - set(self.manifest)):
            findings.append(
                self._finding(
                    "manifest.missing_key",
                    self._relative(self.manifest_path),
                    "error",
                    f"Required manifest key is missing: {key}",
                    blocks_migration=True,
                    remediation_phase="Phase 1",
                )
            )

        for key in ("current_production_launcher", "current_production_python_target"):
            value = self.manifest.get(key)
            if value and not (self.root / str(value)).exists():
                findings.append(
                    self._finding(
                        "manifest.missing_current_path",
                        str(value),
                        "critical",
                        f"Manifest {key} does not exist.",
                        blocks_migration=True,
                        remediation_phase="Phase 1",
                    )
                )

        owners = self.manifest.get("canonical_subsystem_ownership", {})
        missing_owners = sorted(REQUIRED_OWNERS - set(owners))
        for owner in missing_owners:
            findings.append(
                self._finding(
                    "ownership.missing",
                    self._relative(self.manifest_path),
                    "error",
                    f"Canonical ownership is missing for: {owner}",
                    blocks_migration=True,
                    remediation_phase="Phase 1",
                )
            )
        return findings

    def _check_required_documents(self) -> list[Finding]:
        findings: list[Finding] = []
        for value in self.manifest.get("required_architecture_documents", []):
            if not (self.root / value).exists():
                findings.append(
                    self._finding(
                        "documentation.missing",
                        str(value),
                        "error",
                        "Required architecture document or tool is missing.",
                        blocks_migration=True,
                        remediation_phase="Phase 1",
                    )
                )
        return findings

    def _check_top_level_folders(self) -> list[Finding]:
        approved = set(self.manifest.get("approved_top_level_folders", []))
        findings: list[Finding] = []
        try:
            children = list(self.root.iterdir())
        except OSError as exc:
            self.errors.append(f"top-level listing failed: {exc}")
            return findings
        for child in children:
            if not child.is_dir() or child.name.startswith("."):
                continue
            if child.name not in approved:
                findings.append(
                    self._finding(
                        "repository.unapproved_top_level_folder",
                        child.name,
                        "warning",
                        "Top-level folder is not listed in the architecture manifest.",
                        remediation_phase="Phase 10",
                    )
                )
        return findings

    def _check_python_sources(self) -> list[Finding]:
        findings: list[Finding] = []
        approved_tkinter = {
            value.replace("\\", "/")
            for value in self.manifest.get("temporary_presentation_paths", [])
        }
        absolute_path_pattern = re.compile(
            r"(?i)(?:[a-z]:[\\/]+(?:users|documents and settings|programdata|temp)[\\/]+[^\"'\r\n]+)"
        )

        for path in self._production_python_files():
            relative = self._relative(path)
            text = self._read_text(path)
            if text is None:
                self.errors.append(f"unable to read Python source: {relative}")
                continue
            tree = self._parse_tree(path, text)
            if tree is None:
                findings.append(
                    self._finding(
                        "python.syntax_unreadable",
                        relative,
                        "error",
                        "Python source cannot be parsed for architecture inspection.",
                        blocks_migration=True,
                        remediation_phase="active feature checkpoint",
                    )
                )
                continue

            imports: list[str] = []
            tkinter_import = False
            sys_path_mutation = False
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
                elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    owner = node.func.value
                    if (
                        isinstance(owner, ast.Attribute)
                        and isinstance(owner.value, ast.Name)
                        and owner.value.id == "sys"
                        and owner.attr == "path"
                        and node.func.attr in {"append", "extend", "insert"}
                    ):
                        sys_path_mutation = True

            for imported in imports:
                root_name = imported.split(".", 1)[0]
                if root_name.lower() in {"archive", "archives"}:
                    findings.append(
                        self._finding(
                            "imports.archive",
                            relative,
                            "critical",
                            f"Production source imports archived code: {imported}",
                            blocks_migration=True,
                            remediation_phase="Phase 1/new debt",
                        )
                    )
                if root_name in RUNTIME_IMPORT_ROOTS:
                    findings.append(
                        self._finding(
                            "imports.runtime_data",
                            relative,
                            "error",
                            f"Production source imports a runtime-data root: {imported}",
                            remediation_phase="Phase 4",
                        )
                    )
                if root_name in {"tkinter", "Tkinter"}:
                    tkinter_import = True

            if tkinter_import and relative not in approved_tkinter:
                findings.append(
                    self._finding(
                        "layers.tkinter_outside_presentation",
                        relative,
                        "error",
                        "Tkinter is imported outside an approved temporary presentation path.",
                        remediation_phase="Phase 8",
                    )
                )

            if sys_path_mutation:
                findings.append(
                    self._finding(
                        "imports.sys_path_mutation",
                        relative,
                        "error",
                        "Production source mutates sys.path.",
                        remediation_phase="Phase 2-4",
                    )
                )

            if absolute_path_pattern.search(text):
                findings.append(
                    self._finding(
                        "paths.hard_coded_absolute_windows",
                        relative,
                        "error",
                        "Production source contains a machine-specific absolute Windows path.",
                        remediation_phase="Phase 2-4",
                    )
                )
        return findings

    def _check_entry_points(self) -> list[Finding]:
        candidates: list[str] = []
        main_guard = re.compile(
            r"if\s+__name__\s*==\s*['\"]__main__['\"]\s*:"
        )
        for path in self._production_python_files():
            text = self._read_text(path)
            if text is None:
                continue
            if main_guard.search(text) and (
                "tkinter" in text or re.search(r"\b(?:tk|tkinter)\.Tk\s*\(", text)
            ):
                candidates.append(self._relative(path))
        if len(candidates) <= 1:
            return []
        return [
            self._finding(
                "entry_points.multiple_gui",
                "<repository>",
                "error",
                f"Multiple likely Python GUI entry points detected ({len(candidates)}): "
                + ", ".join(sorted(candidates)),
                remediation_phase="Phase 3, 8-10",
            )
        ]

    def _check_launcher_targets(self) -> list[Finding]:
        targets: dict[str, list[str]] = {}
        for relative in self._tracked_files():
            path = self.root / relative
            if path.suffix.lower() not in LAUNCHER_SUFFIXES:
                continue
            parts = set(Path(relative).parts)
            if parts & {"Archive", "Docs", "Tools", "Work_Sessions"}:
                continue
            text = self._read_text(path)
            if text is None:
                continue
            found = set(
                match.replace("\\", "/")
                for match in re.findall(
                    r"(?i)(?:[A-Za-z0-9_./\\ -]+\.py|(?:py|python)\s+-m\s+[A-Za-z0-9_.]+)",
                    text,
                )
            )
            for target in found:
                normalized = re.sub(r"\s+", " ", target.strip())
                targets.setdefault(normalized, []).append(relative)
        if len(targets) <= 1:
            return []
        summary = "; ".join(
            f"{target} <- {', '.join(sorted(paths))}"
            for target, paths in sorted(targets.items())
        )
        return [
            self._finding(
                "entry_points.multiple_launcher_targets",
                "<repository>",
                "warning",
                f"Multiple launcher targets detected: {summary}",
                remediation_phase="Phase 3 and Phase 10",
            )
        ]

    def _check_forbidden_filenames(self) -> list[Finding]:
        patterns = [
            re.compile(value, re.IGNORECASE)
            for value in self.manifest.get("forbidden_production_filename_patterns", [])
        ]
        findings: list[Finding] = []
        roots = self.manifest.get("approved_production_package_roots", [])
        for path in self._iter_files(roots):
            if path.name.lower().startswith("test_"):
                continue
            if not any(pattern.search(path.name) for pattern in patterns):
                continue
            findings.append(
                self._finding(
                    "files.forbidden_production_name",
                    self._relative(path),
                    "warning",
                    "Production filename matches a forbidden backup/version pattern.",
                    remediation_phase="Phase 10",
                )
            )
        return findings

    def _check_tracked_runtime_files(self) -> list[Finding]:
        findings: list[Finding] = []
        for relative in self._tracked_files():
            lower = relative.lower()
            path = Path(relative)
            parts = {part.lower() for part in path.parts}
            suffix = path.suffix.lower()
            rule = ""
            message = ""
            severity = "warning"

            if "__pycache__" in parts or suffix in {".pyc", ".pyo"}:
                rule = "tracked.cache"
                message = "Cache artifact is tracked by Git."
            elif "logs" in parts or suffix == ".log":
                rule = "tracked.log"
                message = "Log artifact is tracked by Git."
            elif suffix in {".tmp", ".bak", ".backup", ".orig"}:
                rule = "tracked.temporary"
                message = "Temporary or backup artifact is tracked by Git."
            elif suffix in {".db", ".sqlite", ".sqlite3"}:
                if {"tests", "fixtures", "samples"} & parts:
                    continue
                rule = "tracked.runtime_database"
                message = "Local runtime database is tracked outside an approved fixture path."
                severity = "error"
            elif (
                path.parts
                and path.parts[0] in {"Capture", "MobileCapture", "Work_Sessions"}
                and (
                    lower.endswith(".json")
                    or lower.endswith(".csv")
                    or lower.endswith(".jpg")
                    or lower.endswith(".jpeg")
                    or lower.endswith(".png")
                )
            ):
                rule = "tracked.runtime_data"
                message = "Generated operational data is tracked in a runtime root."

            if rule:
                findings.append(
                    self._finding(
                        rule,
                        relative,
                        severity,
                        message,
                        remediation_phase="Phase 10-11",
                    )
                )
        return findings


def build_report(
    checker: ArchitectureChecker,
    findings: Sequence[Finding],
    mode: str,
) -> dict[str, Any]:
    counts = Counter(item.severity for item in findings)
    return {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(),
        "repository_root": ".",
        "manifest": checker._relative(checker.manifest_path),
        "mode": mode,
        "summary": {
            "total": len(findings),
            "critical": counts["critical"],
            "error": counts["error"],
            "warning": counts["warning"],
            "info": counts["info"],
            "pre_existing": sum(item.pre_existing for item in findings),
            "new": sum(not item.pre_existing for item in findings),
            "checker_errors": len(checker.errors),
        },
        "checker_errors": checker.errors,
        "findings": [asdict(item) for item in findings],
    }


def format_text(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "CardVector Architecture Check",
        f"Mode: {report['mode']}",
        (
            "Findings: "
            f"{summary['total']} "
            f"(critical {summary['critical']}, error {summary['error']}, "
            f"warning {summary['warning']}, info {summary['info']})"
        ),
        f"Baseline: {summary['pre_existing']} pre-existing, {summary['new']} new",
    ]
    for item in report["findings"]:
        baseline = "baseline" if item["pre_existing"] else "new"
        lines.append(
            f"[{item['severity'].upper()}] {item['rule']} "
            f"({baseline}) {item['path']}: {item['message']}"
        )
    for error in report["checker_errors"]:
        lines.append(f"[CHECKER ERROR] {error}")
    return "\n".join(lines) + "\n"


def format_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Phase 1 Architecture Baseline",
        "",
        f"- **Generated:** {report['generated_at']}",
        f"- **Mode:** {report['mode']}",
        f"- **Total findings:** {summary['total']}",
        f"- **Critical:** {summary['critical']}",
        f"- **Error:** {summary['error']}",
        f"- **Warning:** {summary['warning']}",
        f"- **Info:** {summary['info']}",
        f"- **Pre-existing:** {summary['pre_existing']}",
        f"- **New:** {summary['new']}",
        "",
        "Existing findings are recorded, not fixed, by Phase 1. A baseline item",
        "does not become approved architecture merely because it is recorded.",
        "",
        "## Findings",
        "",
        "| Severity | Rule | Path | Pre-existing | Blocks migration | Future phase | False-positive status | Notes |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in report["findings"]:
        values = [
            item["severity"].upper(),
            item["rule"],
            f"`{item['path']}`",
            "Yes" if item["pre_existing"] else "No",
            "Yes" if item["blocks_migration"] else "No",
            item["remediation_phase"],
            item["false_positive_status"],
            item["message"].replace("|", "\\|"),
        ]
        lines.append("| " + " | ".join(values) + " |")
    if not report["findings"]:
        lines.append("| - | - | - | - | - | - | - | No findings |")
    lines.extend(["", "## Checker Errors", ""])
    if report["checker_errors"]:
        lines.extend(f"- {value}" for value in report["checker_errors"])
    else:
        lines.append("None.")
    return "\n".join(lines) + "\n"


def determine_exit_code(
    report: dict[str, Any],
    strict: bool,
) -> int:
    if report.get("checker_errors"):
        return 2
    if strict and any(not item["pre_existing"] for item in report["findings"]):
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read-only CardVector architecture rule checker."
    )
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument(
        "--format",
        choices=("text", "json", "markdown"),
        default="text",
    )
    parser.add_argument(
        "--establish-baseline",
        action="store_true",
        help="Mark current findings pre-existing in output without writing files.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        checker = ArchitectureChecker(
            root=args.root,
            manifest_path=args.manifest,
            establish_baseline=args.establish_baseline,
        )
        findings = checker.scan()
    except ValueError as exc:
        print(f"Architecture checker error: {exc}", file=sys.stderr)
        return 2
    mode = "strict" if args.strict else "warning"
    if args.establish_baseline:
        mode = f"{mode}-establish-baseline"
    report = build_report(checker, findings, mode)
    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=False))
    elif args.format == "markdown":
        print(format_markdown(report), end="")
    else:
        print(format_text(report), end="")
    return determine_exit_code(report, strict=args.strict)


if __name__ == "__main__":
    raise SystemExit(main())
