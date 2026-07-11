---
title: Servicio de IA
description: Configura los ajustes globales de LLM usados por FAIR.
---

FAIR usa un servicio global de IA para funciones que crean contenido con un modelo de lenguaje, como la generación de rúbricas. Estas funciones requieren que una persona administradora configure el proveedor del modelo antes de que los usuarios puedan ejecutarlas.

## Configuración requerida

Define la clave de API en el entorno donde se ejecuta el backend de FAIR:

```bash
FAIR_LLM_API_KEY="tu-clave-de-api-del-proveedor"
```

Si este valor no existe, FAIR mostrará a los usuarios un mensaje de configuración amigable en lugar de exponer detalles específicos del proveedor.

## Configuración opcional

Usa estas variables de entorno cuando necesites un endpoint de proveedor o modelo personalizado:

| Variable | Predeterminado | Descripción |
|---|---|---|
| `FAIR_LLM_BASE_URL` | `https://api.openai.com/v1` | URL base para una API de chat completions compatible con OpenAI. |
| `FAIR_LLM_MODEL` | `gpt-4o` | Nombre del modelo usado por las funciones de IA del backend. |

## Después de cambiar la configuración

Reinicia el backend de FAIR después de actualizar estos valores para que el servicio lea el nuevo entorno. Luego prueba una función como la generación de rúbricas desde una cuenta de profesor para confirmar que la configuración funciona.
