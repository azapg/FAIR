---
title: Automatización de Lanzamientos
description: Cómo funciona el pipeline de lanzamientos en FAIR Platform
---

## Flujo de desarrollo local

Usa el comando de desarrollo dedicado para trabajar en backend y frontend al mismo tiempo. Inicia el API de FastAPI en modo headless con CORS habilitado en el puerto 8000 y ejecuta el servidor de desarrollo de Vite en `frontend-dev`:

```bash
fair dev
```

Opciones comunes:

```bash
# Backend en un puerto personalizado
fair dev --port 9000

# Solo backend (sin servidor de frontend)
fair dev --no-frontend

# Servir el frontend empaquetado junto con el frontend de desarrollo
fair dev --no-headless
```

Este proyecto incluye un pipeline ligero de lanzamientos que se ejecuta cada vez que se sube una etiqueta Git que comienza con `v` a GitHub. El flujo de trabajo se encuentra en [`.github/workflows/release.yml`](https://github.com/azapg/FAIR/blob/main/.github/workflows/release.yml) y se encarga de los metadatos de versión, validación de compilación, creación de lanzamiento y publicación opcional de paquetes.

## Gestión de Versiones Basada en Etiquetas

1. Crea una etiqueta de versión semántica convencional como `v0.5.0` y súbela a GitHub:
   ```bash
   git push origin v0.5.0
   ```

2. El flujo de trabajo de lanzamiento normaliza la etiqueta (por ejemplo `v0.5.0` → `0.5.0`) y ejecuta `scripts/sync_version.py` para escribir ese valor en `pyproject.toml` y `src/fair_platform/__init__.py` antes de que se ejecuten los pasos de compilación. El script también se puede ejecutar localmente si necesitas verificar o pre-poblar metadatos de versión:
   ```bash
   python scripts/sync_version.py --version v0.5.0
   ```

3. Los cambios de versión solo existen dentro de la ejecución del flujo de trabajo; no se comprometen de vuelta al repositorio. La versión efectiva del paquete por lo tanto siempre coincide con la etiqueta que activó el lanzamiento, y los desarrolladores son libres de elegir cómo gestionan los incrementos de versión en ramas de larga duración.

## Flujo de Compilación y Lanzamiento

Cuando una etiqueta activa el flujo de trabajo, realiza las siguientes acciones:

1. Instala el toolchain (Python 3.12, [uv](https://docs.astral.sh/uv/) y [Bun](https://bun.sh/))
2. Instala dependencias bloqueadas del frontend (`bun install --frozen-lockfile`)
3. Ejecuta el pipeline de compilación del proyecto vía `./build.sh`. Este paso realiza la compilación Bun/Vite del frontend, copia los recursos al paquete Python y ejecuta `uv build` para producir artefactos en `dist/`
4. Publica un lanzamiento de GitHub con notas generadas automáticamente y adjunta todos los artefactos de compilación desde `dist/`. Las notas de lanzamiento son generadas por GitHub y agrupan commits por tipo (características, correcciones, documentación, etc.) basándose en los títulos de PR fusionados y mensajes de commit desde la etiqueta anterior
5. Marca el lanzamiento como prelanzamiento cuando la etiqueta contiene un guión (por ejemplo `v0.6.0-rc1`). Las etiquetas de versión semántica simples como `v1.0.0` se tratan como lanzamientos de producción

## Publicación en PyPI

La publicación en PyPI es opcional. Establece el secreto del repositorio `PYPI_API_TOKEN` para habilitarla. El flujo de trabajo solo intenta publicar cuando **ambas** de las siguientes condiciones son verdaderas:

- La etiqueta no tiene guión (por ejemplo `v1.2.3`)
- `PYPI_API_TOKEN` está definido

Los paquetes se suben desde el directorio `dist/` usando [`pypa/gh-action-pypi-publish`](https://github.com/pypa/gh-action-pypi-publish). Para etiquetas de prelanzamiento o cuando el secreto está ausente, el flujo de trabajo omite el paso de PyPI pero aún produce el lanzamiento de GitHub y los recursos adjuntos.

Si necesitas publicar en TestPyPI en su lugar, agrega un paso similar con su propio secreto (por ejemplo `TEST_PYPI_API_TOKEN`) y apúntalo a la URL del repositorio alternativo. El paso existente es una buena plantilla.

## Ejecuciones de Prueba Locales

Puedes ensayar el proceso de lanzamiento localmente para asegurar que la compilación tenga éxito antes de subir una etiqueta:

```bash
python scripts/sync_version.py --version 0.0.0-dev
./build.sh
```

El script mantiene los números de versión alineados, mientras que `./build.sh` reproduce la misma secuencia de pasos de frontend y empaquetado que el flujo de trabajo ejecuta en CI. Limpia el repositorio después si no quieres mantener el cambio de versión temporal.
