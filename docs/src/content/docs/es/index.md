---
title: Bienvenido a FAIR Platform
description: Plataforma de código abierto para sistemas de calificación con IA
---

FAIR (o _The Fair Platform_) es una plataforma de código abierto que facilita la experimentación con sistemas de calificación automática usando IA. Proporciona un entorno flexible y extensible para construir, probar y comparar enfoques de calificación, desde interpretadores y rúbricas hasta sistemas basados en agentes y conjuntos de datos de investigación.

El objetivo es apoyar a investigadores, educadores y estudiantes que deseen explorar cómo la IA puede mejorar la evaluación, reducir la carga de trabajo de calificación manual y permitir experimentos reproducibles en tecnología educativa.

## Características

### Arquitectura Flexible
Define cursos, tareas y módulos de calificación con total personalización.

### Interpretadores
Analiza y estandariza envíos de estudiantes (PDFs, imágenes, código, etc.) en artefactos estructurados.

### Calificadores
Aplica rúbricas configurables, modelos de IA o enfoques híbridos para evaluar envíos.

### Experimentación Primero
Intercambia módulos, ejecuta pruebas A/B y mide el rendimiento entre enfoques.

### Amigable para Investigación
Diseñado para reproducibilidad, con planes para conjuntos de datos y benchmarks estandarizados.

### Extensible
Construye plugins para compiladores, validadores de pruebas, sistemas RAG o calificadores agénticos.

## Inicio Rápido

Comienza con FAIR Platform en solo unos comandos:

```bash
pip install fair-platform
fair serve
```

La plataforma se iniciará en `http://localhost:8000` por defecto.

## ¿Qué Sigue?

- Consulta la [Guía de Instalación](/es/getting-started/installation) para instrucciones detalladas de configuración
- Aprende sobre [Lanzamientos](/es/development/releases) y el proceso de automatización de lanzamientos
- Explora las características de la plataforma y comienza a construir tus propios módulos de calificación

## Contribuciones

¡FAIR está abierto a contribuciones! Puedes:

- Enviar problemas y solicitudes de características
- Proponer o implementar nuevos módulos de calificación
- Compartir conjuntos de datos experimentales y benchmarks

Si estás interesado en colaborar, abre un problema o inicia una discusión en [GitHub](https://github.com/azapg/FAIR).

## Licencia

Este proyecto está licenciado bajo la Licencia Pública General GNU v3.0 (GPL-3.0). Consulta la [LICENCIA](https://github.com/azapg/FAIR/blob/main/LICENSE) para más detalles.
