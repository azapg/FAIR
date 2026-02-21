---
title: Plugins (SDK)
description: Cómo funcionan los plugins en Fair Platform y qué tipos puedes implementar (placeholder).
---

Esta página es un **placeholder** para la documentación en español sobre **plugins del SDK** de Fair Platform.

Su objetivo es:

- Evitar páginas 404 cuando navegas en Español
- Mantener una estructura estable para completar la traducción y el contenido técnico
- Dar una visión general útil desde ya (aunque sin cubrir todos los detalles)

## ¿Qué es un plugin?

Un **plugin** es un módulo de extensión que Fair Platform puede:

- **Descubrir** al iniciar el backend
- **Configurar** mediante un esquema de settings (tipado)
- **Ejecutar** como parte del flujo (por ejemplo: procesar entregas, generar artefactos, evaluar, validar)

En otras palabras, los plugins son la forma principal de extender la plataforma **sin modificar el núcleo**.

## Tipos comunes de plugins (conceptual)

Dependiendo de tu caso de uso, normalmente implementarás uno (o varios) de estos tipos:

### Transcriptores / Intérpretes
Convierten entradas “crudas” de los estudiantes (PDFs, imágenes, notebooks, ZIPs, etc.) en una forma interna estandarizada:

- **Artefactos** derivados (OCR, texto extraído, estructura parseada)
- Metadatos que facilitan la evaluación posterior

### Calificadores (Graders)
Evalúan artefactos y producen resultados como:

- Nota/puntaje (numérico o por rúbrica)
- Retroalimentación textual
- Desglose por criterios
- Señales/flags (por ejemplo: “requiere revisión”)

### Validadores
Aplican verificaciones y agregan advertencias o bloqueos, por ejemplo:

- Validación de formato (archivos requeridos, estructura)
- Compilación o ejecución
- Verificación (pruebas, propiedades, proofs, etc.)
- Reglas específicas del curso/asignación

### Backends de almacenamiento (Storage)
Permiten personalizar cómo se almacenan y recuperan:

- Artefactos
- Resultados
- Datasets de investigación

## Settings (configuración) y buenas prácticas

Una pieza clave del SDK es que los plugins deben exponer **settings tipados**, lo cual permite:

- Validación de configuración en el backend
- Formularios dinámicos en el frontend (UI)
- Reproducibilidad (export/import de configuración)

### Seguridad (importante)
- No guardes **secretos** (API keys, tokens) dentro de settings del plugin.
- Para servicios externos (LLMs, almacenamiento, etc.), usa variables de entorno o gestión de secretos.

## Flujo típico para desarrollar un plugin (alto nivel)

1. Definir el objetivo del plugin (¿transcribir? ¿calificar? ¿validar? ¿almacenamiento?)
2. Definir settings (qué necesita configurar el usuario)
3. Implementar la lógica principal (entrada → procesamiento → salida)
4. Asegurar que el backend lo **descubre/carga**
5. Validar que aparece en la UI / API
6. Probar end-to-end con una asignación real
7. Iterar (logging, trazas, reproducibilidad)

## Próximos pasos

- `es/sdk/overview` — visión general del SDK
- `es/sdk/schemas` — modelos de datos (placeholder)
- `es/sdk/examples` — ejemplos prácticos (placeholder)

Mientras se completa la documentación en español, también puedes consultar la versión en inglés:

- `/en/sdk/plugins`
