---
title: Plugins (Guía)
description: Guía en español (placeholder) para crear, configurar y usar plugins en Fair Platform.
---

Esta página es un **marcador de posición** para la versión en español de la guía de plugins. Su objetivo es evitar errores 404 y ofrecer una estructura clara mientras completamos la traducción y documentación detallada.

## ¿Qué es un plugin en Fair Platform?

Un **plugin** es una extensión que permite añadir capacidades a Fair Platform sin modificar el núcleo. En general, un plugin puede:

- Descubrirse/cargarse al iniciar el backend
- Exponer una **configuración (settings)** con esquema tipado para validación y UI
- Ejecutarse como parte del flujo de trabajo (workflows) sobre entregas (submissions) y artefactos (artifacts)

## Tipos de plugins (conceptual)

Dependiendo del caso de uso, es común implementar uno (o más) de los siguientes tipos:

- **Transcriptores / Intérpretes**  
  Convierten entregas en formatos variados (PDF, imágenes, notebooks, ZIP, etc.) en **artefactos estandarizados** (por ejemplo: OCR, parsing, extracción de texto/estructura).

- **Calificadores (graders)**  
  Evalúan artefactos y generan **nota** y **retroalimentación**. Pueden ser:
  - basados en rúbricas,
  - basados en LLMs,
  - híbridos,
  - o flujos “agentic”.

- **Validadores**  
  Aplican verificaciones y agregan **flags/advertencias** (por ejemplo: formato, compilación, reglas específicas, verificación de pruebas, etc.).

- **Backends de almacenamiento**  
  Permiten personalizar cómo se almacenan y recuperan artefactos, resultados o datasets.

## Configuración (settings)

Una de las ideas centrales de Fair Platform es que los plugins expongan **settings tipados**, de forma que:

- El backend pueda validar la configuración antes de ejecutarla
- La UI pueda generar formularios de configuración automáticamente
- Los experimentos sean reproducibles (config exportable/importable)

### Recomendación de seguridad
No guardes secretos (API keys, tokens) dentro de settings. Para servicios externos (por ejemplo, proveedores LLM), usa variables de entorno o un gestor de secretos.

## Flujo típico de desarrollo (alto nivel)

Un ciclo típico para crear un plugin:

1. Definir el propósito del plugin (¿transcribir? ¿calificar? ¿validar?).
2. Definir settings (qué puede configurar el usuario).
3. Implementar la lógica principal del plugin (entrada/salida).
4. Asegurar que el backend lo **descubre** (registro/carga de plugins).
5. Ejecutar Fair Platform y verificar que el plugin aparece en la UI.
6. Probarlo con una tarea/entrega real (end-to-end).
7. Iterar: logs, métricas, reproducibilidad.

## Convenciones sugeridas (placeholder)

Estas convenciones se ampliarán, pero como guía inicial:

- El plugin debe ser **determinista** cuando sea posible, o registrar parámetros/semillas.
- Los resultados y transformaciones deberían reflejarse en **artefactos** (para auditoría).
- Mantén “estado oculto” al mínimo: configura explícitamente mediante settings.

## Próximos pasos

- SDK (ES): `/es/sdk/overview`
- Workflows y extensiones (ES): `/es/getting-started/extensions`
- Instalación para desarrolladores (ES): `/es/guides/installation`

## Nota sobre el estado de esta guía

Esta página es un placeholder y se irá expandiendo con:

- Estructura recomendada de plugins
- Ejemplos mínimos (transcriptor, grader, validador)
- Integración con el cargador de plugins del backend
- Buenas prácticas para investigación y reproducibilidad