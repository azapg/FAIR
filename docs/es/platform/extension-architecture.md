---
title: Núcleo y extensiones
description: Conoce el núcleo mínimo de FAIR y el límite para comportamiento personalizado.
---

FAIR está diseñado para seguir siendo útil sin extensiones instaladas. En ese estado ofrece la capa educativa durable: personas, cursos, asignaciones, entregas, rúbricas, autorización, artefactos y decisiones humanas.

Las extensiones agregan comportamiento. Evaluadores con IA, asistentes personalizados, generadores de diapositivas, transcripción, conectores externos y herramientas deterministas son extensiones; no son servicios incorporados al backend de FAIR.

## La regla fundacional

La plataforma controla **estado, políticas y observación**. Una extensión controla **comportamiento**.

| Núcleo de la plataforma | Extensión instalada |
|---|---|
| autentica usuarios e instalaciones | implementa una o más capacidades |
| autoriza acceso a cursos y recursos | elige modelos, frameworks, prompts y proveedores |
| crea y registra Ejecuciones | recibe un comando de ejecución con alcance limitado |
| acepta Eventos de Ejecución ordenados | realiza el trabajo personalizado o de IA |
| almacena Artefactos y procedencia | emite progreso, resultados y propuestas |
| registra revisión humana y decisiones finales | nunca publica silenciosamente una decisión importante |

FAIR no tiene un servicio global de IA. Las credenciales del proveedor y la configuración del modelo pertenecen a una instalación de extensión o al entorno donde se ejecuta esa extensión.

## Ciclo de vida canónico

```text
Intención del usuario o del sistema
  -> Ejecución
  -> outbox transaccional de despacho
  -> capacidad de una Extensión instalada
  -> Eventos de Ejecución ordenados
  -> proyecciones, Artefactos, interacciones y propuestas
  -> decisión humana o de dominio explícita cuando corresponda
```

Los clientes observan la Ejecución. La cola y los registros de entrega son detalles internos de implementación.

## Recursos fundacionales

- **ExtensionInstallation** es una instancia instalada y confiable de una Extensión.
- **CapabilityDefinition** es un comportamiento invocable y versionado declarado por esa instalación.
- **ExtensionGrant** autoriza una capacidad en un contexto y alcance específicos.
- **Execution** es un intento de invocar una capacidad o una FlowVersion publicada.
- **ExecutionEvent** es un hecho aceptado, inmutable y ordenado dentro de una Ejecución.
- **Artifact** y sus versiones inmutables conservan resultados y procedencia.
- **FlowVersion** fija una composición ordenada y reproducible de capacidades y configuración.

## Superficie canónica de la API

La nueva base vive bajo `/api/v1`:

| Recurso | Ruta base |
|---|---|
| Instalaciones, capacidades y permisos de Extensiones | `/api/v1/extensions` |
| Ejecuciones, eventos, streams e interacciones | `/api/v1/executions` |
| Flows y FlowVersions inmutables | `/api/v1/flows` |
| Artefactos, versiones, partes y finalización | `/api/v1/artifacts` |

Los endpoints `Workflow`, `WorkflowRun`, `Job` público, `Plugin` y Artefactos sin versión se eliminaron. No existen alias de compatibilidad: las integraciones deben usar los recursos `/api/v1` anteriores.

<Warning>
La recepción de eventos requiere credenciales de cliente con scopes, y cada Ejecución valida la instalación y los permisos contextuales. Los comandos salientes son durables, idempotentes y reintentables, pero la firma de solicitudes desde la plataforma hacia la Extensión sigue siendo una tarea de endurecimiento de FAIR 1.0. Usa una red confiable para los endpoints de despacho hasta que exista despacho firmado.
</Warning>

## Por qué los Flows siguen siendo fundamentales

Una Ejecución es suficiente para una tarea asignada a una capacidad. Un Flow agrega un procedimiento fijo e inspeccionable: versiones exactas de capacidades, configuración, orden, entradas y Ejecuciones de pasos enlazadas. Esto permite comparar y reproducir experimentos deterministas y asistidos por IA sin crear un segundo sistema de ejecución.

Consulta [La API fundacional](/es/platform/foundational-api) para ver los contratos, las capas de autorización y el ciclo de vida de una Ejecución.
