---
title: Autenticación
description: Cómo funciona la autenticación en la API de Fair Platform (tokens JWT) y cómo llamar endpoints de forma segura.
---

Esta página explica cómo autenticarte cuando llamas la **API de Fair Platform** directamente.

> Estado: **placeholder**. Existe para evitar 404s y para ofrecer una estructura estable mientras la referencia completa de la API se va documentando.

## Resumen

Fair Platform utiliza **autenticación basada en tokens** (normalmente **JWT**). El flujo típico es:

1. Inicias sesión usando un endpoint de autenticación
2. Recibes un **token de acceso**
3. Incluyes el token en solicitudes posteriores usando el header `Authorization`

## Enviar el token

En la mayoría de solicitudes autenticadas, envía este header:

```/dev/null/auth-header.txt#L1-1
Authorization: Bearer <ACCESS_TOKEN>
```

## Ejemplo (cURL)

```/dev/null/authenticated-request.sh#L1-6
FAIR_TOKEN="tu-token-aqui"

curl -H "Authorization: Bearer $FAIR_TOKEN" \
     -H "Content-Type: application/json" \
     http://localhost:3000/api/health
```

## Ejemplo (JavaScript fetch)

```/dev/null/authenticated-request.js#L1-19
const token = process.env.FAIR_TOKEN;

const res = await fetch("http://localhost:3000/api/health", {
  headers: {
    Authorization: `Bearer ${token}`,
  },
});

if (!res.ok) throw new Error(`Request failed: ${res.status}`);
console.log(await res.json());
```

## Códigos de estado comunes

- `401 Unauthorized`: falta el token, el token expiró, o el token es inválido
- `403 Forbidden`: el token es válido, pero el usuario no tiene permisos suficientes
- `422 Unprocessable Entity`: falló la validación de esquema (muy común cuando el body JSON no cumple)

## Notas de seguridad

- No hardcodees tokens en el código ni los subas a git.
- En desarrollo, usa variables de entorno (por ejemplo `FAIR_TOKEN`).
- Si integras servicios externos (LLMs, storage, etc.), guarda las claves en variables de entorno o un gestor de secretos.

## Próximos pasos

- `es/api-reference/overview`: resumen de cómo está organizada la API
- `es/api-reference/endpoints`: directorio de endpoints (placeholder / próximamente)
- `en/api-reference/authentication`: versión en inglés (más completa mientras se traduce)