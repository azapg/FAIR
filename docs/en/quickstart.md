---
title: Quickstart
description: How to get started with FAIR Platform
---

This page shows the fastest way to start using **FAIR Platform**. You can either try our community instance at [platform.fairgradeproject.org](https://platform.fairgradeproject.org) or install it locally on your machine. Both are, and will always be, completely free.

<Card
title="Community Instance"
href="https://platform.fairgradeproject.org"
arrow="true"
cta="Explore the community instance"
img="/assets/showcase.png"
horizontal>
Our community instance lets you explore FAIR immediately. It’s the quickest way for educators and researchers to test features without needing to touch a terminal.
</Card>

## What should I use?
* The community instance is perfect for those who want a quick look at the interface or want to start experimenting with features right away.
* The Local Installation is ideal for institutions that want full control over their data, or developers looking to build custom modules and contribute to the project.

For local use, FAIR is designed to be lightweight: it only needs one command to install and one command to run. No prior programming experience is required.

<Accordion title="Local Installation Guide">
## Requirements
The only requirement to run the platform is **Python 3.12 or higher**.
    
When you install Python from <a href="https://www.python.org/downloads/" target="_blank">python.org</a>, it already includes [**pip**](https://en.wikipedia.org/wiki/Pip_(package_manager)), the tool used to install FAIR.
    
To confirm your Python installation:
    
```bash
python --version
````

* Windows: Use Command Prompt or PowerShell.
* macOS/Linux: Use Terminal.
    
## Installation process
Installing FAIR is a simple three-step process.    

<Steps>
  <Step title="Open your terminal">
      Launch your Command Prompt (Windows) or Terminal (macOS/Linux).
  </Step>
  <Step title="Install FAIR">
    Run the following command to download the platform from the Python Package Index (PyPI):
      
    ```bash
      pip install fair-platform
    ```
      
      This will install the FAIR core and its necessary dependencies.
  </Step>
  <Step title="Run the platform">
    Once the installation finishes, start the platform by running:

    ```bash
      fair serve
    ```

    The terminal will provide a local URL (usually `http://localhost:3000`). Open that link in your browser to start using your private instance of FAIR.
  </Step>
</Steps>
    
    
## The CLI
The `fair` command is your entry point for managing the platform. You can find a full list of capabilities in our [CLI documentation](/en/cli).

## Troubleshooting
If something doesn't look right during installation, please refer to our [troubleshooting guide](/en/troubleshooting) or open an issue on our [GitHub](https://github.com/azapg/fair).
</Accordion>

## Next Steps

More documentation is coming soon, including:

- Platform features
- Module development guides
- Release process
