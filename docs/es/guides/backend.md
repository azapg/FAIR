---
title: Backend (Guía)
description: Guía en español (placeholder) para entender y desarrollar el backend de Fair Platform (FastAPI + SQLAlchemy + plugins).
---

Esta página es un **marcador de posición** para la guía del **backend** en español. Está aquí para evitar páginas 404 y para que sea posible navegar el sitio completo en **Español** mientras completamos la traducción.

Si necesitas la versión más completa por ahora, consulta la guía en inglés (cuando exista):

- `/en/guides/backend`

---

## ¿Qué es el backend de Fair Platform?

El backend es el servidor que:

- expone la **API HTTP** usada por el frontend y por clientes externos
- gestiona **autenticación** y permisos
- maneja el **modelo académico** (usuarios, cursos, asignaciones, submissions, artifacts)
- carga y ejecuta **plugins/extensiones** (transcriptores/intérpretes, graders, validadores, storage)
- sirve el **frontend embebido** en modo “full platform” (cuando no se usa `--headless`)

---

## Componentes principales (visión general)

En el repositorio, el backend vive bajo:

- `src/fair_platform/backend/`

Y típicamente incluye:

- **FastAPI**: routers/endpoints, middlewares, lifespan de la app
- **SQLAlchemy**: base de datos (SQLite por defecto, PostgreSQL vía `DATABASE_URL`)
- **Autenticación**: JWT, manejo de sesión del usuario
- **Routers modulares**: endpoints separados por dominio (auth, courses, assignments, plugins, etc.)
- **Carga de plugins**: descubrimiento y registro en runtime
- **Static serving**: sirve `src/fair_platform/frontend/dist/` cuando corresponde

---

## Ejecutar el backend en modo desarrollo

Este modo es útil si estás desarrollando el frontend por separado (Vite/Bun) o si estás trabajando en endpoints, DB, auth o plugins.

Ejemplos comunes:

```/dev/null/backend-dev.txt#L1-6
# API en :8000 con CORS habilitado para desarrollo
uv run fair serve --dev --port 8000

# Solo API (sin servir frontend embebido)
uv run fair serve --headless --port 8000
```

Notas:

- En `--dev`, normalmente se habilita CORS para poder usar el frontend dev server.
- En `--headless`, el backend no intenta servir la SPA embebida.

---

## Base de datos

- Por defecto, el proyecto suele funcionar con **SQLite** (ideal para desarrollo).
- Para producción o despliegues más robustos se recomienda **PostgreSQL** usando la variable `DATABASE_URL`.

Este documento se ampliará con:

- cómo inicializa/migra la base de datos
- dónde se definen los modelos y cómo se organizan

---

## Plugins en el backend

Una de las características clave del backend es la capacidad de **descubrir y cargar plugins**.

De forma conceptual:

1. El backend arranca
2. Descubre plugins (SDK)
3. Registra tipos de plugins y esquemas de settings
4. Expone plugins disponibles por la API y permite configurarlos desde la UI

Mientras el contenido se completa, revisa:

- `/es/sdk/overview`

---

## Estructura de API (placeholder)

En general, la API:

- usa JSON para la mayoría de endpoints
- usa `multipart/form-data` para algunos flujos de upload (submissions/artifacts)
- utiliza JWT: `Authorization: Bearer <token>`

Referencias:

- `/es/api-reference/overview`

---

## Próximos pasos (para completar esta guía)

Esta página se expandirá con secciones como:

- Arquitectura de `FastAPI` (lifespan, routers, dependencias)
- Organización de routers (auth/users/courses/assignments/plugins)
- Patrones de diseño para endpoints
- Manejo de errores, logging y trazabilidad
- Carga de plugins y modelos de settings
- Serving del frontend embebido vs frontend dev server
- Configuración (`DATABASE_URL`, flags del CLI, variables de entorno)

---

## Páginas relacionadas

- Instalación (dev): `/es/guides/installation`
- Workflow de desarrollo: `/es/guides/development-workflow`
- Frontend (guía): `/es/guides/frontend`
- Plugins (guía): `/es/guides/plugins`
- SDK: `/es/sdk/overview`
- API: `/es/api-reference/overview`
