---
title: Instalación
description: Cómo instalar y configurar FAIR Platform
---

Esta guía te ayudará a instalar y configurar FAIR Platform en tu sistema.

## Requisitos

Antes de instalar FAIR Platform, asegúrate de tener lo siguiente:

- **Python 3.12+** - Requerido para ejecutar la plataforma
- **[uv](https://docs.astral.sh/uv/getting-started/installation/)** - Instalador y resolvedor de paquetes Python
- **[Bun](https://bun.com/get)** - Para desarrollo del frontend (opcional)

## Instalación Rápida

La forma más sencilla de instalar FAIR Platform es usando pip:

```bash
pip install fair-platform
```

## Ejecutar la Plataforma

Una vez instalado, puedes iniciar la plataforma con:

```bash
fair serve
```

La plataforma estará disponible en `http://localhost:8000` por defecto.

### Opciones de Comando

```bash
# Especificar un puerto personalizado
fair serve --port 3000

# Modo desarrollo con CORS habilitado
fair serve --dev

# Modo headless (solo API, sin frontend)
fair serve --headless
```

## Instalación para Desarrollo

Para trabajo de desarrollo en la plataforma misma:

### 1. Clonar el Repositorio

```bash
git clone https://github.com/azapg/FAIR.git
cd FAIR
```

### 2. Instalar Dependencias

```bash
uv sync
```

### 3. Construir el Frontend

```bash
./build.sh
```

Este script:
1. Construye los recursos del frontend usando Vite
2. Copia los archivos construidos al paquete Python
3. Construye el paquete Python

### 4. Ejecutar el Servidor de Desarrollo

```bash
fair serve --dev
```

## Desarrollo del Frontend

Si estás trabajando solo en el frontend:

```bash
cd frontend-dev
bun install
bun run dev
```

El servidor de desarrollo del frontend se ejecutará en el puerto 3000 y enviará las llamadas API al backend en el puerto 8000.

## Configuración de Base de Datos

Por defecto, FAIR Platform usa SQLite. Para usar PostgreSQL:

```bash
export DATABASE_URL="postgresql://user:password@localhost/dbname"
fair serve
```

## Próximos Pasos

- Explora las [características de la plataforma](/es/)
- Aprende sobre el [proceso de lanzamientos](/es/development/releases)
- Comienza a construir tus propios módulos de calificación

## Solución de Problemas

### Problemas con la Versión de Python

Asegúrate de estar usando Python 3.12 o superior:

```bash
python --version
```

### Errores de Construcción

Si la construcción falla, asegúrate de tener todas las dependencias instaladas:

```bash
# Reinstalar dependencias
uv sync

# Limpiar y reconstruir
rm -rf frontend-dev/dist
./build.sh
```

### Puerto Ya en Uso

Si el puerto 8000 ya está en uso, especifica un puerto diferente:

```bash
fair serve --port 8080
```
