#!/usr/bin/env python3
"""
Utilities for automatic semantic versioning and changelog generation.
Implements the hybrid versioning system with conventional commits and label override.
"""

import re
import json
import sys
from enum import Enum
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import subprocess


class BumpType(Enum):
    """Types of version bumps according to semantic versioning."""
    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"


class ConventionalCommitType:
    """Conventional commit types and their corresponding version bumps."""
    
    # Mapping from commit type to bump type
    TYPE_TO_BUMP = {
        "feat": BumpType.MINOR,
        "fix": BumpType.PATCH,
        "perf": BumpType.PATCH,
        "refactor": BumpType.PATCH,
        "style": BumpType.PATCH,
        "test": BumpType.PATCH,
        "docs": BumpType.PATCH,
        "ci": BumpType.PATCH,
        "chore": BumpType.PATCH,
        "build": BumpType.PATCH,
    }
    
    # Breaking change indicators
    BREAKING_INDICATORS = ["BREAKING CHANGE", "!", "feat!"]


def parse_conventional_commit(commit_message: str) -> Optional[Tuple[str, bool]]:
    """
    Parse a conventional commit message.
    
    Args:
        commit_message: The commit message to parse
        
    Returns:
        Tuple of (commit_type, is_breaking) or None if not conventional
    """
    # Pattern for conventional commits: type(scope): description
    pattern = r'^(\w+)(\(.+\))?(!)?:\s*.+'
    match = re.match(pattern, commit_message.strip())
    
    if not match:
        return None
    
    commit_type = match.group(1).lower()
    has_breaking_marker = match.group(3) == "!"
    
    # Check for BREAKING CHANGE in body
    has_breaking_in_body = "BREAKING CHANGE" in commit_message
    
    is_breaking = has_breaking_marker or has_breaking_in_body
    
    return commit_type, is_breaking


def determine_bump_from_commits(commit_messages: List[str]) -> BumpType:
    """
    Determine the version bump type from a list of commit messages.
    
    Args:
        commit_messages: List of commit messages to analyze
        
    Returns:
        The appropriate bump type
    """
    max_bump = BumpType.PATCH  # Default to patch
    
    for message in commit_messages:
        parsed = parse_conventional_commit(message)
        if not parsed:
            continue  # Skip non-conventional commits
            
        commit_type, is_breaking = parsed
        
        # Breaking changes always trigger major
        if is_breaking:
            return BumpType.MAJOR
            
        # Get bump type for this commit type
        if commit_type in ConventionalCommitType.TYPE_TO_BUMP:
            bump = ConventionalCommitType.TYPE_TO_BUMP[commit_type]
            
            # Take the highest priority bump (major > minor > patch)
            if bump == BumpType.MINOR and max_bump == BumpType.PATCH:
                max_bump = BumpType.MINOR
    
    return max_bump


def parse_pr_labels(labels: List[str]) -> Optional[BumpType]:
    """
    Parse PR labels to find version bump override.
    
    Args:
        labels: List of label names
        
    Returns:
        BumpType if exactly one release label found, None otherwise
        
    Raises:
        ValueError: If multiple release labels found
    """
    release_labels = []
    for label in labels:
        if label in ["release:major", "release:minor", "release:patch"]:
            release_labels.append(label)
    
    if len(release_labels) > 1:
        raise ValueError(f"Multiple release labels found: {release_labels}. Only one is allowed.")
    
    if len(release_labels) == 1:
        label_to_bump = {
            "release:major": BumpType.MAJOR,
            "release:minor": BumpType.MINOR,
            "release:patch": BumpType.PATCH,
        }
        return label_to_bump[release_labels[0]]
    
    return None


def get_current_version(repo_path: Path = None) -> str:
    """
    Get the current version from the package __init__.py file.
    
    Args:
        repo_path: Path to the repository root
        
    Returns:
        Current version string
    """
    if repo_path is None:
        repo_path = Path.cwd()
    
    init_file = repo_path / "certbox" / "__init__.py"
    
    if not init_file.exists():
        raise FileNotFoundError(f"Version file not found: {init_file}")
    
    content = init_file.read_text(encoding="utf-8")
    match = re.search(r'^__version__ = ["\']([^"\']*)["\']', content, re.MULTILINE)
    
    if not match:
        raise ValueError(f"Version not found in {init_file}")
    
    return match.group(1)


def bump_version(current_version: str, bump_type: BumpType) -> str:
    """
    Bump a semantic version string.
    
    Args:
        current_version: Current version (e.g., "1.2.3")
        bump_type: Type of bump to perform
        
    Returns:
        New version string
    """
    # Parse version
    version_pattern = r'^(\d+)\.(\d+)\.(\d+)(?:-(.+))?$'
    match = re.match(version_pattern, current_version)
    
    if not match:
        raise ValueError(f"Invalid version format: {current_version}")
    
    major, minor, patch = int(match.group(1)), int(match.group(2)), int(match.group(3))
    
    # Apply bump
    if bump_type == BumpType.MAJOR:
        major += 1
        minor = 0
        patch = 0
    elif bump_type == BumpType.MINOR:
        minor += 1
        patch = 0
    elif bump_type == BumpType.PATCH:
        patch += 1
    
    return f"{major}.{minor}.{patch}"


def update_version_file(new_version: str, repo_path: Path = None) -> None:
    """
    Update the version in the package __init__.py file.
    
    Args:
        new_version: New version string
        repo_path: Path to the repository root
    """
    if repo_path is None:
        repo_path = Path.cwd()
    
    init_file = repo_path / "certbox" / "__init__.py"
    
    if not init_file.exists():
        raise FileNotFoundError(f"Version file not found: {init_file}")
    
    content = init_file.read_text(encoding="utf-8")
    
    # Replace version
    new_content = re.sub(
        r'^(__version__ = )["\'][^"\']*["\']',
        f'\\1"{new_version}"',
        content,
        flags=re.MULTILINE
    )
    
    if content == new_content:
        raise ValueError("Version line not found or not modified")
    
    init_file.write_text(new_content, encoding="utf-8")


def get_pr_info() -> Dict:
    """
    Get PR information from GitHub environment variables.
    
    Returns:
        Dictionary with PR information
    """
    import os
    
    # In GitHub Actions for PRs, we have these environment variables
    if os.getenv("GITHUB_EVENT_NAME") == "pull_request":
        event_path = os.getenv("GITHUB_EVENT_PATH")
        if event_path and Path(event_path).exists():
            with open(event_path) as f:
                event_data = json.load(f)
            return event_data.get("pull_request", {})
    
    return {}


def validate_pr_consistency(commit_messages: List[str], labels: List[str]) -> Tuple[BumpType, List[str]]:
    """
    Validate PR consistency and determine final bump type.
    
    Args:
        commit_messages: List of commit messages in the PR
        labels: List of PR labels
        
    Returns:
        Tuple of (final_bump_type, warnings)
        
    Raises:
        ValueError: If validation fails and merge should be blocked
    """
    warnings = []
    
    # Try to get bump from labels first
    try:
        label_bump = parse_pr_labels(labels)
    except ValueError as e:
        raise ValueError(f"PR label validation failed: {e}")
    
    # Get bump from commits
    commit_bump = determine_bump_from_commits(commit_messages)
    
    # If label is present, it takes precedence
    if label_bump is not None:
        final_bump = label_bump
        
        # Warning if label disagrees with commits
        if label_bump != commit_bump:
            warnings.append(
                f"Label indicates {label_bump.value} but commits suggest {commit_bump.value}. "
                f"Using label: {label_bump.value}"
            )
    else:
        # No label, use commit-based inference
        final_bump = commit_bump
        
        # For safety, if we can't infer anything meaningful, default to patch
        if final_bump == BumpType.PATCH and not any(
            parse_conventional_commit(msg) for msg in commit_messages
        ):
            warnings.append(
                "No conventional commits found and no release label specified. "
                "Defaulting to patch version bump."
            )
    
    return final_bump, warnings


if __name__ == "__main__":
    # Simple CLI for testing
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "parse-commit":
            message = " ".join(sys.argv[2:])
            result = parse_conventional_commit(message)
            print(json.dumps(result))
            
        elif command == "current-version":
            version = get_current_version()
            print(version)
            
        elif command == "bump":
            current = sys.argv[2]
            bump_type = BumpType(sys.argv[3])
            new_version = bump_version(current, bump_type)
            print(new_version)