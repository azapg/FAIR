---
title: Bienvenido a FAIR
description: Un LMS abierto y una plataforma de investigación con Extensiones instalables y opcionales.
---

**FAIR** es una plataforma educativa y un entorno de investigación de código abierto creado por el [Proyecto Fair Grade](https://fairgradeproject.org). Ofrece a profesores, estudiantes e investigadores un espacio controlado para estudiar cómo las nuevas tecnologías afectan la educación, manteniendo el juicio humano en el centro.

FAIR es útil sin IA. Cuando no hay Extensiones instaladas, funciona como un LMS enfocado: personas, cursos, asignaciones, entregas, rúbricas, artefactos y decisiones humanas siguen disponibles.

## Las Extensiones agregan comportamiento

Las Extensiones instaladas pueden agregar:

- evaluadores y herramientas de retroalimentación asistidas por IA;
- asistentes personalizados con contexto del curso;
- generadores de diapositivas HTML y materiales educativos;
- transcripción y procesamiento de documentos;
- herramientas deterministas y conectores con otros LMS.

La plataforma no incorpora esas implementaciones ni un proveedor global de IA. Autentica y autoriza una Extensión instalada, crea una Ejecución observable, registra eventos ordenados y Artefactos, y conserva la procedencia necesaria para revisión e investigación.

Lee [Núcleo y extensiones](/es/platform/extension-architecture) para conocer este límite fundacional.

## Investigación reproducible mediante Flows

Una tarea puntual puede representarse con una Ejecución. Una **FlowVersion** fija un procedimiento ordenado: versiones exactas de capacidades, configuración, entradas y Ejecuciones de pasos enlazadas. Así es posible comparar resultados, costos e intervenciones sin depender de un segundo sistema de workflows opaco.

Lee [Flows y Ejecuciones](/es/platform/flows) para conocer el modelo actual y su estado de implementación.

## El juicio humano sigue siendo explícito

Las Extensiones pueden analizar, explicar, recomendar y proponer. Completar una Ejecución no publica silenciosamente una calificación ni toma una decisión institucional. Los resultados importantes siguen siendo acciones explícitas con procedencia humana o de política visible.

## Próximos pasos

<Columns cols={2}>
  <Card title="Inicio rápido" icon="rocket" href="/es/quickstart">
    Ejecuta FAIR y crea tu primer curso.
  </Card>
  <Card title="Núcleo y extensiones" icon="blocks" href="/es/platform/extension-architecture">
    Comprende el límite de cada capacidad personalizada.
  </Card>
  <Card title="Flows y Ejecuciones" icon="workflow" href="/es/platform/flows">
    Aprende cómo los procedimientos reproducibles comparten un solo modelo de ejecución.
  </Card>
  <Card title="Hoja de ruta" icon="map" href="/es/roadmap">
    Sigue el avance hacia el contrato de FAIR 1.0.
  </Card>
</Columns>
