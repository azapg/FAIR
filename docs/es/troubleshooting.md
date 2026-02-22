---
title: Problemas comunes
---

### Python no reconocido

Si `python` o `pip` no son reconocidos en Windows, reinicia tu computadora o reinstala Python y marca la casilla que dice **"Add Python to PATH"** durante la instalación.

### Versión incorrecta de Python

Verifica tu versión:

```bash
python --version
```

Debes usar **Python 3.12 o superior**.

### Puerto ya en uso

Si el puerto 8000 está ocupado, elige otro:

```bash
fair serve --port 8080
