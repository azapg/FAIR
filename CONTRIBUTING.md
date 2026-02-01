# Contributing to FAIR

First off, thank you for taking the time to contribute! FAIR is an open-source platform for experimenting with automatic grading systems using AI, and we aim for a community built on discipline, technical excellence, and real-world impact.

All types of contributions are encouraged and valued. See the [Table of Contents](#table-of-contents) for different ways to help and details about how this project handles them. Please make sure to read the relevant section before making your contribution—it will make it a lot easier for us maintainers and smooth out the experience for all involved.

> [!NOTE]
> And if you like the project, but just don't have time to contribute, that's fine. There are other easy ways to support the project and show your appreciation:
> - Star the project on GitHub
> - Tweet about it or share on LinkedIn
> - Refer this project in your project's README
> - Mention the project at local meetups and tell your friends/colleagues

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [I Have a Question](#i-have-a-question)
- [How We Work](#how-we-work)
- [I Want To Contribute](#i-want-to-contribute)
  - [Reporting Bugs](#reporting-bugs)
  - [Suggesting Enhancements](#suggesting-enhancements)
  - [Your First Code Contribution](#your-first-code-contribution)
- [Development Setup](#development-setup)
- [Styleguides](#styleguides)
  - [Code Style](#code-style)
  - [Commit Messages](#commit-messages)
- [Join The Project Team](#join-the-project-team)
- [Communication](#communication)

## Code of Conduct

This project and everyone participating in it is governed by our Code of Conduct. By participating, you are expected to uphold this code. Please report unacceptable behavior to [allan.zapata@up.ac.pa](mailto:allan.zapata@up.ac.pa).

## I Have a Question

> [!IMPORTANT]
> If you want to ask a question, we assume that you have read the available [Documentation](https://github.com/azapg/FAIR/blob/main/README.md).

Before you ask a question, it is best to search for existing [Issues](https://github.com/azapg/FAIR/issues) that might help you. In case you have found a suitable issue and still need clarification, you can write your question in that issue. It is also advisable to search the internet for answers first.

If you then still feel the need to ask a question and need clarification, we recommend the following:

- Open an [Issue](https://github.com/azapg/FAIR/issues/new).
- Provide as much context as you can about what you're running into.
- Provide project and platform versions (Python, uv, Bun, OS), depending on what seems relevant.

We will then take care of the issue as soon as possible.

## How We Work

We use a [Public GitHub Project](https://github.com/users/azapg/projects/2/) to manage our tasks. Inside it you can find all issues and "epics" (big goals that we split into smaller issues) we are currently working on. There you have multiple views to organize and make sense of what needs work and where you can help:

- **[Prioritized Backlog](https://github.com/users/azapg/projects/2/views/1)**: Organizes current tasks by priority. P0 is most urgent, P2 is less urgent.
- **[Horizon Board](https://github.com/users/azapg/projects/2/views/7)**: Understand the big picture. Stores epics we are currently working on and ones we will move to next.
- **[Status Board](https://github.com/users/azapg/projects/2/views/2)**: See the status of all tasks:
  - `Backlog`: Not yet clarified or ready for work
  - `Ready`: You can start working on this right away
  - `In Progress`: Someone is currently working on it
  - `In Review`: Finished, waiting for maintainer review
- **[Bugs](https://github.com/users/azapg/projects/2/views/4)**: All reported bugs.
- **[My Items](https://github.com/users/azapg/projects/2/views/6)**: Tasks assigned to you.

### Labels to Watch

- `good first issue`: Low-dependency, "one-bite" tasks perfect for getting started.
- `bug`: High priority. If you find one, please report it with reproduction steps.
- `epic`: Large architectural changes (e.g., Event-Driven Refactor).
- `quality`: Inspired by [Linear's Quality Wednesdays](https://linear.app/now/quality-wednesdays), every time we see something small that can be improved, we report it so we can improve it.

## I Want To Contribute

> [!IMPORTANT]
> ### Legal Notice
> When contributing to this project, you must agree that you have authored 100% of the content, that you have the necessary rights to the content, and that the content you contribute may be provided under the project license.

### Reporting Bugs

#### Before Submitting a Bug Report

A good bug report shouldn't leave others needing to chase you up for more information. Therefore, we ask you to investigate carefully, collect information, and describe the issue in detail in your report. Please complete the following steps in advance to help us fix any potential bug as fast as possible.

- Make sure that you are using the latest version.
- Determine if your bug is really a bug and not an error on your side (e.g., using incompatible environment components/versions). Make sure that you have read the [documentation](). If you are looking for support, you might want to check [this section](#i-have-a-question).
- To see if other users have experienced (and potentially already solved) the same issue you are having, check if there is not already a bug report existing for your bug or error in the [bug tracker](https://github.com/azapg/FAIR/issues?q=label%3Abug).
- Also make sure to search the internet (including Stack Overflow) to see if users outside of the GitHub community have discussed the issue.
- Collect information about the bug:
  - Stack trace (Traceback)
  - OS, Platform and Version (Windows, Linux, macOS, x86, ARM)
  - Version of the interpreter, compiler, SDK, runtime environment, package manager
  - Your input and the output
  - Can you reliably reproduce the issue? And can you also reproduce it with older versions?

#### How Do I Submit a Good Bug Report?

> [!IMPORTANT]
> You must never report security related issues, vulnerabilities or bugs including sensitive information to the issue tracker, or elsewhere in public. Instead, sensitive bugs must be sent by email to [allan.zapata@up.ac.pa](mailto:allan.zapata@up.ac.pa).

We use GitHub issues to track bugs and errors. If you run into an issue with the project:

- Open an [Issue](https://github.com/azapg/FAIR/issues/new). (Since we can't be sure at this point whether it is a bug or not, we ask you not to talk about a bug yet and not to label the issue.)
- Explain the behavior you would expect and the actual behavior.
- Please provide as much context as possible and describe the *reproduction steps* that someone else can follow to recreate the issue on their own. This usually includes your code. For good bug reports you should isolate the problem and create a reduced test case.
- Provide the information you collected in the previous section.

Once it's filed:

- The project team will label the issue accordingly.
- A team member will try to reproduce the issue with your provided steps. If there are no reproduction steps or no obvious way to reproduce the issue, the team will ask you for those steps and mark the issue as `needs-repro`. Bugs with the `needs-repro` tag will not be addressed until they are reproduced.
- If the team is able to reproduce the issue, it will be marked `needs-fix`, as well as possibly other tags (such as `critical`), and the issue will be left to be [implemented by someone](#your-first-code-contribution).

### Suggesting Enhancements

This section guides you through submitting an enhancement suggestion for FAIR, **including completely new features and minor improvements to existing functionality**. Following these guidelines will help maintainers and the community understand your suggestion and find related suggestions.

#### Before Submitting an Enhancement

- Make sure that you are using the latest version.
- Read the [documentation]() carefully and find out if the functionality is already covered, maybe by an individual configuration.
- Perform a [search](https://github.com/azapg/FAIR/issues) to see if the enhancement has already been suggested. If it has, add a comment to the existing issue instead of opening a new one.
- Find out whether your idea fits with the scope and aims of the project. It's up to you to make a strong case to convince the project's developers of the merits of this feature. Keep in mind that we want features that will be useful to the majority of our users and not just a small subset. If you're just targeting a minority of users, consider writing an add-on/plugin library.

#### How Do I Submit a Good Enhancement Suggestion?

Enhancement suggestions are tracked as [GitHub issues](https://github.com/azapg/FAIR/issues).

- Use a **clear and descriptive title** for the issue to identify the suggestion.
- Provide a **step-by-step description of the suggested enhancement** in as many details as possible.
- **Describe the current behavior** and **explain which behavior you expected to see instead** and why. At this point you can also tell which alternatives do not work for you.
- You may want to **include screenshots and animated GIFs** which help you demonstrate the steps or point out the part which the suggestion is related to.
- **Explain why this enhancement would be useful** to most FAIR users. You may also want to point out other projects that solved it better and which could serve as inspiration.

### Your First Code Contribution

1. **Explore the Roadmap**: Check the [FAIR Project Board](https://github.com/users/azapg/projects/2/) to see what's marked as "Ready."
2. **Claim an Issue**: Comment on the issue to let others know you're working on it.
3. **Set Up Your Environment**: Follow the [Development Setup](#development-setup) instructions below.
4. **Follow the Architecture**: We prioritize modularity. Check the `src/fair_platform/sdk` for core schemas before modifying the backend.
5. **Write Tests**: We use `pytest`. Not all tests are passing currently, but you should ensure your new code has passing tests.
6. **Submit a Pull Request**: Reference the issue number and provide a clear description of your changes.

## Development Setup

**Prerequisites:**
- **Python 3.12+**
- **uv** (Python package manager)
- **Bun** (JavaScript runtime)

**Quick Start:**
```bash
# Clone the repository
git clone https://github.com/azapg/FAIR.git
cd FAIR

# Initialize the platform
./build.sh
```

**Architecture Notes:**
- We prioritize modularity and clean imports
- Standardized state management is valued throughout the codebase

## Styleguides

### Code Style

- **Python**: Follow PEP 8 guidelines. We value clean imports and modular design.
- **TypeScript/JavaScript**: Use consistent formatting with the existing codebase.
- **General**: Prioritize readability and maintainability over cleverness.

### Commit Messages

- Use the present tense ("Add feature" not "Added feature")
- Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit the first line to 72 characters or less
- Reference issues and pull requests liberally after the first line
- Consider starting with a type prefix:
  - `feat:` for new features
  - `fix:` for bug fixes
  - `docs:` for documentation changes
  - `style:` for formatting changes
  - `refactor:` for code restructuring
  - `test:` for adding tests
  - `chore:` for maintenance tasks

## Join The Project Team

If you're interested in becoming a maintainer or joining the core team, please reach out via [email](mailto:allan.zapata@up.ac.pa) or open a discussion on GitHub. We're looking for contributors who align with our values of discipline, technical excellence, and real-world impact.

## Communication

- **GitHub Discussions**: For questions about architecture, features like the **Human-in-the-Loop (HITL)** flow, or general brainstorming.
- **Email**: [allan.zapata@up.ac.pa](mailto:allan.zapata@up.ac.pa) for sensitive matters or direct maintainer contact.
- **Project Board**: Check our [GitHub Project](https://github.com/users/azapg/projects/2/) for real-time task updates.

---

## Attribution

This guide is based on the [contributing.md](https://contributing.md/) template.
