import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import check_architecture


class ArchitectureCheckerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.production = self.root / "Platform" / "App"
        self.production.mkdir(parents=True)
        (self.root / "Docs" / "Architecture").mkdir(parents=True)
        (self.root / "current.vbs").write_text("python app.py", encoding="utf-8")
        (self.production / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
        self.manifest_path = (
            self.root / "Docs" / "Architecture" / "manifest.json"
        )
        self.required_doc = self.root / "Docs" / "Architecture" / "required.md"
        self.required_doc.write_text("# Required\n", encoding="utf-8")
        self.write_manifest()

    def tearDown(self):
        self.temporary.cleanup()

    def write_manifest(self, **updates):
        owners = {name: f"owner.{name}" for name in check_architecture.REQUIRED_OWNERS}
        manifest = {
            "schema_version": "1.0",
            "architecture_version": "1.0",
            "approval_status": "test",
            "current_migration_phase": "test",
            "current_production_launcher": "current.vbs",
            "current_production_python_target": "Platform/App/app.py",
            "canonical_subsystem_ownership": owners,
            "approved_top_level_folders": ["Docs", "Platform"],
            "approved_production_package_roots": ["Platform/App"],
            "forbidden_production_filename_patterns": [
                "(^|[_ .-])(old|backup|copy|final|new|temp)([_ .-]|$)",
                "\\.(bak|backup|orig|tmp)$",
            ],
            "temporary_presentation_paths": [],
            "required_architecture_documents": [
                "Docs/Architecture/required.md"
            ],
        }
        manifest.update(updates)
        self.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    def scan(self):
        checker = check_architecture.ArchitectureChecker(
            self.root, self.manifest_path
        )
        return checker, checker.scan()

    def rules(self):
        _, findings = self.scan()
        return {item.rule for item in findings}

    def test_forbidden_filename_detection(self):
        (self.production / "pricing_backup.py").write_text("VALUE = 1\n")
        self.assertIn("files.forbidden_production_name", self.rules())

    def test_archive_import_detection(self):
        (self.production / "app.py").write_text("from Archive.old import value\n")
        self.assertIn("imports.archive", self.rules())

    def test_tkinter_layer_violation_detection(self):
        (self.production / "app.py").write_text("import tkinter\n")
        self.assertIn("layers.tkinter_outside_presentation", self.rules())

    def test_sys_path_mutation_detection(self):
        (self.production / "app.py").write_text(
            "import sys\nsys.path.insert(0, 'x')\n"
        )
        self.assertIn("imports.sys_path_mutation", self.rules())

    def test_hard_coded_absolute_path_detection(self):
        (self.production / "app.py").write_text(
            "ROOT = r'C:\\\\Users\\\\person\\\\project'\n"
        )
        self.assertIn("paths.hard_coded_absolute_windows", self.rules())

    def test_tracked_runtime_file_detection_without_git(self):
        log_path = self.root / "Platform" / "App" / "logs" / "run.log"
        log_path.parent.mkdir()
        log_path.write_text("runtime\n")
        self.assertIn("tracked.log", self.rules())

    def test_warning_and_strict_exit_behavior(self):
        (self.production / "app.py").write_text("import tkinter\n")
        checker, findings = self.scan()
        report = check_architecture.build_report(checker, findings, "warning")
        self.assertEqual(check_architecture.determine_exit_code(report, False), 0)
        self.assertEqual(check_architecture.determine_exit_code(report, True), 1)

    def test_established_baseline_passes_strict(self):
        (self.production / "app.py").write_text("import tkinter\n")
        checker = check_architecture.ArchitectureChecker(
            self.root, self.manifest_path, establish_baseline=True
        )
        report = check_architecture.build_report(
            checker, checker.scan(), "strict-establish-baseline"
        )
        self.assertEqual(check_architecture.determine_exit_code(report, True), 0)

    def test_saved_baseline_passes_strict(self):
        (self.production / "app.py").write_text("import tkinter\n")
        checker, findings = self.scan()
        baseline = self.root / "Docs" / "Architecture" / "baseline.json"
        baseline.write_text(
            json.dumps(
                {
                    "findings": [
                        {"fingerprint": item.fingerprint} for item in findings
                    ]
                }
            ),
            encoding="utf-8",
        )
        self.write_manifest(
            baseline_violation_snapshot="Docs/Architecture/baseline.json"
        )
        checker, findings = self.scan()
        report = check_architecture.build_report(checker, findings, "strict")
        self.assertTrue(all(item.pre_existing for item in findings))
        self.assertEqual(check_architecture.determine_exit_code(report, True), 0)

    def test_manifest_loading(self):
        checker, findings = self.scan()
        self.assertEqual(checker.manifest["schema_version"], "1.0")
        self.assertFalse(any(item.rule == "manifest.missing_key" for item in findings))

    def test_invalid_manifest_returns_checker_error(self):
        self.manifest_path.write_text("{", encoding="utf-8")
        command = [
            sys.executable,
            str(Path(check_architecture.__file__)),
            "--root",
            str(self.root),
            "--manifest",
            str(self.manifest_path),
        ]
        completed = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(completed.returncode, 2)

    def test_missing_document_detection(self):
        self.required_doc.unlink()
        self.assertIn("documentation.missing", self.rules())


if __name__ == "__main__":
    unittest.main()
