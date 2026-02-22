---
title: Configuración
description: Personaliza FAIR según tu flujo de trabajo
---

La plataforma ofrece varias configuraciones para personalizar tu experiencia, controlar notificaciones y ajustar el comportamiento de la IA. Esta página explica cada opción y cómo usarla de forma efectiva.

## Cuenta y preferencias
Esta sección cubre configuraciones relacionadas con tu cuenta y con la forma en que interactúas con la plataforma FAIR. Puedes encontrar esta sección bajo `CUENTA Y PREFERENCIAS` dentro del menú de configuración.

### Preferencias

Estas opciones controlan tu experiencia personal en el espacio de trabajo.

<ResponseField name="Tema" type="select" required>
Elige cómo se ve FAIR: `Sistema`, `Claro` u `Oscuro`.
</ResponseField>

<ResponseField name="Idioma" type="select" required>
Elige el idioma de tu interfaz: `Inglés` o `Español`.
</ResponseField>

<ResponseField name="Vista simple" type="boolean" required>
Cuando está activada, FAIR usa una interfaz más compacta y enfocada, con menos ruido visual.
</ResponseField>

### Notificaciones

Las notificaciones te permiten elegir exactamente qué actualizaciones quieres recibir.

| Grupo | Configuración | Qué recibes |
|---|---|---|
| Calificación e IA | Finalización por lotes | Alerta cuando la IA termina de calificar un lote completo. |
| Calificación e IA | Banderas de baja confianza | Alerta cuando la IA no está segura y recomienda revisión manual. |
| Calificación e IA | Detección de plagio/IA | Alerta por alta similitud o patrones de texto probablemente generados por IA. |
| Calificación e IA | Límites de tokens/cuota | Alerta cuando te acercas a límites de uso o crédito. |
| Actividad estudiantil | Nuevas entregas | Alerta cuando estudiantes envían trabajo nuevo. |
| Actividad estudiantil | Entregas tardías | Alerta cuando un trabajo llega después de la fecha límite. |
| Actividad estudiantil | Retroalimentación leída | Alerta cuando estudiantes abren calificaciones o comentarios. |
| Actividad estudiantil | Solicitudes de recalificación | Alerta cuando estudiantes piden revisión de nota. |
| Colaboración | Cambios de rúbrica | Alerta cuando se editan rúbricas compartidas. |
| Colaboración | Sobrescritura de calificaciones | Alerta cuando un TA/co-docente cambia una nota sugerida por IA. |
| Colaboración | Nuevas invitaciones a cursos | Alerta cuando te agregan a una clase o grupo. |
| Sistema y entrega | Resumen diario | Recibe un único resumen en lugar de múltiples alertas instantáneas. |
| Sistema y entrega | Notificaciones del navegador | Recibe notificaciones push en tiempo real mientras usas la plataforma. |
| Sistema y entrega | Actualizaciones de la plataforma | Recibe anuncios sobre nuevas funciones y mantenimiento de FAIR. |

## Funciones de IA
Esta sección cubre configuraciones relacionadas con el comportamiento del asistente y con los modelos predeterminados. Puedes encontrar esta sección bajo `FUNCIONES DE IA` dentro del menú de configuración.

### Personalización

Personaliza cómo se comporta el asistente contigo.

<ResponseField name="Personalidad del chat" type="select" required>
Selecciona el tono del asistente: `Predeterminada` (equilibrada), `Profesional` (concisa/formal) o `Amigable` (cercana/motivadora).
</ResponseField>

<ResponseField name="Sobre ti (Instrucciones personalizadas)" type="string" required>
Agrega contexto como tu rol, programa o filosofía de evaluación para que la IA responda mejor a tu flujo de trabajo.
</ResponseField>

<ResponseField name="Habilitar memoria persistente" type="boolean" required>
Permite que la IA recuerde tu contexto personalizado de **Sobre ti** entre sesiones.
</ResponseField>

### Modelos

<ResponseField name="Búsqueda web" type="boolean" required>
Permite que el asistente use búsqueda web cuando necesita información en tiempo real.
</ResponseField>

<ResponseField name="Modelo predeterminado" type="select" required>
Elige qué modelo usa FAIR por defecto en el chat.
</ResponseField>

## Consejos

- Comienza habilitando solo alertas esenciales y agrega más según necesidad.
- Usa **Resumen diario** si las alertas instantáneas son demasiado frecuentes.
- Usa **Vista simple** si prefieres pantallas más densas y con menos distracciones.
