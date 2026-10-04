---
title: Inicio Rápido
description: Cómo empezar con la Plataforma FAIR
---

Esta página muestra la forma confiable más rápida de comenzar a usar la **Plataforma FAIR**: instalar la aplicación de código abierto localmente u operar tu propio despliegue.

<Card
title="Estado de la instancia comunitaria pública"
img="/assets/showcase.png"
horizontal>
La antigua instancia comunitaria pública de FAIR no está disponible actualmente. Es posible que se vuelva a desplegar en el futuro, pero su disponibilidad pública no está garantizada. Usa una instalación local o gestionada por un operador cuando necesites acceso confiable.
</Card>

## ¿Qué debería usar?
* Una instalación local es la vía disponible más rápida para evaluación, desarrollo e investigación reproducible.
* Un despliegue gestionado por un operador es apropiado para instituciones que necesitan servicio duradero, registro controlado y límites explícitos de uso de IA.

Para uso local, FAIR está diseñado para ser ligero: solo necesita un comando para instalar y un comando para ejecutar. No se requiere experiencia previa en programación.

<Accordion title="Guía de Instalación Local">
## Requisitos
El único requisito para ejecutar la plataforma es **Python 3.12 o superior**.

Cuando instalas Python desde <a href="https://www.python.org/downloads/" target="_blank">python.org</a>, ya incluye [**pip**](https://en.wikipedia.org/wiki/Pip_(package_manager)), la herramienta utilizada para instalar FAIR.

Para confirmar tu instalación de Python:

```bash
python --version
```

* Windows: Usa Símbolo del sistema o PowerShell.
* macOS/Linux: Usa Terminal.

## Proceso de instalación
Instalar FAIR es un proceso simple de tres pasos.

<Steps>
  <Step title="Abre tu terminal">
      Abre tu Símbolo del sistema (Windows) o Terminal (macOS/Linux).
  </Step>
  <Step title="Instala FAIR">
    Ejecuta el siguiente comando para descargar la plataforma desde el Índice de Paquetes de Python (PyPI):
      
    ```bash
      pip install fair-platform
    ```
      
      Esto instalará el núcleo de FAIR y sus dependencias necesarias.
  </Step>
  <Step title="Ejecuta la plataforma">
    Una vez que finalice la instalación, inicia la plataforma ejecutando:

    ```bash
      fair serve
    ```

    La terminal proporcionará una URL local (generalmente `http://localhost:3000`). Abre ese enlace en tu navegador para comenzar a usar tu instancia privada de FAIR.
  </Step>
</Steps>


## La CLI
El comando `fair` es tu punto de entrada para gestionar la plataforma. Puedes encontrar una lista completa de capacidades en nuestra [documentación de CLI](/es/cli). Los operadores de instancias compartidas también deben revisar [Controles de admisión y costos de IA](/es/platform/access-controls).

## Solución de problemas
Si algo no se ve correcto durante la instalación, consulta nuestra [guía de solución de problemas](/en/troubleshooting) o abre un issue en nuestro [GitHub](https://github.com/azapg/fair).
</Accordion>

## Próximos pasos

Más documentación próximamente, incluyendo:

- Funcionalidades de la plataforma
- Guías de desarrollo de módulos
- Proceso de lanzamiento
