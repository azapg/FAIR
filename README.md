# The Fair Platform

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE) ![PyPI - Version](https://img.shields.io/pypi/v/fair-platform) ![PyPI - Downloads](https://img.shields.io/pypi/dm/fair-platform)


FAIR (or _The Fair Platform_) is an open-source platform that makes it easy to experiment with automatic grading systems using AI. It provides a flexible and extensible environment for building, testing, and comparing grading approaches, from interpreters and rubrics to agent-based systems and research datasets.

The goal is to support researchers, educators, and students who want to explore how AI can improve assessment, reduce manual grading workload, and enable reproducible experiments in educational technology.
## Features
<!-- TODO: When adding docs, link "customization" to a page talking about different education system data types support -->
- **Flexible Architecture** – Define courses, assignments, and grading modules with full customization.
- **Interpreters** – Parse and standardize student submissions (PDFs, images, code, etc.) into structured artifacts.
- **Graders** – Apply configurable rubrics, AI models, or hybrid approaches to evaluate submissions.
- **Artifacts** – A universal data type for storing submissions, results, and metadata.
- **Experimentation First** – Swap modules, run A/B tests, and measure performance across approaches.
- **Research-Friendly** – Designed for reproducibility, with plans for standardized datasets and benchmarks.
- **Extensible** – Build plugins for compilers, proof validators, RAG systems, or agentic graders.

## Getting Started
```bash
pip install fair-platform
fair serve

# To serve documentation locally
fair serve --docs  # Documentation available at http://127.0.0.1:3000/docs
```

For detailed installation instructions, troubleshooting, and more, visit the [documentation](https://fair.alam.systems/docs/) (available in English and Spanish).

### Development Requirements
- Python 3.12+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- [Bun](https://bun.com/get) (for frontend development)

Once you have uv and Bun instlaled, you can build the platform and start using it:
```bash
uv run
./build.sh
fair serve
```

## Roadmap
Some planned directions for FAIR include:

- [ ] Standardized datasets for AI grading research
- [ ] Dataset generation tools (e.g., synthetic student responses with realistic errors)
- [ ] Plugins for popular LMS
- [ ] More visualization and reporting tools

## Contributing
FAIR is open for contributions! You can:

- Submit issues and feature requests.
- Propose or implement new grading modules.
- Share experimental datasets and benchmarks.

If you’re interested in collaborating, open an issue or start a discussion.

## License

This project is licensed under the GNU General Public License v3.0 (GPL-3.0). See LICENSE for the full text and details.

### What this means:

**You CAN:**
- Use, modify, and distribute this software for any purpose, including commercial use.
- Use insights and knowledge gained from the platform for any purpose.
- Make modifications and distribute copies, provided that when you distribute the software (or derivative works) you comply with GPL-3.0 requirements.
- Nonprofit organizations can use it regardless of funding source.

**You MUST / OBEY GPL-3.0 REQUIREMENTS WHEN DISTRIBUTING:**
- When distributing the software or derivative works, make the source code available under the terms of GPL-3.0.
- Preserve copyright and license notices in redistributed source and binaries.
- License any derivative works under GPL-3.0 when you distribute them.

### For Researchers:
This platform is intended for academic and research use and may also be used in commercial research or products. Note that if you distribute derived software that includes code from this project, you must do so under GPL-3.0 and provide corresponding source code.

**Questions about licensing?** Please open an issue or contact [allan.zapata@up.ac.pa](mailto:allan.zapata@up.ac.pa).
