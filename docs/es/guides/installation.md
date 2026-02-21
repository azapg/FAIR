---
title: Instalación (Desarrolladores)
description: Instala FAIR Platform para desarrollo, compila el frontend y ejecuta el servidor localmente.
---

Esta guía es para **desarrolladores** que quieren ejecutar FAIR Platform desde el código fuente (backend + frontend embebido).  
Si solo quieres *usar* la plataforma, puedes hacer el inicio rápido:

- `pip install fair-platform`
- `fair serve`

> Nota: Esta página es un **placeholder** de traducción. El contenido se irá ampliando para igualar la guía en inglés.

## Requisitos

Necesitas:

- **Python 3.12+**
- **uv** (gestor de dependencias): https://docs.astral.sh/uv/getting-started/installation/
- **Bun** (tooling del frontend): https://bun.com/get
- (Recomendado) Git

## Clonar el repositorio

```/dev/null/clone.sh#L1-3
git clone https://github.com/allanzapata/fair-platform.git
cd fair-platform
```

## Instalar dependencias

El proyecto usa `uv` para dependencias de Python:

```/dev/null/uv-sync.sh#L1-1
uv sync
```

Para ejecutar comandos dentro del entorno gestionado:

```/dev/null/uv-run.sh#L1-1
uv run python --version
```

## Compilar la plataforma (incluye frontend)

FAIR embebe el frontend compilado dentro del paquete de Python para que el backend lo sirva como archivos estáticos.

Flujo típico:

1. Compilar frontend → `frontend-dev/dist/`
2. Copiar assets → `src/fair_platform/frontend/dist/`
3. Ejecutar `fair serve` → sirve esos assets embebidos

Compila con el script del repo:

```/dev/null/build.sh#L1-1
./build.sh
```

En Windows, si `./build.sh` no funciona en tu shell, ejecútalo desde una shell compatible (por ejemplo Git Bash) o replica los pasos:

- `cd frontend-dev && bun install && bun run build`
- copiar `frontend-dev/dist/` → `src/fair_platform/frontend/dist/`

## Ejecutar la plataforma

Después de compilar:

```/dev/null/serve.sh#L1-1
uv run fair serve --port 3000
```

Abre:

- http://localhost:3000

## Desarrollo solo del frontend (recomendado para UI)

Terminal 1 (backend en modo dev):

```/dev/null/backend-dev.sh#L1-1
uv run fair serve --dev --port 8000
```

Terminal 2 (frontend dev server):

```/dev/null/frontend-dev.sh#L1-3
cd frontend-dev
bun install
bun run dev
```

## Próximos pasos

- Introducción (ES): `/es/introduction`
- Primeros pasos (ES): `/es/getting-started/installation`
- SDK (ES): `/es/sdk/overview`
