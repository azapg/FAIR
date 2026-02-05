---
title: Endpoints de la API
description: Página placeholder con convenciones y grupos de endpoints de la API de Fair Platform.
---

Esta página es un **placeholder** para la referencia completa de endpoints de la API de Fair Platform en Español.

Su objetivo es evitar errores 404 y mantener una URL estable mientras se documentan y estabilizan los endpoints.

## Convenciones

- **Ruta base**: normalmente los endpoints se sirven bajo `/api/*` (por ejemplo: `http://localhost:3000/api/...`).
- **Autenticación**: autenticación basada en tokens (JWT) enviada como:

```/dev/null/auth-header.txt#L1-1
Authorization: Bearer <token>
```

- **Formatos**:
  - **JSON** para la mayoría de solicitudes y respuestas.
  - Cargas de archivos (submissions/artefactos) pueden usar `multipart/form-data`.

## Grupos de endpoints (por documentar)

Las secciones siguientes reflejan la organización *esperada* de la API. Los routes concretos, esquemas y ejemplos se agregarán a medida que se finalicen los routers del backend.

### Salud & Metadatos

- `GET /api/health` — verificación básica de salud (si está habilitado)

### Autenticación & Usuarios

- Inicio de sesión / emisión de tokens
- Sesión del usuario actual
- Gestión de usuarios (administración)

### Cursos

- Crear/listar/actualizar cursos
- Gestión de inscripción/roster

### Asignaciones (Assignments)

- Crear/listar/actualizar asignaciones
- Configuración de formatos aceptados y workflow de evaluación

### Entregas (Submissions)

- Subir contenido de una entrega
- Listar entregas por asignación
- Estado/progreso de procesamiento

### Artefactos (Artifacts)

Los artefactos son la representación interna normalizada del contenido subido y derivado.

- Subir/listar/descargar artefactos
- Artefactos derivados (OCR, parseo de notebooks, logs de ejecución, etc.)

### Plugins / Extensiones

- Descubrir plugins disponibles
- Configurar settings de plugins
- Habilitar/deshabilitar plugins por curso/asignación

## Próximos pasos

- Lee `es/api-reference/overview` para entender cómo está estructurada la API.
- Lee `es/api-reference/authentication` para detalles de login/tokens (placeholder).
- Si vas a construir extensiones, comienza por `es/sdk/overview`.
