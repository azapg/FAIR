---
title: Troubleshooting
---

## Common Issues

### Python not recognized

If `python` or `pip` are not recognized on Windows, restart your computer or reinstall Python ancheck the box that says **“Add Python to PATH”** during installation.

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
