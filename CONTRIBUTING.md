# Contributing to Certbox

Thank you for your interest in contributing to Certbox! This document provides guidelines for contributing to the project, with a focus on our automated versioning and release system.

## 🚀 Quick Start

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Make your changes following the guidelines below
4. Run tests: `pytest tests/ -v`
5. Commit using conventional commits (see below)
6. Push and create a Pull Request

## 📦 Versioning and Release System

Certbox uses an automated hybrid semantic versioning system that ensures consistent and traceable releases.

### How It Works

Our system determines version bumps using two methods:

1. **Automatic Detection** (from commit messages)
2. **Manual Override** (using PR labels)

### 1. Automatic Detection - Conventional Commits

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

#### Format
```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

#### Types and Version Bumps

| Commit Type | Version Bump | Example |
|-------------|--------------|---------|
| `feat:` | **Minor** (x.Y.0) | `feat(api): add certificate renewal endpoint` |
| `fix:` | **Patch** (x.y.Z) | `fix(cli): resolve config file parsing error` |
| `perf:` | **Patch** (x.y.Z) | `perf: optimize certificate generation speed` |
| `refactor:` | **Patch** (x.y.Z) | `refactor(core): improve certificate manager structure` |
| `style:` | **Patch** (x.y.Z) | `style: fix code formatting in auth module` |
| `test:` | **Patch** (x.y.Z) | `test: add integration tests for API endpoints` |
| `docs:` | **Patch** (x.y.Z) | `docs: update installation instructions` |
| `ci:` | **Patch** (x.y.Z) | `ci: add Python 3.12 to test matrix` |
| `chore:` | **Patch** (x.y.Z) | `chore: update dependencies` |
| `build:` | **Patch** (x.y.Z) | `build: update Docker base image` |

#### Breaking Changes → Major Version Bump

Use any of these patterns for **Major** (X.0.0) bumps:

1. **Exclamation mark**: `feat!: remove deprecated certificate format`
2. **BREAKING CHANGE footer**:
   ```
   feat: update API response format
   
   BREAKING CHANGE: Certificate info endpoint now returns ISO 8601 timestamps
   ```

#### Examples

```bash
# Minor version bump - new feature
git commit -m "feat(api): add certificate batch creation endpoint"

# Patch version bump - bug fix
git commit -m "fix(cli): handle missing config file gracefully"

# Patch version bump - documentation
git commit -m "docs: add troubleshooting section to README"

# Major version bump - breaking change
git commit -m "feat!: change certificate storage format

BREAKING CHANGE: Certificates are now stored in nested directories by year"
```

### 2. Manual Override - Release Labels

You can override automatic detection by adding **exactly one** release label to your PR:

| Label | Version Bump | Use When |
|-------|--------------|----------|
| `release:major` | **Major** (X.0.0) | Breaking changes, API modifications |
| `release:minor` | **Minor** (x.Y.0) | New features, enhancements |
| `release:patch` | **Patch** (x.y.Z) | Bug fixes, small improvements |

**Important**: Only add one release label. Multiple labels will cause validation to fail.

### 3. PR Validation

Every PR is automatically validated:

✅ **Checks performed:**
- Exactly zero or one release label
- Consistent commit format (if using conventional commits)
- Proper version bump determination

⚠️ **Warnings shown for:**
- Label disagrees with commit analysis (label takes precedence)
- Non-conventional commits without release label

❌ **Validation fails for:**
- Multiple release labels
- Unresolvable version bump determination

## 🛠️ Development Workflow

### Setting Up Development Environment

```bash
# Clone your fork
git clone https://github.com/your-username/certbox.git
cd certbox

# Install in development mode
pip install -e .
pip install -r requirements-dev.txt

# Run tests
pytest tests/ -v
```

### Making Changes

1. **Choose your commit strategy**:
   - Use conventional commits for automatic versioning
   - Or plan to add a release label to your PR

2. **Write tests** for new features:
   ```bash
   # Add tests to appropriate test file
   # Run specific test file
   pytest tests/test_your_feature.py -v
   ```

3. **Update documentation** if needed:
   - Update README.md for user-facing changes
   - Update docstrings for API changes
   - Add examples for new features

### Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test categories
pytest tests/test_api.py -v          # API tests
pytest tests/test_cli.py -v          # CLI tests
pytest tests/test_semver_system.py -v  # Versioning system tests

# Test the application startup
python -c "from certbox.app import app; print('✓ App imports successfully')"
```

## 📋 Release Process

When your PR is merged to `main`, the automated release system:

1. **Analyzes changes** since the last release
2. **Determines version bump** (from commits or labels)
3. **Updates version** in `certbox/__init__.py`
4. **Generates changelog** entry in `CHANGELOG.md`
5. **Creates git tag** (e.g., `v1.2.3`)
6. **Creates GitHub release** with changelog
7. **Publishes to PyPI** (if configured)

### Publishing to PyPI (repository maintainers)

To enable publishing to PyPI from the automated release workflow you must add a repository secret containing a PyPI API token.

- Create an API token on PyPI (https://pypi.org/manage/account/#api-tokens) with the desired scope (project or full).
- In your GitHub repository, go to Settings → Secrets and variables → Actions → New repository secret.
- Add a secret named `PYPI_MASTER_TOKEN` and paste the token value.

The workflow uses token-based authentication with Twine. When using an API token, Twine expects the username to be `__token__` and the token itself to be provided as the password (the workflow sets `TWINE_USERNAME: __token__` and reads the token from the `PYPI_MASTER_TOKEN` secret).

If you'd prefer a different secret name (for example to match conventions in other repos like `PYPI_API_TOKEN_GITHUB_GESTIONATR`), update the secret name in the workflow at `.github/workflows/release.yml` accordingly.

## 🔍 Special Cases

### Documentation-Only Changes

For pure documentation changes:
```bash
git commit -m "docs: update API endpoint documentation"
# Results in patch version bump
```

### Internal Refactoring

For refactoring that doesn't change public APIs:
```bash
git commit -m "refactor(core): improve certificate validation logic"
# Results in patch version bump
```

### Breaking Internal Changes

For refactoring that breaks public APIs:
```bash
git commit -m "refactor!: change CertificateManager constructor signature

BREAKING CHANGE: CertificateManager now requires config parameter"
# Results in major version bump
```

Or use a label:
- Add `release:major` label to your PR

### Cherry-picking to Release Branches

For cherry-picks to maintenance branches:
- Only `release:patch` labels are allowed
- Only `fix:` commits are recommended

## 🎯 Best Practices

### Commit Messages

✅ **Good examples:**
```bash
feat(api): add bulk certificate revocation endpoint
fix(cli): resolve issue with config file validation  
docs: add Docker deployment examples
test: add unit tests for certificate manager
perf(core): optimize certificate generation by 50%
```

❌ **Avoid:**
```bash
Update stuff
Fix bug
Add feature
WIP
Temporary commit
```

### PR Labels

✅ **Good practices:**
- Add release label if you want to override automatic detection
- Use `release:patch` for small fixes that don't follow conventional commits
- Use `release:major` for breaking changes that aren't marked with `!`

❌ **Avoid:**
- Adding multiple release labels
- Using release labels unnecessarily if commits are conventional

### Breaking Changes

Always clearly document breaking changes:

1. **In commit message**:
   ```
   feat!: update certificate storage format
   
   BREAKING CHANGE: Certificates are now stored in subdirectories
   by creation year. Migration guide in CHANGELOG.md.
   ```

2. **In PR description**: Explain the impact and migration path

3. **In documentation**: Update relevant docs and examples

## 🆘 Getting Help

- **Questions**: Open a GitHub Discussion
- **Bugs**: Open a GitHub Issue with reproduction steps
- **Feature Requests**: Open a GitHub Issue with use case description
- **Security Issues**: Email the maintainers directly

## 📝 Code Style

- Follow existing code style in the repository
- Use meaningful variable and function names
- Add docstrings for public functions and classes
- Keep line length reasonable (100-120 characters)
- Use type hints where appropriate

## ✅ Checklist Before Submitting PR

- [ ] Tests pass: `pytest tests/ -v`
- [ ] Code follows existing style
- [ ] Documentation updated (if needed)
- [ ] Commit messages follow conventional format (if using auto-detection)
- [ ] OR appropriate release label added
- [ ] Breaking changes documented
- [ ] No multiple release labels

Thank you for contributing to Certbox! 🎉