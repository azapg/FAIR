---
title: Flujo de trabajo de desarrollo
description: Flujos recomendados para desarrollar Fair Platform (backend, frontend y plugins) localmente.
---

Esta página es un **placeholder** en español para evitar errores 404 y ofrecer una estructura estable mientras completamos la traducción y ampliamos la guía.

---

## ¿Para quién es esta guía?

Usa esta guía si estás:

- Desarrollando el **backend** (FastAPI + base de datos + carga de plugins)
- Desarrollando el **frontend** (Vite + React + TypeScript)
- Desarrollando **plugins del SDK** (graders, transcribers/intérpretes, validators, storage)
- Trabajando en **docs** y en el proceso de lanzamientos

Si solo quieres ejecutar Fair Platform como usuario final, consulta:

- `/es/getting-started/installation`

---

## Flujos de trabajo comunes

### 1) Ejecutar la plataforma completa (frontend embebido)

Este es el modo más cercano a “producción”: el backend sirve los assets del frontend compilado.

Ciclo típico:

1. Compilar el frontend y copiar los assets dentro del paquete de Python
2. Iniciar el servidor
3. Refrescar el navegador para ver cambios (si cambias el frontend, normalmente debes recompilar)

Comandos (ejemplo):

```/dev/null/dev-workflow-es.txt#L1-6
uv sync
./build.sh
uv run fair serve --port 3000
```

Notas:

- Si cambias el frontend, normalmente debes volver a ejecutar `./build.sh`.
- Si cambias el backend, reinicia `fair serve`.

---

### 2) Frontend dev server + backend dev API (recomendado para UI)

Este flujo te da recarga rápida (HMR) para la interfaz mientras consultas la API del backend mediante proxy.

Ciclo típico:

- Iniciar backend en modo dev (habilita CORS para desarrollo)
- Iniciar el frontend dev server (Vite)
- Iterar rápido con hot reload

Comandos (ejemplo):

```/dev/null/dev-workflow-es.txt#L1-9
# Terminal 1 (backend)
uv run fair serve --dev --port 8000

# Terminal 2 (frontend)
cd frontend-dev
bun install
bun run dev
```

Notas:

- El frontend normalmente corre en `http://localhost:3000`
- La API del backend normalmente corre en `http://localhost:8000`

---

### 3) Solo backend (API/headless)

Útil si trabajas en endpoints, autenticación, base de datos o carga de plugins y no necesitas la UI.

```/dev/null/dev-workflow-es.txt#L1-2
uv run fair serve --headless --port 8000
```

---

## Estructura del proyecto (alto nivel)

- `src/fair_platform/cli/`: CLI con Typer (por ejemplo `fair serve`)
- `src/fair_platform/backend/`: app FastAPI, routers, DB, auth, plugins
- `frontend-dev/`: frontend React/Vite (Bun)
- `src/fair_platform/frontend/dist/`: assets del frontend embebido (destino de copia del build)
- `src/fair_platform/sdk/`: clases base del sistema de plugins y esquemas

---

## Recomendaciones de desarrollo

- Mantén cambios del API **compatibles** cuando sea posible.
- Cuando agregues una funcionalidad, actualiza:
  - rutas y esquemas (backend)
  - comportamiento UI (frontend)
  - documentación (este sitio)
- Prefiere PRs pequeños con alcance claro.

---

## Solución de problemas (placeholder)

Esta sección se ampliará. Problemas comunes:

- “Port already in use”: ejecuta en otro puerto.
- Cambios de frontend no aparecen: recompila assets embebidos con `./build.sh`.
- Errores de CORS en frontend dev: asegúrate de iniciar el backend con `--dev`.

---

## Próximas páginas

- `/es/guides/frontend`
- `/es/guides/backend`
- `/es/guides/plugins`
- `/es/guides/releases`
