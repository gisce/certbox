#!/usr/bin/env python3
"""
Changelog generation utilities for automated semver releases.
"""

import re
import json
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path
from dataclasses import dataclass
try:
    from .version_utils import parse_conventional_commit, BumpType
except ImportError:
    # For standalone execution
    from version_utils import parse_conventional_commit, BumpType


@dataclass
class ChangelogEntry:
    """Represents a single changelog entry."""
    commit_hash: str
    message: str
    commit_type: str
    scope: Optional[str]
    is_breaking: bool
    pr_number: Optional[str] = None


class ChangelogGenerator:
    """Generates and maintains CHANGELOG.md files."""
    
    # Mapping of conventional commit types to changelog sections
    TYPE_TO_SECTION = {
        "feat": "✨ Features",
        "fix": "🐛 Bug Fixes", 
        "perf": "⚡ Performance Improvements",
        "refactor": "♻️ Code Refactoring",
        "style": "💄 Style Changes",
        "test": "✅ Tests",
        "docs": "📚 Documentation",
        "ci": "👷 CI/CD",
        "chore": "🔧 Chores",
        "build": "🏗️ Build System",
    }
    
    def __init__(self, repo_path: Path = None):
        """Initialize the changelog generator."""
        self.repo_path = repo_path if repo_path else Path.cwd()
        self.changelog_path = self.repo_path / "CHANGELOG.md"
    
    def parse_commit_for_changelog(self, commit_message: str, commit_hash: str = "", pr_number: str = None) -> Optional[ChangelogEntry]:
        """
        Parse a commit message into a changelog entry.
        
        Args:
            commit_message: The commit message
            commit_hash: The commit hash (optional)
            pr_number: The PR number if available
            
        Returns:
            ChangelogEntry or None if not a conventional commit
        """
        parsed = parse_conventional_commit(commit_message)
        if not parsed:
            return None
        
        commit_type, is_breaking = parsed
        
        # Extract scope if present
        scope_match = re.match(r'^\w+\(([^)]+)\)', commit_message.strip())
        scope = scope_match.group(1) if scope_match else None
        
        return ChangelogEntry(
            commit_hash=commit_hash,
            message=commit_message.strip(),
            commit_type=commit_type,
            scope=scope,
            is_breaking=is_breaking,
            pr_number=pr_number
        )
    
    def group_entries_by_type(self, entries: List[ChangelogEntry]) -> Dict[str, List[ChangelogEntry]]:
        """Group changelog entries by their type."""
        grouped = {}
        
        # First, separate breaking changes
        breaking_changes = [entry for entry in entries if entry.is_breaking]
        if breaking_changes:
            grouped["💥 BREAKING CHANGES"] = breaking_changes
        
        # Then group by type
        for entry in entries:
            if entry.is_breaking:
                continue  # Already handled above
                
            section = self.TYPE_TO_SECTION.get(entry.commit_type, "🔧 Other Changes")
            if section not in grouped:
                grouped[section] = []
            grouped[section].append(entry)
        
        return grouped
    
    def format_changelog_entry(self, entry: ChangelogEntry) -> str:
        """Format a single changelog entry."""
        # Clean up the commit message - remove type prefix
        message = entry.message
        type_pattern = r'^(\w+)(\([^)]+\))?(!)?:\s*'
        clean_message = re.sub(type_pattern, '', message)
        
        # Capitalize first letter
        if clean_message:
            clean_message = clean_message[0].upper() + clean_message[1:]
        
        # Add scope if present
        scope_text = f"**{entry.scope}**: " if entry.scope else ""
        
        # Add PR link if available
        pr_text = f" ([#{entry.pr_number}](https://github.com/gisce/certbox/pull/{entry.pr_number}))" if entry.pr_number else ""
        
        # Add commit hash if available (short form)
        commit_text = f" ([{entry.commit_hash[:7]}](https://github.com/gisce/certbox/commit/{entry.commit_hash}))" if entry.commit_hash else ""
        
        return f"- {scope_text}{clean_message}{pr_text}{commit_text}"
    
    def generate_version_section(self, version: str, entries: List[ChangelogEntry], date: str = None) -> str:
        """
        Generate a changelog section for a specific version.
        
        Args:
            version: Version string (e.g., "1.2.3")
            entries: List of changelog entries
            date: Release date (defaults to today)
            
        Returns:
            Formatted changelog section
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        # Group entries by type
        grouped = self.group_entries_by_type(entries)
        
        # Build the section
        lines = [
            f"## [{version}] - {date}",
            ""
        ]
        
        # Add each group
        for section_name, section_entries in grouped.items():
            if not section_entries:
                continue
                
            lines.append(f"### {section_name}")
            lines.append("")
            
            for entry in section_entries:
                lines.append(self.format_changelog_entry(entry))
            
            lines.append("")
        
        return "\n".join(lines)
    
    def read_existing_changelog(self) -> str:
        """Read the existing changelog file."""
        if self.changelog_path.exists():
            return self.changelog_path.read_text(encoding="utf-8")
        return ""
    
    def create_initial_changelog(self) -> str:
        """Create the initial changelog structure."""
        return """# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

"""
    
    def update_changelog(self, version: str, entries: List[ChangelogEntry], date: str = None) -> str:
        """
        Update the changelog with a new version section.
        
        Args:
            version: New version string
            entries: List of changelog entries for this version
            date: Release date (defaults to today)
            
        Returns:
            Updated changelog content
        """
        existing_content = self.read_existing_changelog()
        
        if not existing_content:
            existing_content = self.create_initial_changelog()
        
        # Generate new version section
        new_section = self.generate_version_section(version, entries, date)
        
        # Find where to insert the new section
        # Look for the "## [Unreleased]" section and insert after it
        unreleased_pattern = r'(## \[Unreleased\]\s*\n*)'
        
        if re.search(unreleased_pattern, existing_content):
            # Insert after unreleased section
            new_content = re.sub(
                unreleased_pattern,
                f'\\1\n{new_section}',
                existing_content,
                count=1
            )
        else:
            # If no unreleased section found, add at the top after header
            header_pattern = r'(# Changelog.*?\n+)'
            if re.search(header_pattern, existing_content, re.DOTALL):
                new_content = re.sub(
                    header_pattern,
                    f'\\1{new_section}',
                    existing_content,
                    count=1,
                    flags=re.DOTALL
                )
            else:
                # Fallback: prepend to content
                new_content = new_section + "\n" + existing_content
        
        return new_content
    
    def write_changelog(self, content: str) -> None:
        """Write changelog content to file."""
        self.changelog_path.write_text(content, encoding="utf-8")
    
    def generate_from_commits(self, commit_messages: List[str], version: str, pr_number: str = None, date: str = None) -> str:
        """
        Generate changelog from commit messages.
        
        Args:
            commit_messages: List of commit messages
            version: Version string
            pr_number: PR number if updating from a PR
            date: Release date
            
        Returns:
            Updated changelog content
        """
        entries = []
        
        for i, message in enumerate(commit_messages):
            entry = self.parse_commit_for_changelog(
                message, 
                commit_hash=f"commit_{i}",  # Placeholder hash
                pr_number=pr_number
            )
            if entry:
                entries.append(entry)
        
        # If no conventional commits found, create a generic entry
        if not entries and commit_messages:
            entries.append(ChangelogEntry(
                commit_hash="",
                message="Various improvements and fixes",
                commit_type="chore",
                scope=None,
                is_breaking=False,
                pr_number=pr_number
            ))
        
        return self.update_changelog(version, entries, date)


def main():
    """CLI interface for changelog generation."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python changelog_utils.py <command> [args...]")
        return
    
    command = sys.argv[1]
    generator = ChangelogGenerator()
    
    if command == "generate":
        # Generate changelog from commit messages
        if len(sys.argv) < 4:
            print("Usage: python changelog_utils.py generate <version> <commit1> [commit2] ...")
            return
        
        version = sys.argv[2]
        commits = sys.argv[3:]
        
        content = generator.generate_from_commits(commits, version)
        print(content)
    
    elif command == "init":
        # Initialize changelog
        content = generator.create_initial_changelog()
        generator.write_changelog(content)
        print(f"Initialized changelog at {generator.changelog_path}")
    
    elif command == "test-parse":
        # Test parsing a commit message
        if len(sys.argv) < 3:
            print("Usage: python changelog_utils.py test-parse <commit_message>")
            return
        
        message = " ".join(sys.argv[2:])
        entry = generator.parse_commit_for_changelog(message)
        if entry:
            print(f"Type: {entry.commit_type}")
            print(f"Scope: {entry.scope}")
            print(f"Breaking: {entry.is_breaking}")
            print(f"Formatted: {generator.format_changelog_entry(entry)}")
        else:
            print("Not a conventional commit")


if __name__ == "__main__":
    main()