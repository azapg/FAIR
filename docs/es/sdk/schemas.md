---
title: Esquemas del SDK
description: Modelos de datos clave usados por el SDK de Fair Platform (placeholder).
---

Esta página es un **marcador de posición** para la documentación en español de los **esquemas (schemas)** del SDK de Fair Platform.

Su objetivo inmediato es:

- Evitar errores 404 al navegar el sitio en Español
- Establecer una estructura estable de URLs para la documentación del SDK
- Servir como base para completar la traducción y la referencia detallada

## ¿Qué significa “esquemas” en Fair Platform?

En Fair Platform, “esquemas” se refiere a los **modelos tipados** que describen:

- Entidades de la plataforma (cursos, asignaciones, entregas, artefactos)
- Entradas a plugins (qué datos recibe un plugin)
- Salidas de plugins (calificación, feedback, artefactos derivados, flags)
- Metadatos de artefactos y referencias al contenido almacenado

Estos modelos existen para apoyar:

- **Validación** (detectar errores temprano)
- **Reproducibilidad** (serialización consistente para experimentos)
- **UI dinámica** (formularios y vistas generados desde campos tipados)

## Conceptos comunes (visión general)

> Nota: Los nombres exactos de clases/campos pueden cambiar; esta sección es conceptual.

### Assignment (Asignación)
Representa lo que se le pide al estudiante y cómo se evalúa.

Suele incluir:

- Título, descripción e instrucciones
- Formatos aceptados (PDF, imagen, ZIP, notebook, etc.)
- Configuración de evaluación (rubrica, plugins habilitados, settings)
- Fechas límite y parámetros del flujo de calificación

### Submission (Entrega)
Representa el intento de un estudiante para una asignación.

Suele incluir:

- Referencia al estudiante/usuario
- Referencia a la asignación
- Timestamps y estado (por ejemplo, recibido, procesando, evaluado, etc.)
- Lista de artefactos (originales y derivados)
- Logs/metadata del procesamiento (cuando aplica)

### Artifact (Artefacto)
Representa una pieza de contenido almacenado: ya sea un archivo subido o un resultado derivado.

Ejemplos:

- PDF original
- Texto OCR extraído de una imagen
- Notebook parseado
- Logs de ejecución de código
- Datos estructurados derivados de un documento

Metadatos típicos:

- Tipo/kind (qué representa)
- Referencia al contenido (ruta, URL, key en object storage)
- MIME/format
- Proveniencia (qué plugin lo produjo, a partir de qué fuente)

### Result / Grade / Feedback (Resultado / Nota / Retroalimentación)
Representa la salida de evaluación.

Suele incluir:

- Puntaje o nota (numérica o por rúbrica)
- Retroalimentación (texto)
- Desglose por criterios (si aplica)
- Flags/advertencias (p. ej., “falta citar”, “formato inválido”)
- Artefactos adicionales (p. ej., PDF anotado, trazas, reportes)

## Dónde buscar la “fuente de verdad”

Esta página es intencionalmente ligera: la definición canónica vive en el código del proyecto (SDK y modelos del backend).

A medida que avancemos, esta página incluirá:

- Tabla de campos por modelo
- Ejemplos JSON de entrada/salida
- Recomendaciones de compatibilidad hacia atrás (versionado)
- Buenas prácticas para diseñar artefactos y resultados reproducibles

## Próximos pasos

- `/es/sdk/overview` — visión general del SDK
- `/es/sdk/plugins` — tipos de plugins y estructura recomendada
- `/es/sdk/examples` — ejemplos prácticos (por completar)
- Versión en inglés (mientras se traduce): `/en/sdk/schemas`
