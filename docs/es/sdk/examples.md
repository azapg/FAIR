---
title: Ejemplos del SDK
description: Ejemplos prácticos (placeholder) para crear plugins del SDK de Fair Platform e integrarlos en workflows.
---

Esta página contiene **ejemplos iniciales** del SDK de Fair Platform en **Español**.

> Estado: **placeholder**. Existe para evitar errores 404 y mantener una estructura estable mientras se completa la traducción y se agregan ejemplos reales alineados con la implementación actual del SDK.

## Qué encontrarás aquí

Estos ejemplos se enfocarán en:

- Crear un plugin mínimo con **settings tipados**
- Consumir **artifacts** y producir artifacts derivados
- Devolver resultados de evaluación (nota + retroalimentación) de forma consistente
- Registrar plugins para que el backend los descubra
- Flujo de desarrollo local para iterar rápidamente

## Ejemplo 1: “Hello Plugin” mínimo (estructura)

Un plugin típico incluye:

- Una clase que implementa el tipo correcto (grader / transcriber/intérprete / validator / storage)
- Un modelo de settings (para que UI + API puedan validar configuración)
- Un método tipo `run(...)` / `grade(...)` que reciba contexto y produzca salidas

```/dev/null/sdk-ejemplos-hello-plugin.txt#L1-23
# Pseudocódigo (placeholder)
class ExamplePlugin(BasePlugin):
    name = "example"

    class Settings(BaseModel):
        enabled: bool = True

    def run(self, submission, assignment, settings: Settings):
        if not settings.enabled:
            return None
        return {"message": "hola"}
```

## Ejemplo 2: Artifact de entrada → artifact de salida

Muchos workflows se ven así:

1. Artifact de entrada (por ejemplo: PDF/imagen/zip)
2. El plugin extrae/normaliza contenido
3. Artifact derivado (texto OCR, notebook parseado, logs de ejecución, etc.)

```/dev/null/sdk-ejemplos-artifacts.txt#L1-26
# Pseudocódigo (placeholder)
def run(self, submission, assignment, settings):
    source = select_artifact(submission.artifacts, kind="file")
    text = extract_text(source.bytes)
    derived = Artifact(kind="text", content=text)
    return {"artifacts": [derived]}
```

## Ejemplo 3: Forma de salida de un grader (a alto nivel)

Normalmente un grader produce:

- Puntaje/nota (numérico y/o por rúbrica)
- Retroalimentación (texto)
- Flags/advertencias (opcional)
- Artifacts adicionales (opcional; por ejemplo, un PDF anotado)

```/dev/null/sdk-ejemplos-grader.txt#L1-28
# Pseudocódigo (placeholder)
def grade(self, submission, assignment, settings):
    return {
        "score": 0.92,
        "feedback": "Buen trabajo. Mejora la claridad en la sección 2.",
        "flags": ["needs-citations"]
    }
```

## Ejemplo 4: Settings tipados (por qué importan)

Los settings tipados ayudan a:

- Validar configuración en backend
- Renderizar formularios en UI automáticamente
- Mantener experimentos reproducibles

```/dev/null/sdk-ejemplos-settings.txt#L1-22
# Pseudocódigo (placeholder)
class RubricGrader(BaseGrader):
    class Settings(BaseModel):
        rubric_text: str
        strict: bool = False
        max_points: int = 100
```

## Próximos pasos

- `/es/sdk/overview` — cómo encaja el SDK en la arquitectura
- `/es/sdk/plugins` — tipos de plugins y estructura recomendada
- `/es/sdk/schemas` — modelos de datos principales del SDK

Mientras se completa la documentación en español (incluyendo ejemplos reales), puedes consultar la versión en inglés:

- `/en/sdk/examples`
