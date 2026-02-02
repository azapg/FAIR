---
title: Resumen de la Referencia de API
description: Visión general de la API HTTP de Fair Platform, su estructura y autenticación.
---

Esta sección es una **traducción inicial (placeholder)** de la documentación de la API. Su objetivo es evitar páginas 404 y permitir que los usuarios seleccionen **Español** como idioma en todo el sitio mientras completamos la traducción.

## URL base

- Al ejecutar localmente con `fair serve`, la interfaz web normalmente se expone en `http://localhost:3000`.
- La API suele servirse bajo el prefijo `/api` en el mismo origen.

En algunos flujos de trabajo (por ejemplo, modo desarrollo con frontend separado), la API puede estar en otro puerto, por ejemplo `http://localhost:8000/api`, dependiendo de los flags del CLI y tu configuración.

## Qué ofrece la API

A alto nivel, la API permite:

- Autenticación y gestión de usuarios/sesiones
- Operaciones CRUD para entidades principales (cursos, asignaciones, entregas, artefactos)
- Descubrimiento y configuración de plugins/extensiones (cuando están habilitados)
- Flujos de trabajo que orquesta el frontend

## Formato de solicitudes y respuestas

- La mayoría de endpoints usan **JSON**.
- Cargas de archivos (entregas/artefactos) pueden usar `multipart/form-data`.

## Autenticación

Fair Platform utiliza autenticación basada en tokens (JWT). De forma general:

1. Inicias sesión mediante un endpoint de autenticación.
2. Recibes un token de acceso.
3. En solicitudes posteriores envías `Authorization: Bearer <token>`.

## Próximos pasos

- `api-reference/authentication` (pendiente de traducción)
- `api-reference/endpoints` (pendiente de traducción)