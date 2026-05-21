# Tahcia Console Script Sync for Sublime Text

A lightweight Sublime Text package providing system-level remote execution script management for the Tahcia platform client. Securely develop, validate, download, and automatically upload automation scripts directly within your workspace layout.

---

## Features

*   **Zero-Intervention Auto-Upload:** Saves locally and pushes immediately to the remote engine automatically on `Cmd+S` / `Ctrl+S`.
*   **Fail-Safe JSON Validation:** Validates JSON syntax locally *before* processing requests, keeping malformed code from breaking remote agent endpoints.
*   **Server-Side Workspace Integrity:** Automatically syncs file renames downstream if the server mutates file naming schema.
*   **Complete Lifecycle Commands:** Direct access to fetch, list, download, and delete remote server scripts via the command palette or context menus.

---

## Installation

### Manual Installation (Development)
Clone this repository directly into your Sublime Text `Packages` directory:

```bash
cd ~/Library/Application\ Support/Sublime\ Text/Packages/
git clone [https://github.com/tahcia/sublime-text](https://github.com/tahcia/sublime_text) Tahcia