# Tahcia Script Sync for Sublime Text

A lightweight Sublime Text package providing remote execution script management for the Tahcia platform client. Securely develop, validate, download, and automatically upload automation scripts directly within your workspace layout.


---

## About Tahcia

Tahcia is an platform designed for agentic AI tools and browser automation workflows. It operates as a secure remote control bridge rather than a remote code execution engine, allowing external automation clients or AI agents to connect to local target environments and plugins via a dedicated communication layer without running unvetted, arbitrary scripts directly on your hardware. 

This Sublime Text plugin serves as a direct pipeline to your Tahcia developer instance, letting you manage the lifecycle of your automation scripts without context-switching out of your editor.


---

## Features

* **Zero-Intervention Auto-Upload:** Saves locally and pushes immediately to the remote engine automatically on `Cmd+S` / `Ctrl+S`.
* **Fail-Safe JSON Validation:** Validates JSON syntax locally *before* processing requests, keeping malformed code from breaking remote agent endpoints.
* **Server-Side Workspace Integrity:** Automatically syncs file renames downstream if the server mutates file naming schema.
* **Complete Lifecycle Commands:** Direct access to fetch, list, download, and delete remote server scripts via the command palette or context menus.

---

## Installation

### Manual Installation (Development)
Clone this repository directly into your Sublime Text `Packages` directory:

```bash
# macOS
cd ~/Library/Application\ Support/Sublime\ Text/Packages/
git clone [https://github.com/tahcia/sublime-text](https://github.com/tahcia/sublime-text) Tahcia

# Windows
cd %APPDATA%\Sublime Text\Packages
git clone [https://github.com/tahcia/sublime-text](https://github.com/tahcia/sublime-text) Tahcia

```

---

## Configuration

Tahcia looks for a `tahcia-config.json` file in your project directory tree.

```json
{
    "api_key": "PASTE_YOUR_TAHCIA_API_KEY_HERE",
    "uploadOnSave": true
}

```

### Settings Documentation

* **`api_key`** *(String)*: Your authenticating API token generated from Tahcia.com.
* **`uploadOnSave`** *(Boolean)*: Controls automated background syncing.
* `true`: **Enabled**. Automatically uploads `.tahcia.json` files to the cloud when saved.
* `false`: **Disabled**. Files will only upload when manually triggered via the context menu or command palette.



---

## Privacy & Security Notice

**CRITICAL:** This extension uploads code payloads to remote servers managed by Tahcia.com.

* **What gets uploaded:** Only valid JSON files explicitly matching and ending with the `.tahcia.json` extension.
* **Where it goes:** Securely transmitted via TLS directly to the Tahcia cloud execution layer endpoints.
* **When it uploads:**
1. Manually when you execute the **Push Script to Cloud** command.
2. Automatically on file save **ONLY** if a valid `tahcia-config.json` file exists in the directory tree with `"uploadOnSave"` set to true.


* **Data Isolation:** Standard source code files (`.py`, `.js`, `.php`, etc.) or non-Tahcia config files are **never scanned, read, or transmitted**. No data leaves your machine without an explicit project-level opt-in config file.

