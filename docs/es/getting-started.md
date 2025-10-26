# Primeros pasos

Esta guía rápida explica cómo instalar FAIR para desarrollo local. Necesitas
versiones recientes de [uv](https://docs.astral.sh/uv/) y
[Bun](https://bun.sh/).

## 1. Clona el repositorio

```bash
git clone https://github.com/your-org/FAIR.git
cd FAIR
```

## 2. Instala las dependencias

Instala las dependencias de Python con `uv` y las del frontend con Bun:

```bash
uv sync
cd frontend-dev
bun install
cd ..
```

## 3. Ejecuta la compilación

El proyecto incluye un script que genera los recursos del frontend, el paquete
Python y la documentación:

```bash
./build.sh
```

Los artefactos resultantes se copian a `src/fair_platform/frontend/dist/` para
que el backend pueda servirlos directamente.

## 4. Inicia el backend

```bash
uv run fair --dev
```

La API estará disponible en `http://127.0.0.1:8000` y el frontend en la ruta
principal. Visita `http://127.0.0.1:8000/docs/` para abrir el sitio generado con
MkDocs.

## Próximos pasos

- Explora la referencia para desarrolladores y aprende sobre el proceso de
  lanzamientos.
- Experimenta con el sistema de plugins para extender la plataforma.
- Cuéntanos qué guías faltan para seguir ampliando la documentación.
