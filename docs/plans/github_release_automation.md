# GitHub Release Automation Plan

## Objective
Automate the creation of GitHub Releases, Git Tags, and Changelogs based on Conventional Commits. This ensures semantic versioning is strictly followed and reduces manual toil.

## Selected Strategy: Release Please
We will use [Release Please](https://github.com/googleapis/release-please-action) by Google. 

**Why?**
- Native support for **Monorepos**.
- Handles **Conventional Commits** (`feat`, `fix`, `breaking`, etc.) automatically.
- Works by creating a **Release PR** that you review and merge. This gives you control/visibility before the actual release happens.
- Updates `package.json` (Web) and `pyproject.toml` (API) versions automatically.

## Implementation Steps

### 1. Configuration Files
Create the configuration files in the root directory to tell Release Please how to handle the monorepo structure.

**`release-please-config.json`**
Defines the package types and release settings.
```json
{
  "packages": {
    ".": {
      "release-type": "node", 
      "package-name": "nous-monorepo",
      "include-component-in-tag": false
    },
    "apps/api": {
      "release-type": "python",
      "package-name": "nous-api"
    },
    "apps/web": {
      "release-type": "node",
      "package-name": "nous-web"
    }
  },
  "bootstrap-sha": "PREVIOUS_COMMIT_SHA_IF_NEEDED" 
}
```

**`.release-please-manifest.json`**
Stores the current versions of your packages (Release Please manages this file after setup).
```json
{
  ".": "0.0.0",
  "apps/api": "0.1.0",
  "apps/web": "0.0.0"
}
```

### 2. GitHub Action Workflow
Create `.github/workflows/release.yml`:

```yaml
on:
  push:
    branches:
      - main

permissions:
  contents: write
  pull-requests: write

name: release-please

jobs:
  release-please:
    runs-on: ubuntu-latest
    steps:
      - uses: google-github-actions/release-please-action@v4
        with:
          # Uses the config files created above
          config-file: release-please-config.json
          manifest-file: .release-please-manifest.json
          token: ${{ secrets.GITHUB_TOKEN }}
```

## How It Works (The Flow)

1.  **Development:** You push changes to `main` using conventional commits (e.g., `feat(api): add new endpoint`).
2.  **Automation (Draft):** The GitHub Action runs. It analyzes the commits and realizes a new version is needed.
3.  **PR Creation:** The Action creates (or updates) a specialized Pull Request named **"chore: release ..."**.
    -   This PR contains updates to `CHANGELOG.md`, `package.json`, `pyproject.toml`, and `.release-please-manifest.json`.
4.  **Review:** You review this PR. It serves as a staging area for your release.
5.  **Release:** When you **merge** this PR into `main`:
    -   The Action runs again.
    -   It detects the merge.
    -   It creates the **GitHub Release** and **Git Tag**.

## Next Steps
1.  Review and approve this plan.
2.  Create the configuration files.
3.  Create the workflow file.
4.  Push to `main` to initialize the workflow.
