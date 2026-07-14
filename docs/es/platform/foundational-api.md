---
title: La API fundacional
description: Construye Extensiones y Flows reproducibles sobre un único modelo de ejecución.
---

FAIR 1.0 tiene un solo límite para comportamiento personalizado: una **capacidad de Extensión** instalada se invoca mediante una **Ejecución**. IA, agentes, evaluadores, renderers y conectores son implementaciones detrás de ese límite, no servicios especiales de la plataforma.

## Mapa de recursos

| Recurso | Propósito | Ruta canónica |
|---|---|---|
| ExtensionInstallation | despliegue confiable y destino de despacho | `/api/v1/extensions/installations` |
| CapabilityDefinition | contrato invocable y versionado de un manifiesto | `/api/v1/extensions/capabilities` |
| ExtensionGrant | decisión contextual de permitir o denegar | `/api/v1/extensions/grants` |
| Execution | un intento durable de realizar trabajo | `/api/v1/executions` |
| ExecutionEvent | hecho ordenado e idempotente emitido durante el trabajo | `/api/v1/executions/{id}/events` |
| ArtifactVersion | resultado o evidencia inmutable con procedencia | `/api/v1/artifact-versions` |
| FlowVersion | procedimiento ordenado e inmutable con capacidades fijadas | `/api/v1/flows/{id}/versions` |

`Workflow`, `WorkflowRun`, `Job` público y `Plugin` no pertenecen a este modelo. Sus endpoints y tablas se eliminaron en vez de crear alias porque sus semánticas eran diferentes.

## Tres capas de autorización

1. **Autorización del usuario.** Las solicitudes llevan un token bearer de FAIR. Las capacidades del rol y la propiedad del recurso controlan quién puede crear, leer, modificar o ejecutar un Flow y quién puede ver una Ejecución o Artefacto.
2. **Autorización de instalación y permisos.** Una capacidad solo puede ejecutarse mediante una instalación habilitada. Los permisos contextuales restringen los efectos declarados por curso, asignación o alcance de plataforma.
3. **Autorización del cliente de Extensión.** Las Extensiones autentican sus llamadas a FAIR con un secreto emitido y scopes como `executions:events` o `artifacts:write`. Los secretos solo se muestran al emitirlos o rotarlos.

<Warning>
El despacho saliente usa HTTP directo y durable con encabezados estables de despacho e idempotencia. La firma criptográfica de la plataforma hacia la Extensión sigue en endurecimiento; protege los endpoints con transporte y red confiables hasta que exista despacho firmado.
</Warning>

## Contrato de una capacidad

El manifiesto declara identidad, versión, URL de despacho y una o más capacidades. Cada capacidad declara:

- ID estable, tipo y versión;
- esquemas de entrada, salida y configuración opcional;
- scopes solicitados y efectos declarados;
- soporte para streaming, cancelación, reanudación o lotes.

FAIR guarda una instantánea del manifiesto y cada definición de capacidad por separado. Una FlowVersion fija la definición e instalación exactas para que una actualización no cambie silenciosamente un experimento publicado.

## Ciclo de vida de una Ejecución

```text
intención
  -> autorizar usuario, instalación, capacidad, contexto y efectos
  -> crear Ejecución y eventos iniciales inmutables
  -> confirmar el comando de despacho en la misma transacción
  -> entregar el comando a la Extensión instalada
  -> aceptar Eventos de Ejecución idempotentes y con scope
  -> proyectar estado, mensajes, interacciones, Artefactos y propuestas
  -> completar, fallar, cancelar o expirar
```

La entrega es al menos una vez. Los encabezados `Idempotency-Key` y `X-FAIR-Dispatch-Id` permanecen estables entre reintentos, por lo que la Extensión debe tratar un comando repetido como la misma solicitud. FAIR también deduplica eventos entrantes por identidad del productor.

Los clientes públicos observan Ejecuciones y eventos. Los leases, intentos y estado dead-letter son detalles internos.

## Una tarea versus un Flow

Usa una Ejecución para invocar una capacidad. Usa una FlowVersion cuando el orden y las entradas exactas deban repetirse.

Iniciar una FlowVersion publicada crea una Ejecución raíz y el primer paso. El runtime ordenado:

- resuelve cada capacidad fijada y permiso contextual;
- crea una Ejecución hija enlazada para cada intento;
- pasa la salida del paso anterior al siguiente nodo;
- aplica timeout, reintentos y política `fail` o `continue`;
- propaga cancelación y expiración;
- registra el resumen terminal y el linaje completo.

La base de datos es el límite de reinicio: el avance se deriva de Ejecuciones y eventos durables, no de memoria de proceso.

## Artefactos y resultados importantes

Un Artefacto es un recurso lógico; una ArtifactVersion es inmutable después de finalizarse. Sus partes contienen datos estructurados inline o referencias de almacenamiento, y sus enlaces conectan versiones con Ejecuciones, entregas, asignaciones, cursos, mensajes y otros destinos de procedencia.

Una Extensión solo puede crear un Artefacto para la Ejecución que atiende. FAIR registra la instalación y Ejecución productoras. Completar una Ejecución no publica una nota silenciosamente: las Extensiones crean propuestas y las decisiones de dominio siguen siendo explícitas y atribuibles.

## Fuente del contrato

La pestaña API Reference se genera desde el documento OpenAPI de la aplicación FastAPI. Es la fuente de verdad para campos; esta página define el ciclo de vida y los límites semánticos.
