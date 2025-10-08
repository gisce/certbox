#!/usr/bin/env python3
"""
Tests for the hybrid semver versioning system.
"""

import pytest
import tempfile
from pathlib import Path
import sys
import os

# Add the scripts directory to Python path for testing
scripts_dir = Path(__file__).parent.parent / ".github" / "scripts"
sys.path.insert(0, str(scripts_dir))

from version_utils import (
    BumpType, 
    parse_conventional_commit, 
    determine_bump_from_commits,
    parse_pr_labels,
    bump_version,
    validate_pr_consistency,
    get_current_version,
    update_version_file
)
from changelog_utils import ChangelogGenerator, ChangelogEntry


class TestConventionalCommits:
    """Test conventional commit parsing."""
    
    def test_parse_conventional_commit_valid(self):
        """Test parsing valid conventional commits."""
        # Basic feature
        result = parse_conventional_commit("feat: add new user authentication")
        assert result == ("feat", False)
        
        # Feature with scope
        result = parse_conventional_commit("feat(auth): add OAuth2 support")
        assert result == ("feat", False)
        
        # Breaking change with !
        result = parse_conventional_commit("feat!: remove deprecated API")
        assert result == ("feat", True)
        
        # Breaking change in body
        result = parse_conventional_commit("feat: add new API\n\nBREAKING CHANGE: old API removed")
        assert result == ("feat", True)
        
        # Fix
        result = parse_conventional_commit("fix: resolve memory leak in certificate parsing")
        assert result == ("fix", False)
        
        # Different types
        result = parse_conventional_commit("docs: update README with installation instructions")
        assert result == ("docs", False)
    
    def test_parse_conventional_commit_invalid(self):
        """Test parsing invalid conventional commits."""
        # Not conventional
        assert parse_conventional_commit("Add new feature") is None
        assert parse_conventional_commit("Update documentation") is None
        assert parse_conventional_commit("") is None
        assert parse_conventional_commit("random text") is None
    
    def test_determine_bump_from_commits(self):
        """Test determining version bump from commit messages."""
        # Only patches
        commits = [
            "fix: resolve bug in certificate validation",
            "docs: update API documentation",
            "test: add unit tests for core module"
        ]
        assert determine_bump_from_commits(commits) == BumpType.PATCH
        
        # Feature (minor)
        commits = [
            "fix: resolve bug",
            "feat: add new certificate export format"
        ]
        assert determine_bump_from_commits(commits) == BumpType.MINOR
        
        # Breaking change (major)
        commits = [
            "feat: add new API endpoint",
            "feat!: remove old certificate format support"
        ]
        assert determine_bump_from_commits(commits) == BumpType.MAJOR
        
        # Breaking change in body (major)
        commits = [
            "feat: update certificate validation\n\nBREAKING CHANGE: API signature changed"
        ]
        assert determine_bump_from_commits(commits) == BumpType.MAJOR
        
        # Non-conventional commits default to patch
        commits = [
            "Add some changes",
            "Update stuff"
        ]
        assert determine_bump_from_commits(commits) == BumpType.PATCH


class TestPRLabels:
    """Test PR label parsing."""
    
    def test_parse_pr_labels_single(self):
        """Test parsing single release labels."""
        assert parse_pr_labels(["release:major", "bug", "enhancement"]) == BumpType.MAJOR
        assert parse_pr_labels(["bug", "release:minor"]) == BumpType.MINOR
        assert parse_pr_labels(["release:patch"]) == BumpType.PATCH
    
    def test_parse_pr_labels_none(self):
        """Test parsing labels with no release labels."""
        assert parse_pr_labels(["bug", "enhancement", "documentation"]) is None
        assert parse_pr_labels([]) is None
    
    def test_parse_pr_labels_multiple(self):
        """Test parsing multiple release labels raises error."""
        with pytest.raises(ValueError, match="Multiple release labels"):
            parse_pr_labels(["release:major", "release:minor"])
        
        with pytest.raises(ValueError, match="Multiple release labels"):
            parse_pr_labels(["release:patch", "release:major", "bug"])


class TestVersionBumping:
    """Test version bumping logic."""
    
    def test_bump_version_patch(self):
        """Test patch version bumping."""
        assert bump_version("1.0.0", BumpType.PATCH) == "1.0.1"
        assert bump_version("2.5.9", BumpType.PATCH) == "2.5.10"
    
    def test_bump_version_minor(self):
        """Test minor version bumping."""
        assert bump_version("1.0.0", BumpType.MINOR) == "1.1.0"
        assert bump_version("2.5.9", BumpType.MINOR) == "2.6.0"
    
    def test_bump_version_major(self):
        """Test major version bumping."""
        assert bump_version("1.0.0", BumpType.MAJOR) == "2.0.0"
        assert bump_version("2.5.9", BumpType.MAJOR) == "3.0.0"
    
    def test_bump_version_invalid(self):
        """Test invalid version format."""
        with pytest.raises(ValueError, match="Invalid version format"):
            bump_version("1.0", BumpType.PATCH)
        
        with pytest.raises(ValueError, match="Invalid version format"):
            bump_version("not.a.version", BumpType.MINOR)


class TestPRValidation:
    """Test PR consistency validation."""
    
    def test_validate_pr_consistency_label_override(self):
        """Test that label overrides commit-based inference."""
        commits = ["feat: add new feature"]  # Would suggest minor
        labels = ["release:patch"]  # Override to patch
        
        bump_type, warnings = validate_pr_consistency(commits, labels)
        assert bump_type == BumpType.PATCH
        assert any("Label indicates patch but commits suggest minor" in w for w in warnings)
    
    def test_validate_pr_consistency_no_label(self):
        """Test validation without release label."""
        commits = ["feat: add new feature", "fix: resolve bug"]
        labels = ["bug", "enhancement"]
        
        bump_type, warnings = validate_pr_consistency(commits, labels)
        assert bump_type == BumpType.MINOR  # Based on commits
    
    def test_validate_pr_consistency_non_conventional(self):
        """Test validation with non-conventional commits."""
        commits = ["Add some changes", "Update documentation"]
        labels = []
        
        bump_type, warnings = validate_pr_consistency(commits, labels)
        assert bump_type == BumpType.PATCH
        assert any("No conventional commits found" in w for w in warnings)
    
    def test_validate_pr_consistency_multiple_labels_fails(self):
        """Test that multiple release labels fail validation."""
        commits = ["feat: add feature"]
        labels = ["release:major", "release:minor"]
        
        with pytest.raises(ValueError, match="PR label validation failed"):
            validate_pr_consistency(commits, labels)


class TestVersionFile:
    """Test version file operations."""
    
    def test_version_file_operations(self):
        """Test reading and updating version files."""
        # Create a temporary directory structure
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            certbox_dir = temp_path / "certbox"
            certbox_dir.mkdir()
            
            # Create initial __init__.py
            init_file = certbox_dir / "__init__.py"
            init_content = '''"""
Certbox - X.509 Certificate Management Service
"""

__version__ = "1.0.0"
__author__ = "GISCE-TI"

from .app import app
'''
            init_file.write_text(init_content)
            
            # Test reading current version
            current = get_current_version(temp_path)
            assert current == "1.0.0"
            
            # Test updating version
            update_version_file("1.1.0", temp_path)
            
            # Verify update
            new_version = get_current_version(temp_path)
            assert new_version == "1.1.0"
            
            # Verify the rest of the file is unchanged
            updated_content = init_file.read_text()
            assert "__author__ = \"GISCE-TI\"" in updated_content
            assert "from .app import app" in updated_content


class TestChangelogGeneration:
    """Test changelog generation."""
    
    def test_parse_commit_for_changelog(self):
        """Test parsing commits for changelog."""
        generator = ChangelogGenerator()
        
        # Regular feature
        entry = generator.parse_commit_for_changelog("feat(auth): add OAuth2 support", "abc1234")
        assert entry is not None
        assert entry.commit_type == "feat"
        assert entry.scope == "auth"
        assert not entry.is_breaking
        
        # Breaking change
        entry = generator.parse_commit_for_changelog("feat!: remove old API", "def5678")
        assert entry is not None
        assert entry.is_breaking
    
    def test_format_changelog_entry(self):
        """Test formatting changelog entries."""
        generator = ChangelogGenerator()
        
        entry = ChangelogEntry(
            commit_hash="abc1234",
            message="feat(auth): add OAuth2 support",
            commit_type="feat",
            scope="auth",
            is_breaking=False,
            pr_number="123"
        )
        
        formatted = generator.format_changelog_entry(entry)
        assert "**auth**: Add OAuth2 support" in formatted
        assert "#123" in formatted
        assert "abc1234" in formatted
    
    def test_group_entries_by_type(self):
        """Test grouping changelog entries."""
        generator = ChangelogGenerator()
        
        entries = [
            ChangelogEntry("1", "feat: add feature", "feat", None, False),
            ChangelogEntry("2", "fix: fix bug", "fix", None, False),
            ChangelogEntry("3", "feat!: breaking change", "feat", None, True),
        ]
        
        grouped = generator.group_entries_by_type(entries)
        
        assert "💥 BREAKING CHANGES" in grouped
        assert "✨ Features" in grouped
        assert "🐛 Bug Fixes" in grouped
        assert len(grouped["💥 BREAKING CHANGES"]) == 1
        assert len(grouped["✨ Features"]) == 1  # Only non-breaking features
        assert len(grouped["🐛 Bug Fixes"]) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])