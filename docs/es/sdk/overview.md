---
title: Resumen del SDK
description: Extiende Fair Platform creando plugins para transcripción, calificación, validación y almacenamiento.
---

Esta página es un **marcador de posición** para la versión en español del *SDK Overview*.

El SDK de Fair Platform está diseñado para que puedas **extender la plataforma** sin necesidad de modificar el núcleo, implementando **plugins** que el backend puede descubrir, configurar y ejecutar.

## ¿Para qué sirve el SDK?

Úsalo cuando quieras:

- Crear **intérpretes/transcriptores** (convertir PDFs, imágenes, notebooks, ZIPs, etc. en artefactos estandarizados)
- Crear **calificadores (graders)** (rúbricas, LLMs, enfoques híbridos, flujos agentic)
- Crear **validadores** (checks de formato, compilación, verificación, flags, etc.)
- Implementar **backends de almacenamiento** (artefactos, resultados, datasets, etc.)

## Conceptos clave

- **Plugins**: unidades de extensión que la plataforma puede cargar y ejecutar.
- **Artefactos**: representación interna estandarizada del trabajo del estudiante y datos derivados (OCR, parsing, logs, datos estructurados).
- **Asignaciones y entregas**: definen el flujo académico (tareas → submissions → artefactos → resultados).

## Nota sobre traducción

La documentación completa del SDK en español se irá ampliando. Mientras tanto, puedes consultar la versión en inglés:

- `/en/sdk/overview`

## Próximos pasos (pendiente)

- `es/sdk/plugins`: Tipos de plugins y estructura recomendada
- `es/sdk/schemas`: Modelos de datos (Submission, Assignment, Artifact, etc.)
- `es/sdk/examples`: Ejemplos mínimos de plugins