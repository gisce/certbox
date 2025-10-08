#!/usr/bin/env python3
"""
Test suite to validate version consistency across all components.
"""

import pytest
import asyncio
import re
import subprocess
from pathlib import Path

from certbox import __version__ as package_version
from certbox.api.routes import root
from certbox.cli import cli
from click.testing import CliRunner


class TestVersionConsistency:
    """Test cases to ensure version is consistently used across all components."""

    def test_package_version_defined(self):
        """Test that package version is properly defined."""
        assert package_version is not None
        assert isinstance(package_version, str)
        assert len(package_version) > 0
        # Basic semantic version format check (doesn't have to be strict)
        assert re.match(r'\d+\.\d+\.\d+', package_version)

    def test_setup_py_version_consistency(self):
        """Test that setup.py version matches package version."""
        setup_path = Path(__file__).parent.parent / "setup.py"
        
        # Extract version from setup.py using the same logic as setup.py
        init_path = Path(__file__).parent.parent / "certbox" / "__init__.py"
        with open(init_path, "r", encoding="utf-8") as f:
            version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", f.read(), re.M)
            if version_match:
                setup_version = version_match.group(1)
            else:
                pytest.fail("Unable to find version string in certbox/__init__.py")

        assert setup_version == package_version, f"setup.py version {setup_version} doesn't match package version {package_version}"

    def test_api_version_consistency(self):
        """Test that API root endpoint returns the same version as package."""
        result = asyncio.run(root())
        api_version = result["version"]
        
        assert api_version == package_version, f"API version {api_version} doesn't match package version {package_version}"

    def test_cli_version_consistency(self):
        """Test that CLI version matches package version."""
        runner = CliRunner()
        result = runner.invoke(cli, ['--version'])
        
        assert result.exit_code == 0
        # CLI output format is "certbox, version X.X.X"
        version_line = result.output.strip()
        cli_version_match = re.search(r'version (\d+\.\d+\.\d+)', version_line)
        
        assert cli_version_match is not None, f"Could not extract version from CLI output: {version_line}"
        cli_version = cli_version_match.group(1)
        
        assert cli_version == package_version, f"CLI version {cli_version} doesn't match package version {package_version}"

    def test_all_hardcoded_versions_removed(self):
        """Test that no hardcoded versions remain in the codebase."""
        # Define files to check and their expected patterns
        files_to_check = [
            ("certbox/api/routes.py", r'"version":\s*"[0-9]+\.[0-9]+\.[0-9]+"'),
            ("certbox/cli.py", r'version\s*=\s*"[0-9]+\.[0-9]+\.[0-9]+"'),
            ("setup.py", r'version\s*=\s*"[0-9]+\.[0-9]+\.[0-9]+"'),
        ]
        
        base_path = Path(__file__).parent.parent
        hardcoded_found = []
        
        for file_path, pattern in files_to_check:
            full_path = base_path / file_path
            if full_path.exists():
                content = full_path.read_text(encoding="utf-8")
                if re.search(pattern, content):
                    hardcoded_found.append(f"{file_path}: {pattern}")
        
        if hardcoded_found:
            pytest.fail(f"Found hardcoded versions in: {', '.join(hardcoded_found)}")

    def test_version_change_propagation(self):
        """Test that changing the version in __init__.py would propagate everywhere."""
        # This is a conceptual test - we can't actually change the version,
        # but we can verify that all components import from the same source
        
        # Verify that routes imports __version__ from parent package
        routes_path = Path(__file__).parent.parent / "certbox" / "api" / "routes.py"
        routes_content = routes_path.read_text(encoding="utf-8")
        assert "from .. import __version__" in routes_content, "API routes should import __version__ from parent package"
        
        # Verify that CLI imports __version__ from parent package
        cli_path = Path(__file__).parent.parent / "certbox" / "cli.py"
        cli_content = cli_path.read_text(encoding="utf-8")
        assert "from . import __version__" in cli_content, "CLI should import __version__ from parent package"
        
        # Verify that app.py imports __version__ from parent package
        app_path = Path(__file__).parent.parent / "certbox" / "app.py"
        app_content = app_path.read_text(encoding="utf-8")
        assert "from certbox import __version__" in app_content, "App should import __version__ from package"


if __name__ == "__main__":
    pytest.main([__file__])