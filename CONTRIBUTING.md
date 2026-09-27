# Contributing to ID-BIO Project (CSV-IDBIOSYS-LINUX)

Thank you for your interest in contributing to the **ID-BIO Project**! We welcome contributions from developers, computational biologists, and maintainers.

This guide outlines the guidelines and workflow for contributing to the `CSV-IDBIOSYS-LINUX` branch.

---

## Table of Contents
- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
  - [Reporting Bugs](#reporting-bugs)
  - [Suggesting Features](#suggesting-features)
  - [Submitting Pull Requests](#submitting-pull-requests)
- [Branching Strategy](#branching-strategy)
- [Local Setup & Workflow](#local-setup--workflow)
- [Commit Message Guidelines](#commit-message-guidelines)
- [CSV Data Handling & Formatting](#csv-data-handling--formatting)

---

## Code of Conduct

Please maintain a respectful, inclusive, and collaborative environment. Be polite in code reviews, issues, and discussions.

---

## How Can I Contribute?

### Reporting Bugs
Before opening a new issue, please search existing issues to make sure it hasn't already been reported.

When creating a bug report, include:
- **Environment details:** Linux distribution, Python/gcc versions, and relevant dependencies.
- **Steps to reproduce:** Clear, step-by-step instructions.
- **Expected vs. Actual behavior:** What you expected to happen vs. what actually occurred.
- **Logs/Error messages:** Relevant terminal output or backtraces.

### Suggesting Features
Feature requests are tracked as GitHub Issues. Please include:
- A clear and descriptive title.
- A detailed explanation of the proposed feature and why it would be useful.
- Potential implementation details or architecture considerations if applicable.

---

## Branching Strategy

All development related to the Linux CSV engine should target the `CSV-IDBIOSYS-LINUX` branch.

* **Target Branch:** `CSV-IDBIOSYS-LINUX`
* **Feature Branches:** Use descriptive branch names prefixed with your change type:
  - `feature/short-description`
  - `bugfix/issue-number-description`
  - `docs/updating-readme`

---

## Local Setup & Workflow

1. **Fork the repository** on GitHub.
2. **Clone your fork locally:**
   ```bash
   git clone https://github.com/<your-username>/ID-BIO-Project.git
   cd ID-BIO-Project
   ```
3. **Checkout the target Linux branch:**
   ```bash
   git checkout CSV-IDBIOSYS-LINUX
   ```
4. **Create a topic branch for your changes:**
   ```bash
   git checkout -b feature/your-feature-name
   ```
5. **Make and test your changes** in your Linux environment.
6. **Commit and push:**
   ```bash
   git add .
   git commit -m "feat: brief description of changes"
   git push origin feature/your-feature-name
   ```
7. **Submit a Pull Request (PR):**
   - Open a PR targeting `CVAFPI/ID-BIO-Project` on the `CSV-IDBIOSYS-LINUX` branch.
   - Describe what your PR changes or fixes.

---

## Commit Message Guidelines

We recommend following the [Conventional Commits](https://www.conventionalcommits.org/) format:

- `feat:` A new feature.
- `fix:` A bug fix.
- `docs:` Documentation changes only.
- `refactor:` Code refactoring without changing functionality.
- `test:` Adding or updating tests.
- `chore:` Maintenance tasks, dependency updates, or build script changes.

**Example:**
```text
fix: resolve file path parsing issue in CSV Linux importer
```

---

## CSV Data Handling & Formatting

Because this branch (`CSV-IDBIOSYS-LINUX`) deals specifically with CSV data processing under Linux environments, please observe the following standards:

1. **Line Endings:** Ensure all CSV and code files use Unix line endings (`LF`). Avoid Windows line endings (`CRLF`).
2. **Encoding:** Save all CSV files in standard **UTF-8** encoding.
3. **Data Integrity:** Do not commit raw or non-sanitized biometric/ID sample datasets containing Sensitive Personally Identifiable Information (PII). Use anonymized or synthetic test datasets for unit testing.
4. **Validation:** Ensure CSV parsing code handles edge cases gracefully (missing headers, trailing commas, null values).

---

## Need Help?

If you have questions, feel free to open a discussion or ask within your Pull Request!
