# Microservicio de Descripción de Imágenes (Línea A)

## Descripción
Este proyecto es un microservicio diseñado para recibir imágenes presentes en contenidos educativos y generar de forma automática descripciones textuales (alt-text). Su propósito es integrarse mediante una API REST a una arquitectura híbrida de remediación de accesibilidad gestionada por un orquestador de inteligencia artificial.

## Funcionalidad
El servicio recibe una imagen y devuelve una respuesta JSON con:
* El tipo de imagen: gráfica de barras, gráfica de líneas o diagrama de flujo.
* Una confianza de clasificación.
* Los elementos clave disponibles, como título, ejes, datos o pasos.
* Una descripción accesible.

El endpoint `POST /api/v1/describe` acepta imágenes JPEG, PNG y WEBP mediante el campo `file`. La respuesta incluye `tipo_imagen`, `confianza_clasificacion`, `elementos_clave` y `descripcion_accesible`. Para consultar y probar la API también se puede abrir `http://127.0.0.1:8000/docs` una vez iniciado el servidor.

> **Nota:** La clasificación y los datos devueltos son actualmente demostrativos: el servicio elige una respuesta de ejemplo según palabras clave en el nombre del archivo (`diagrama`, `flujo`, `flow`, `linea`, `line` o `tendencia`); si no encuentra esas palabras, devuelve el ejemplo de gráfica de barras. No realiza todavía reconocimiento visual real del contenido.

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

## Prueba con imágenes de ejemplo
Con el servidor en ejecución, abre `http://127.0.0.1:8000/docs`, selecciona `POST /api/v1/describe` y pulsa **Try it out**. En el campo `file`, carga una imagen y ejecuta la solicitud. El resultado será la descripción estructurada en JSON.

El repositorio incluye tres imágenes para probar los tipos contemplados:
* `tests/images/grafica_barras.png`
* `tests/images/grafica_lineas.png`
* `tests/images/diagrama_flujo.png`

Sube cada imagen por separado para revisar su respuesta. La API también rechaza archivos que no se envíen como JPEG, PNG o WEBP.