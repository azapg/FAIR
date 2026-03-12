---
title: Flujos de Trabajo y Complementos
description: Explora los poderosos flujos de trabajo y complementos que hacen de FAIR una plataforma versátil y personalizable para tus necesidades educativas.
---

<Warning>Los flujos de trabajo y complementos están en desarrollo activo y pueden cambiar en futuras versiones. Funcionalidades importantes como los Agentes de TA aún no están implementadas. Consulta nuestra [hoja de ruta](/en/roadmap) para más información.</Warning>

Los flujos de trabajo y complementos son herramientas poderosas que te permiten personalizar y extender la funcionalidad de la plataforma FAIR. Puedes pensar en ellos como pequeños scripts que procesan

## Extension FAIR Core (en desarrollo)
FAIR incluye una extensión integrada llamada **FAIR Core** con acciones base de transcripción, calificación, revisión y generación de rúbricas para los flujos de trabajo. Esta extensión sigue en desarrollo, y su comportamiento, configuración y plugins pueden cambiar a medida que evolucione la plataforma.

La extensión core usa variables de entorno para la configuración por defecto del LLM y expone parámetros de plugin para ajustar el modelo, la base URL, la temperatura y los límites de tokens cuando sea necesario.

<Frame caption="Demostración de un flujo de trabajo utilizado para calificar las entregas de la tarea Implementación y Análisis de Kernels de Detección de Bordes">
    <img src="/assets/workflow.png" alt="Diagrama de flujo de trabajo" style={{height: "700px" }}/>
</Frame>
