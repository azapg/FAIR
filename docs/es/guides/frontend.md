---
title: Frontend (Guía)
description: Guía en español (placeholder) para el frontend de Fair Platform (Vite + React + TypeScript).
---

Esta página es un **marcador de posición** en español para la guía del **frontend** de Fair Platform.  
Su objetivo es evitar páginas 404 y mantener una estructura consistente mientras se completa la traducción y el contenido detallado.

## Stack del frontend

El frontend de Fair Platform (en modo desarrollo) está basado en:

- **Vite** + **React** + **TypeScript**
- **React Router**
- **TanStack Query** (estado de datos del servidor)
- **Zustand** (estado del cliente)
- **Tailwind CSS**

## Desarrollo local (flujo recomendado)

En general, el flujo más rápido para trabajar en UI es:

1. Ejecutar el **backend** en modo desarrollo (API)
2. Ejecutar el **frontend dev server** (Vite) con hot reload

Backend (Terminal 1):

```/dev/null/backend-dev.sh#L1-1
uv run fair serve --dev --port 8000
```

Frontend (Terminal 2):

```/dev/null/frontend-dev.sh#L1-3
cd frontend-dev
bun install
bun run dev
```

Luego abre:

- http://localhost:3000

## Producción (frontend embebido)

Fair Platform suele servir el frontend ya compilado como archivos estáticos embebidos en el paquete Python:

1. `bun run build` genera `frontend-dev/dist/`
2. El script `./build.sh` copia esos assets a `src/fair_platform/frontend/dist/`
3. `fair serve` sirve el frontend embebido (sin dev server)

```/dev/null/build-and-serve.sh#L1-3
uv sync
./build.sh
uv run fair serve --port 3000
```

## Configuración de API (nota)

En producción, el frontend normalmente llama a la API bajo `/api`.  
En desarrollo, es común que el frontend haga proxy hacia `http://localhost:8000`.

## Próximos pasos

- Guía de desarrollo (ES): `/es/guides/development-workflow`
- Guía del backend (ES): `/es/guides/backend`
- SDK (ES): `/es/sdk/overview`
