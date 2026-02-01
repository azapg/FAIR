---
title: Inicio Rápido
description: Cómo instalar y configurar FAIR Platform
sidebar:
  order: 0
---

Esta guía te ayudará a instalar y configurar FAIR Platform en tu sistema.

## Requisitos

El único requisito es tener Python 3.12 o superior instalado en tu sistema, junto con pip para la gestión de paquetes. Puedes instalar Python desde <a href="https://www.python.org/downloads/" target="_blank">python.org</a> y verificar la instalación con el comando `python --version`.

## Instalación Rápida

La forma más sencilla de instalar FAIR es usando pip:

```bash
pip install fair-platform
```

## Ejecutar la Plataforma

Una vez instalado, puedes iniciar la plataforma con:

```bash
fair serve
```

La plataforma estará disponible en `http://localhost:8000` por defecto.

### Opciones del CLI

```bash
# Especificar un puerto personalizado
fair serve --port 3000

# Modo desarrollo con CORS habilitado
fair serve --dev

# Modo headless (solo API, sin frontend)
fair serve --headless
```

## Próximos Pasos

- Explora las [características de la plataforma](/es/)
- Aprende sobre el [proceso de lanzamientos](/es/development/releases)
- Comienza a construir tus propios módulos de calificación

## Solución de Problemas
En caso de problemas durante la instalación o ejecución, considera las siguientes soluciones comunes:

### Problemas con la Versión de Python

Asegúrate de estar usando Python 3.12 o superior:

```bash
python --version
```

### Puerto Ya en Uso

Si el puerto 3000 ya está en uso, especifica un puerto diferente:

```bash
fair serve --port 8080
```
