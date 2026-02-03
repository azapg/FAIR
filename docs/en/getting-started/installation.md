---
title: Quick Start
description: How to install and run FAIR Platform
sidebar:
  order: 0
---

This page shows the fastest way to start using **FAIR Platform**. FAIR only needs **one command to install** and **one command to run**.

Anyone can use it, and no programming experience is required.

## Requirements

You only need **Python 3.12 or higher**.  
When you install Python from <a href="https://www.python.org/downloads/" target="_blank">python.org</a>, it already includes **pip**, the tool used to install FAIR.

To confirm your Python installation:

```bash
python --version
````

If you’re on Windows, use **Command Prompt**.
On macOS or Linux, open **Terminal**.

## Install FAIR

Open your terminal and run:

```bash
pip install fair-platform
```

This command downloads and installs FAIR on your system.

## Run FAIR

Start the platform with:

```bash
fair serve
```

FAIR will launch at:

```
http://localhost:3000
```

If your browser doesn’t open automatically, copy that address into the URL bar.

## Optional CLI Options

```bash
# Use a custom port (default is 3000)
fair serve --port 8000

# API-only mode (no web interface)
fair serve --headless

# Local development (backend + frontend)
fair dev
```

## Troubleshooting

### Python not recognized

If `python` or `pip` are not recognized on Windows, restart your computer or reinstall Python and check the box that says **“Add Python to PATH”** during installation.

### Wrong Python version

Check your version:

```bash
python --version
```

You must use **Python 3.12 or higher**.

### Port already in use

If port 8000 is busy, choose another one:

```bash
fair serve --port 8080
```

## Next Steps

More documentation is coming soon, including:

* Platform features
* Module development guides
* Release process
