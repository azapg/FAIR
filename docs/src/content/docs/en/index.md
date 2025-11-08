---
title: Welcome to FAIR Platform
description: Open-source platform for AI-powered grading systems
---
FAIR (or _The Fair Platform_) is an open-source platform that makes it easy to experiment with automatic grading systems using AI. It provides a flexible and extensible environment for building, testing, and comparing grading approaches, from interpreters and rubrics to agent-based systems and research datasets.

The goal is to support researchers, educators, and students who want to explore how AI can improve assessment, reduce manual grading workload, and enable reproducible experiments in educational technology.

## Features

### Flexible Architecture
Define courses, assignments, and grading modules with full customization.

### Interpreters
Parse and standardize student submissions (PDFs, images, code, etc.) into structured artifacts.

### Graders
Apply configurable rubrics, AI models, or hybrid approaches to evaluate submissions.

### Experimentation First
Swap modules, run A/B tests, and measure performance across approaches.

### Research-Friendly
Designed for reproducibility, with plans for standardized datasets and benchmarks.

### Extensible
Build plugins for compilers, proof validators, RAG systems, or agentic graders.

## Quick Start

Get started with FAIR Platform in just a few commands:

```bash
pip install fair-platform
fair serve
```

The platform will start on `http://localhost:8000` by default.

## What's Next?

- Check out the [Installation Guide](/getting-started/installation) for detailed setup instructions
- Learn about [Releases](/development/releases) and the release automation process
- Explore the platform features and start building your own grading modules

## Contributing

FAIR is open for contributions! You can:

- Submit issues and feature requests
- Propose or implement new grading modules
- Share experimental datasets and benchmarks

If you're interested in collaborating, open an issue or start a discussion on [GitHub](https://github.com/azapg/FAIR).

## License

This project is licensed under the GNU General Public License v3.0 (GPL-3.0). See the [LICENSE](https://github.com/azapg/FAIR/blob/main/LICENSE) for details.
