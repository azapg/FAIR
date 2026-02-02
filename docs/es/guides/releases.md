---
title: Lanzamientos (Guía)
description: Guía en español (placeholder) sobre el proceso de lanzamientos en Fair Platform.
---

Esta página es un **marcador de posición** para la guía de **lanzamientos** de Fair Platform en español.

Su objetivo es:

- Evitar errores 404 al navegar por la pestaña de **Guías**
- Mantener una estructura consistente del sitio en **Español**
- Servir como base para documentar el proceso real de releases cuando esté estabilizado

> Mientras se completa esta guía, puedes consultar la documentación de lanzamientos existente:
>
> - Inglés: `/en/development/releases`
> - Español (desarrollo): `/es/development/releases`

---

## ¿Qué se considera un “lanzamiento” en Fair Platform?

Un lanzamiento (release) normalmente implica:

- Publicar una nueva versión del paquete en PyPI (`fair-platform`)
- Etiquetar una versión en Git (tags)
- Actualizar notas de versión/changelog
- Validar que el build incluye el frontend embebido (cuando aplique)
- Verificar que el servidor (`fair serve`) funciona con la versión publicada

---

## Flujo esperado (alto nivel)

Este es el flujo conceptual que se documentará en detalle:

1. Preparar cambios (PRs) y asegurar que pasan las verificaciones
2. Actualizar versionado (según el esquema usado por el proyecto)
3. Generar build (incluyendo assets del frontend)
4. Crear tag y publicar release
5. Publicar a PyPI
6. Validación post-release (instalación limpia + smoke test)

---

## Versionado

Pendiente de documentar:

- Política de versionado (por ejemplo, SemVer u otra)
- Cuándo incrementar major/minor/patch
- Cómo se reflejan cambios de API/SDK

---

## Checklist (placeholder)

Antes de hacer un release:

- [ ] Asegurar que la documentación principal está actualizada
- [ ] Confirmar que el build del frontend se genera y se copia al paquete
- [ ] Ejecutar smoke test: `pip install fair-platform` + `fair serve`
- [ ] Confirmar que los cambios del backend y frontend son compatibles
- [ ] Revisar cambios del SDK (rompimientos, nuevos hooks, etc.)

---

## Problemas comunes (placeholder)

- **Cambios de UI no se ven**: puede faltar regenerar el build del frontend embebido.
- **Diferencias entre dev/prod**: en desarrollo el frontend puede correr separado; en prod el backend sirve assets embebidos.
- **Problemas de publicación**: credenciales/entorno de CI o configuración de PyPI.

---

## Páginas relacionadas

- Releases (EN): `/en/development/releases`
- Releases (ES): `/es/development/releases`
- Flujo de trabajo dev (ES): `/es/guides/development-workflow`
- Instalación dev (ES): `/es/guides/installation`

---

## Nota sobre estado

Esta página se ampliará con:

- Comandos exactos del pipeline de release
- Requisitos del entorno (CI/CD)
- Estrategias de rollback
- Convenciones de changelog
- Validaciones automáticas recomendadas