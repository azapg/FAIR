---
title: CLI
---
Your local instance of FAIR is managed through a powerful Command Line Interface (CLI) that allows you to control every aspect of the platform. Below is an overview of the most commonly used commands to help you get started.

## Database Commands

Use `fair db` to run migrations without manually locating `alembic.ini`.

```/dev/null/commands.sh#L1-7
fair db upgrade head
fair db downgrade -1
fair db current
fair db history
fair db stamp head
fair db revision --autogenerate -m "your message"
```
