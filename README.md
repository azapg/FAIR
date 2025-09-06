# The Fair Platform [![License](https://img.shields.io/badge/License-PolyForm%20Noncommercial%201.0.0-blue.svg)](LICENSE)

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
# For frontend development
cd platform
bun install
bun run dev

# For backend development
cd backend
uv run -m main
```
### Requirements
- Python 3.10+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- [Bun](https://bun.com/get) (for frontend development)

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

This project is licensed under the [PolyForm Noncommercial License 1.0.0](LICENSE).

### What this means:

**You CAN:**
- Use this software for research, education, and personal projects
- Universities and educational institutions can serve it to students
- Make modifications and distribute copies for noncommercial purposes
- Use insights and knowledge gained from the platform for any purpose (including commercial)
- Nonprofit organizations can use it regardless of funding source

**You CANNOT:**
- Use this software or its infrastructure for commercial purposes
- Offer this software as a commercial service
- Integrate this software into commercial products

### For Researchers:
This platform is designed for academic and research use. While you cannot commercialize the software itself, you're free to use any research findings, insights, or knowledge gained from using this platform for commercial applications.

**Questions about licensing?** Please open an issue or contact [allan.zapata@up.ac.pa](mailto:allan.zapata@up.ac.pa).
