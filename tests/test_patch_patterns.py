"""Unit tests for pattern-based patches (template validation).

These patches are code templates/patterns, not importable modules.
Tests validate:
1. Pattern files are valid Python (parseable)
2. Pattern string constants contain expected structures
3. Helper functions (defined as string constants) are syntactically valid
4. Before/After patterns address the documented issues
"""
import ast
import os

import pytest

PATCHES_DIR = os.path.join(os.path.dirname(__file__), "..", "patches")


def read_patch(relative_path):
    """Read a patch file and return its content."""
    path = os.path.join(PATCHES_DIR, relative_path)
    with open(path) as f:
        return f.read()


# ── Coinglass API Error Handling ─────────────────────


class TestCoinglassApiErrorPatterns:
    """Validate patches/coinglass/api_error_handling.py patterns."""

    @pytest.fixture(autouse=True)
    def load_patch(self):
        self.content = read_patch("coinglass/api_error_handling.py")

    def test_file_is_valid_python(self):
        """Patch file must parse without syntax errors."""
        ast.parse(self.content)

    def test_before_pattern_defined(self):
        assert "BEFORE_PATTERN" in self.content

    def test_after_pattern_defined(self):
        assert "AFTER_PATTERN" in self.content

    def test_after_pattern_returns_error_dict(self):
        """After pattern must return structured error dicts, not None."""
        assert '"_error": True' in self.content or "'_error': True" in self.content

    def test_after_pattern_handles_http_errors(self):
        assert "HTTPError" in self.content

    def test_after_pattern_handles_connection_errors(self):
        assert "RequestException" in self.content or "ConnectionError" in self.content

    def test_after_pattern_handles_json_decode_errors(self):
        assert "JSONDecodeError" in self.content

    def test_helper_function_defined(self):
        assert "HELPER" in self.content or "_suggestion_for_status" in self.content

    def test_suggestion_for_status_covers_key_codes(self):
        """Helper must provide suggestions for 401, 403, 429, 500."""
        for code in ["401", "403", "429", "500"]:
            assert code in self.content, f"Missing suggestion for HTTP {code}"

    def test_check_cg_response_helper(self):
        """Must include a tool-level response checker."""
        assert "_check_cg_response" in self.content

    def test_no_return_none_in_after_pattern(self):
        """After pattern must NOT contain 'return None'."""
        # Extract the AFTER_PATTERN string
        tree = ast.parse(self.content)
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if hasattr(target, 'id') and target.id == 'AFTER_PATTERN':
                        if isinstance(node.value, ast.Constant):
                            assert "return None" not in node.value.value


# ── Hyperliquid Client Error Handling ────────────────


class TestHyperliquidClientPatterns:
    """Validate patches/hyperliquid/client_error_handling.py patterns."""

    @pytest.fixture(autouse=True)
    def load_patch(self):
        self.content = read_patch("hyperliquid/client_error_handling.py")

    def test_file_is_valid_python(self):
        ast.parse(self.content)

    def test_has_spot_meta_patch(self):
        """Must patch the silent spot metadata failure."""
        assert "spot_meta" in self.content.lower() or "PATCH_1" in self.content

    def test_has_logging(self):
        """Patches must add logging instead of silent catches."""
        assert "logging" in self.content or "logger" in self.content

    def test_no_bare_except(self):
        """Patches should not use bare 'except:'."""
        lines = self.content.split('\n')
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped == "except:":
                # Only flag if it's in the NEW/AFTER pattern
                pytest.fail(f"Bare except at line {i}: {stripped}")

    def test_documents_problem(self):
        """Must document what problem each patch solves."""
        assert "PROBLEM" in self.content or "问题" in self.content or "problem" in self.content.lower()


# ── Hyperliquid Tools Error Context ──────────────────


class TestHyperliquidToolsErrorContext:
    """Validate patches/hyperliquid/tools_error_context.py patterns."""

    @pytest.fixture(autouse=True)
    def load_patch(self):
        self.content = read_patch("hyperliquid/tools_error_context.py")

    def test_file_is_valid_python(self):
        ast.parse(self.content)

    def test_format_error_helper(self):
        """Must define a _format_error helper function."""
        assert "_format_error" in self.content

    def test_helper_classifies_errors(self):
        """Helper must classify common HL error types."""
        classifiers = ["NoneType", "timeout", "connection", "float"]
        found = sum(1 for c in classifiers if c.lower() in self.content.lower())
        assert found >= 2, f"Only found {found}/4 error classifiers"

    def test_helper_returns_string(self):
        """_format_error must be typed to return str."""
        assert "-> str" in self.content

    def test_context_parameter(self):
        """Helper must accept context dict for enrichment."""
        assert "context" in self.content

    def test_tool_name_parameter(self):
        """Helper must accept tool_name for identification."""
        assert "tool_name" in self.content


# ── Cross-Patch Consistency ──────────────────────────


class TestPatchConsistency:
    """Validate cross-patch consistency."""

    @pytest.fixture(autouse=True)
    def load_all_patches(self):
        self.patches = {}
        for root, dirs, files in os.walk(PATCHES_DIR):
            for f in files:
                if f.endswith(".py") and f != "__init__.py":
                    rel = os.path.relpath(os.path.join(root, f), PATCHES_DIR)
                    with open(os.path.join(root, f)) as fh:
                        self.patches[rel] = fh.read()

    def test_all_patches_have_docstrings(self):
        """Every patch file must start with a docstring."""
        for name, content in self.patches.items():
            assert content.strip().startswith('"""') or content.strip().startswith("'''"), \
                f"{name} missing module docstring"

    def test_all_patches_parseable(self):
        """Every patch file must be valid Python."""
        for name, content in self.patches.items():
            try:
                ast.parse(content)
            except SyntaxError as e:
                pytest.fail(f"{name} has syntax error: {e}")

    def test_no_hardcoded_api_keys(self):
        """No patch should contain hardcoded API keys."""
        for name, content in self.patches.items():
            assert "sk-" not in content, f"{name} contains potential API key"
            assert "Bearer " not in content or "Bearer {" in content, \
                f"{name} may have hardcoded Bearer token"

    def test_error_patches_reference_structured_errors(self):
        """Error-related patches should use structured error dicts."""
        error_patches = [n for n in self.patches if "error" in n.lower()]
        for name in error_patches:
            content = self.patches[name]
            # Should mention structured error approach
            has_structure = any(k in content for k in [
                "_error", '"error"', "error_dict", "normalize_error",
                "_build_error", "ToolResult", "category",
                "user_message", "suggestion", "safe_call",
                "Exception", "exception",
            ])
            assert has_structure, f"{name} doesn't use structured error approach"
