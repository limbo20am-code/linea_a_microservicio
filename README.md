# Microservicio de Descripción de Imágenes (Línea A)

## Descripción
Este proyecto es un microservicio diseñado para recibir imágenes presentes en contenidos educativos y generar de forma automática descripciones textuales (alt-text)[cite: 1]. Su propósito es integrarse mediante una API REST a una arquitectura híbrida de remediación de accesibilidad gestionada por un orquestador de inteligencia artificial[cite: 1].

## Requisitos Previos
* Python 3.x
* Entorno virtual de Python configurado

## Configuración Inicial
1. Clonar este repositorio.
2. Crear un entorno virtual en la raíz del proyecto:
   `python -m venv venv`
3. Activar el entorno virtual:
   `.\venv\Scripts\activate` (En Windows)
4. Instalar las dependencias necesarias:
   `pip install -r requirements.txt`

## Ejecución del Servidor
Para iniciar el entorno de desarrollo local, ejecuta el siguiente comando en la terminal con el entorno virtual activo:

`python -m uvicorn main:app --reload`

El servidor estará escuchando en `http://127.0.0.1:8000`. Al acceder a la ruta principal (`/`), el servicio devolverá un mensaje JSON confirmando su estado operativo.