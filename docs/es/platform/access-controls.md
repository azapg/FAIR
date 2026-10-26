---
title: Controles de admisión y costos de IA
description: Configura la política de registro y los créditos ponderados de ejecución de IA para un despliegue compartido de FAIR
---

FAIR trata la admisión y el acceso a IA como decisiones separadas. Admitir una cuenta no le otorga autorización para gastar en IA, y los roles de curso o permisos de extensiones no reemplazan ninguno de estos controles.

Los valores predeterminados compatibles son **registro abierto** y **controles de IA desactivados**. Las cuentas existentes pueden seguir iniciando sesión cuando el operador cambia la política de registro.

## Crear el primer administrador

Crea el primer administrador verificado desde el entorno del despliegue, sin abrir el registro público:

```bash
fair users create-admin admin@example.edu --name "Administrador de FAIR"
```

El comando solicita una contraseña y solo omite la política de registro público. Ejecuta las migraciones de base de datos antes de usarlo.

## Admisión de registro

Un administrador puede elegir un modo en **Configuración → Administración → Admisión**:

| Modo | Comportamiento del registro |
|---|---|
| Abierto | Cualquier dirección de correo válida puede registrarse. |
| Correos aprobados | La dirección normalizada debe coincidir con una dirección individual aprobada o su dominio exacto debe estar aprobado. Los subdominios no son comodines implícitos. |
| Solo con invitación | El registro requiere un token vigente, no revocado, de un solo uso y vinculado a la misma dirección normalizada. |

Los administradores pueden agregar o eliminar reglas exactas de correo o dominio y crear o revocar invitaciones. La URL de invitación se muestra una sola vez al crearla. Cuando hay un proveedor de correo configurado (`FAIR_EMAIL_ENABLED=1`), un administrador también puede pedir que FAIR envíe el enlace de invitación por correo directamente al invitado; el secreto se sigue mostrando una sola vez en la interfaz de administración como respaldo. FAIR almacena un hash del token, no el token en texto plano, y coloca el token en el fragmento de la URL para que no se envíe en la solicitud HTTP inicial. Registrarse con una invitación no marca el correo como verificado; la política normal de verificación todavía aplica.

Usa `FAIR_ADMISSION_MODE=open|allowlist|invite_only` cuando la configuración del despliegue deba ser autoritativa. Al estar presente, este valor reemplaza la configuración almacenada y bloquea el selector de modo en la interfaz administrativa. Las reglas e invitaciones siguen gestionándose en la base de datos.

Una lista de aprobación compara la dirección que declara la persona; no prueba que sea propietaria de ese buzón. Los despliegues públicos con listas de aprobación deben configurar un proveedor de correo y establecer `FAIR_EMAIL_ENABLED=1` y `FAIR_ENFORCE_EMAIL_VERIFICATION=1`. Sin verificación obligatoria, un atacante puede declarar una dirección de un dominio aprobado.

## Permisos de IA y créditos ponderados

Activa los controles de IA solo después de completar ambos pasos:

1. Clasifica cada capacidad instalada como **sin medición** o **IA**, y asigna un costo entero positivo en créditos a cada capacidad de IA.
2. Asigna a cada usuario previsto un permiso de IA **desactivado**, **limitado** o **ilimitado**. Un permiso limitado requiere un límite mensual de créditos.

Cuando los controles están activos, FAIR reserva atómicamente los créditos configurados antes de crear el despacho. Los agentes de chat, funciones y cada paso de un flujo usan esta ruta central de ejecución. Una solicitud se rechaza antes de iniciar trabajo del proveedor si la capacidad no está clasificada, el usuario no tiene permiso o se excedería el límite mensual. Los contadores se reinician el primer día del mes en UTC.

Los créditos son ponderaciones definidas por el operador, no tokens del proveedor, moneda, facturas ni un techo garantizado en dólares. Una reserva exitosa se conserva como cargo de uso inmutable aunque el proveedor falle después; los reembolsos y la conciliación de precios quedan fuera de esta primera versión. El operador debe usar ponderaciones conservadoras y conciliar el registro de auditoría con la facturación del proveedor.

`FAIR_AI_CONTROLS_ENABLED=true|false` reemplaza el interruptor almacenado y lo bloquea en la interfaz administrativa. Si se establece en `true` mientras una capacidad no está clasificada, esa capacidad falla de forma cerrada. Si se omite, el interruptor se gestiona en la base de datos y permanece desactivado por defecto.

## Despliegue por etapas recomendado

1. Respalda la base de datos y ejecuta la migración de Alembic. Esta se detiene con un error accionable si correos existentes convergen en la misma identidad normalizada; FAIR nunca fusiona ni elimina esos usuarios automáticamente.
2. Crea o confirma un administrador y mantén el registro abierto durante la validación.
3. Agrega reglas o invitaciones, prueba un registro nuevo y luego cambia el modo de admisión.
4. Clasifica todas las capacidades y asigna permisos pequeños de prueba mientras los controles de IA siguen desactivados.
5. Activa los controles, prueba chat, funciones y flujos, y revisa los registros de uso en **Configuración → Administración → Controles de IA**.
6. Aumenta los límites deliberadamente después de comparar los créditos ponderados con el uso real del proveedor.

Para revertir la política, configura `FAIR_ADMISSION_MODE=open` y `FAIR_AI_CONTROLS_ENABLED=false`, o restaura esos valores desde la interfaz administrativa cuando no haya variables de entorno. Esto conserva las reglas, invitaciones, permisos y el registro de auditoría para uso posterior.

## Seguridad y operaciones

- Mantén confidenciales y breves las invitaciones. Revoca los enlaces sin usar cuando cambie el destinatario.
- Exige verificación de correo cuando la admisión dependa de una dirección o dominio aprobado. En modo de invitación, la posesión del enlace es la credencial; protégelo como un enlace de restablecimiento de contraseña.
- Coloca límites de frecuencia y monitoreo en el proxy inverso o WAF para los endpoints públicos de registro e inicio de sesión. Las listas de IP no forman parte de la política de la aplicación y suelen ser demasiado generales para un despliegue reutilizable.
- Usa HTTPS, un `SECRET_KEY` fuerte, cuentas administrativas controladas, respaldos y privilegios mínimos en la base de datos.
- Trata la interfaz como orientación. La API aplica en el servidor la autorización administrativa, reglas de admisión, permisos y reserva de créditos.
- La admisión no suspende cuentas existentes, asigna membresía de cursos, concede efectos de extensiones ni prueba la propiedad de una dirección de correo.

La antigua instancia comunitaria pública de FAIR no está disponible actualmente y su disponibilidad futura no está garantizada. Estos controles son neutrales al despliegue y pueden ser usados por cualquier operador de FAIR.
