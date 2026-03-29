#!/usr/bin/env python3
"""Regression tests for skill-xray deterministic scripts.

Tests pre-analyze.py and generate-report.py against fixture skills with
golden analysis/review JSON files. No LLM agents needed — runs in seconds.

Usage:
    python3 evals/test_regression.py              # from skill-xray dir
    python3 evals/test_regression.py -v            # verbose
    python3 evals/test_regression.py -k problematic  # run only matching tests
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURES_DIR = os.path.join(SKILL_DIR, "evals", "fixtures")
GOLDEN_DIR = os.path.join(SKILL_DIR, "evals", "golden")
SCRIPTS_DIR = os.path.join(SKILL_DIR, "scripts")
ASSETS_DIR = os.path.join(SKILL_DIR, "assets")


def run_script(args, check=True):
    result = subprocess.run(
        args, capture_output=True, text=True, cwd=SKILL_DIR
    )
    if check and result.returncode != 0:
        raise RuntimeError(
            f"Script failed (exit {result.returncode}):\n"
            f"  cmd: {' '.join(args)}\n"
            f"  stderr: {result.stderr}"
        )
    return result


class PreAnalyzeTests(unittest.TestCase):
    """Tests for scripts/pre-analyze.py"""

    def _run_pre_analyze(self, fixture_name):
        fixture_dir = os.path.join(FIXTURES_DIR, fixture_name)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            out_path = f.name
        try:
            run_script(["python3", f"{SCRIPTS_DIR}/pre-analyze.py", fixture_dir, out_path])
            with open(out_path) as f:
                return json.load(f)
        finally:
            os.unlink(out_path)

    def test_minimal_produces_valid_output(self):
        data = self._run_pre_analyze("minimal-skill")
        self.assertIn("file_tree", data)
        self.assertIn("frontmatter", data)
        self.assertIn("structural_spec_checks", data)
        self.assertIn("secret_scan", data)

    def test_minimal_frontmatter(self):
        data = self._run_pre_analyze("minimal-skill")
        fm = data["frontmatter"]
        self.assertEqual(fm["name"], "greeting-responder")
        self.assertEqual(fm["license"], "MIT")
        self.assertIsInstance(fm["description"], str)
        self.assertGreater(len(fm["description"]), 0)

    def test_minimal_file_count(self):
        data = self._run_pre_analyze("minimal-skill")
        self.assertEqual(data["total_files"], 1)
        self.assertEqual(len(data["file_tree"]), 1)
        self.assertEqual(data["file_tree"][0]["path"], "SKILL.md")

    def test_minimal_no_secrets(self):
        data = self._run_pre_analyze("minimal-skill")
        self.assertTrue(data["secret_scan"]["clean"])
        self.assertEqual(data["secret_scan"]["hit_count"], 0)

    def test_complex_detects_all_files(self):
        data = self._run_pre_analyze("complex-skill")
        self.assertEqual(data["total_files"], 3)
        paths = {f["path"] for f in data["file_tree"]}
        self.assertIn("SKILL.md", paths)
        self.assertIn("scripts/preprocess.py", paths)
        self.assertIn("references/analysis-guide.md", paths)

    def test_complex_allowed_tools(self):
        data = self._run_pre_analyze("complex-skill")
        tools = data["frontmatter"]["allowed_tools"]
        self.assertEqual(set(tools), {"Read", "Bash", "Write", "Glob"})

    def test_complex_has_scripts_and_references(self):
        data = self._run_pre_analyze("complex-skill")
        checks = data["structural_spec_checks"]
        self.assertTrue(checks["has_scripts_dir"])
        self.assertTrue(checks["has_references_dir"])
        self.assertTrue(checks["has_allowed_tools"])

    def test_complex_no_secrets(self):
        data = self._run_pre_analyze("complex-skill")
        self.assertTrue(data["secret_scan"]["clean"])

    def test_problematic_name_too_long(self):
        data = self._run_pre_analyze("problematic-skill")
        checks = data["structural_spec_checks"]
        self.assertFalse(checks["name_length_ok"])
        self.assertGreater(checks["name_length"], 64)

    def test_problematic_detects_secrets(self):
        data = self._run_pre_analyze("problematic-skill")
        scan = data["secret_scan"]
        self.assertFalse(scan["clean"])
        self.assertEqual(scan["hit_count"], 2)
        detectors = {h["detector"] for h in scan["hits"]}
        self.assertIn("anthropic-key", detectors)
        self.assertIn("aws-access-key", detectors)

    def test_problematic_secrets_are_redacted(self):
        data = self._run_pre_analyze("problematic-skill")
        for hit in data["secret_scan"]["hits"]:
            self.assertIn("***", hit["redacted"])
            self.assertNotIn("FAKE_KEY_FOR_TESTING", hit["redacted"])

    def test_problematic_no_allowed_tools(self):
        data = self._run_pre_analyze("problematic-skill")
        self.assertFalse(data["structural_spec_checks"]["has_allowed_tools"])
        self.assertEqual(data["frontmatter"]["allowed_tools"], [])


class GenerateReportTests(unittest.TestCase):
    """Tests for scripts/generate-report.py using golden analysis/review JSON."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="skill-xray-test-")
        # Pre-build the template once
        self.template_path = os.path.join(self.tmpdir, "built-template.html")
        run_script(["bash", f"{SCRIPTS_DIR}/build-template.sh", ASSETS_DIR, self.template_path])

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def _generate_report(self, fixture_name):
        fixture_dir = os.path.join(FIXTURES_DIR, fixture_name)
        work_dir = os.path.join(self.tmpdir, fixture_name)
        os.makedirs(work_dir)

        # Copy golden JSON
        golden_dir = os.path.join(GOLDEN_DIR, fixture_name)
        shutil.copy(os.path.join(golden_dir, "analysis.json"), work_dir)
        shutil.copy(os.path.join(golden_dir, "review.json"), work_dir)

        # Generate file-inventory.json fresh
        inv_path = os.path.join(work_dir, "file-inventory.json")
        run_script(["python3", f"{SCRIPTS_DIR}/pre-analyze.py", fixture_dir, inv_path])

        analysis_path = os.path.join(work_dir, "analysis.json")
        review_path = os.path.join(work_dir, "review.json")

        result = run_script([
            "python3", f"{SCRIPTS_DIR}/generate-report.py",
            analysis_path, review_path, self.template_path
        ])

        report_path = os.path.join(work_dir, "report.html")
        self.assertTrue(os.path.isfile(report_path), f"report.html not created for {fixture_name}")

        with open(report_path) as f:
            return f.read()

    def test_minimal_report_generated(self):
        html = self._generate_report("minimal-skill")
        self.assertGreater(len(html), 1000)

    def test_minimal_report_contains_skill_name(self):
        html = self._generate_report("minimal-skill")
        self.assertIn("greeting-responder", html)

    def test_minimal_report_contains_grade(self):
        html = self._generate_report("minimal-skill")
        self.assertIn("grade-A", html)

    def test_complex_report_contains_tools(self):
        html = self._generate_report("complex-skill")
        self.assertIn("Read", html)
        self.assertIn("Bash", html)
        self.assertIn("Write", html)

    def test_complex_report_contains_file_tree(self):
        html = self._generate_report("complex-skill")
        self.assertIn("preprocess.py", html)
        self.assertIn("analysis-guide.md", html)

    def test_complex_report_contains_summary(self):
        html = self._generate_report("complex-skill")
        self.assertIn("CSV analysis skill", html)

    def test_problematic_report_contains_grade_f(self):
        html = self._generate_report("problematic-skill")
        self.assertIn("grade-F", html)

    def test_problematic_report_contains_errors(self):
        html = self._generate_report("problematic-skill")
        self.assertIn("Error", html)
        self.assertIn("Hardcoded", html)

    def test_problematic_report_contains_secret_alerts(self):
        html = self._generate_report("problematic-skill")
        self.assertIn("secret-alert", html)
        self.assertIn("Anthropic API Key", html)
        self.assertIn("AWS Access Key ID", html)

    def test_problematic_report_secrets_redacted_in_html(self):
        html = self._generate_report("problematic-skill")
        self.assertNotIn("FAKE_KEY_FOR_TESTING", html)
        self.assertNotIn("AKIAIOSFODNN7EXAMPLE", html)

    def test_report_rejects_invalid_analysis(self):
        """generate-report.py should fail on analysis.json missing required keys."""
        work_dir = os.path.join(self.tmpdir, "bad-analysis")
        os.makedirs(work_dir)

        with open(os.path.join(work_dir, "analysis.json"), "w") as f:
            json.dump({"skill_name": "test"}, f)

        shutil.copy(os.path.join(GOLDEN_DIR, "minimal-skill", "review.json"), work_dir)

        # Create empty file-inventory.json
        with open(os.path.join(work_dir, "file-inventory.json"), "w") as f:
            json.dump({}, f)

        result = run_script([
            "python3", f"{SCRIPTS_DIR}/generate-report.py",
            os.path.join(work_dir, "analysis.json"),
            os.path.join(work_dir, "review.json"),
            self.template_path
        ], check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing required key", result.stderr)

    def test_report_rejects_invalid_review(self):
        """generate-report.py should fail on review.json with invalid grade."""
        work_dir = os.path.join(self.tmpdir, "bad-review")
        os.makedirs(work_dir)

        shutil.copy(os.path.join(GOLDEN_DIR, "minimal-skill", "analysis.json"), work_dir)

        with open(os.path.join(work_dir, "review.json"), "w") as f:
            json.dump({
                "spec_compliance": [], "security_findings": [],
                "best_practices": [], "scores": {
                    "structure": 50, "spec_compliance": 50, "security": 50,
                    "quality": 50, "best_practices": 50, "overall": 50
                },
                "grade": "Z",  # Invalid grade
                "grade_assessment": "test",
                "grade_strengths": [], "grade_improvements": []
            }, f)

        with open(os.path.join(work_dir, "file-inventory.json"), "w") as f:
            json.dump({}, f)

        result = run_script([
            "python3", f"{SCRIPTS_DIR}/generate-report.py",
            os.path.join(work_dir, "analysis.json"),
            os.path.join(work_dir, "review.json"),
            self.template_path
        ], check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("grade must be A/B/C/D/F", result.stderr)


class BuildTemplateTests(unittest.TestCase):
    """Tests for scripts/build-template.sh"""

    def test_template_builds_successfully(self):
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            out_path = f.name
        try:
            run_script(["bash", f"{SCRIPTS_DIR}/build-template.sh", ASSETS_DIR, out_path])
            self.assertTrue(os.path.isfile(out_path))
            with open(out_path) as f:
                content = f.read()
            self.assertIn("<style>", content)
            self.assertIn("<script>", content)
            self.assertGreater(len(content), 5000)
        finally:
            os.unlink(out_path)


if __name__ == "__main__":
    unittest.main()
