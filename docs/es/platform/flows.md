---
title: Flows y Ejecuciones
description: Construye procedimientos reproducibles con capacidades de Extensiones instaladas.
---

Un **Flow** es la identidad lógica de un procedimiento reutilizable. Una **FlowVersion** es una instantánea ejecutable e inmutable de sus nodos ordenados, versiones de capacidades y configuración.

Iniciar una FlowVersion publicada crea una **Ejecución** raíz. Cada nodo se ejecuta como una Ejecución de paso enlazada sobre el mismo sistema de eventos, Artefactos, autorización y revisión que usan los agentes y las capacidades individuales.

## Por qué existen ambos conceptos

- Usa una **Ejecución** para un intento de realizar una capacidad o una FlowVersion publicada.
- Usa una **FlowVersion** cuando el procedimiento exacto debe inspeccionarse, repetirse, compararse o citarse en una investigación.
- Un Flow no requiere un LLM ni un agente.
- Un agente puede invocar un Flow publicado, pero no reemplaza su definición fija.

## Registro de reproducibilidad

Una Ejecución de Flow conserva:

- el identificador inmutable de FlowVersion y el hash de su definición;
- las versiones exactas de capacidades y configuración;
- el linaje ordenado de Ejecuciones raíz y de pasos;
- los eventos aceptados en orden y el estado terminal;
- la procedencia de Artefactos de entrada y salida.

## API actual

Los recursos Flow viven bajo `/api/v1/flows`. La API permite crear y archivar Flows, crear versiones inmutables, publicar o archivar una versión e iniciar una Ejecución.

El runtime ejecuta los nodos en el orden de la definición. Cada paso es una Ejecución hija con una capacidad e instalación fijadas. La salida de un paso completado alimenta el siguiente nodo. La política del nodo controla timeout, número máximo de intentos y si un fallo detiene o permite continuar el Flow. La cancelación y expiración se propagan a los pasos activos, y la Ejecución raíz conserva el resumen terminal.

Los recursos eliminados `/api/workflows` y `/api/workflow-runs` no tienen alias de compatibilidad.

Consulta [Núcleo y extensiones](/es/platform/extension-architecture) para conocer el ciclo de vida y el límite de la API compartida.
