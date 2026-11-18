# Microservicio de Descripción de Imágenes (Línea A)

## Descripción
Este proyecto es un microservicio diseñado para recibir imágenes presentes en contenidos educativos y generar de forma automática descripciones textuales (alt-text). Su propósito es integrarse mediante una API REST a una arquitectura híbrida de remediación de accesibilidad gestionada por un orquestador de inteligencia artificial.

## Funcionalidad y Estructura JSON Estática
El servicio recibe una imagen mediante el endpoint `POST /api/v1/describe` (formatos aceptados: JPEG, PNG y WEBP en el campo `file`) y devuelve una respuesta JSON con **estructura estrictamente estática**:
* `tipo_imagen`: Clasificación de la imagen (`grafica_barras`, `grafica_lineas` o `diagrama_flujo`).
* `confianza_clasificacion`: Valor flotante entre `0.0` y `1.0`.
* `elementos_clave`: Objeto con llaves fijas e invariantes (`titulo`, `eje_x`, `eje_y`, `datos`, `pasos`) para evitar asignaciones dinámicas de memoria y facilitar la integración con el orquestador y modelos de visión.
* `descripcion_accesible`: Alternativa textual (alt-text) conforme a criterios WCAG.

Para consultar el esquema OpenAPI e interactuar con la API se puede abrir `http://127.0.0.1:8000/docs` una vez iniciado el servidor.

> **Nota:** La clasificación y los datos devueltos son actualmente demostrativos (Sprint 1): el servicio valida la integridad de la imagen en memoria con Pillow y elige una respuesta de ejemplo según palabras clave en el nombre del archivo (`diagrama`, `flujo`, `flow`, `linea`, `line` o `tendencia`); si no encuentra esas palabras, devuelve el ejemplo de gráfica de barras.

## Estructura del Proyecto
```text
microservicio-alt-text/
├── app/
│   ├── __init__.py      # Inicialización y documentación del paquete
│   ├── main.py          # Definición de endpoints FastAPI y gestión de recursos
│   ├── schemas.py       # Modelos Pydantic con contrato JSON estático
│   └── services.py      # Validación de imagen en memoria y lógica de descripción
├── tests/
│   └── images/          # Dataset inicial de prueba (barras, líneas y flujo)
├── requirements.txt     # Dependencias del proyecto
└── README.md            # Documentación general
```

## Requisitos Previos
* Python 3.10+
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
Para iniciar el entorno de desarrollo local, ejecuta el siguiente comando en la terminal desde la raíz del proyecto con el entorno virtual activo:

`python -m uvicorn app.main:app --reload`

El servidor estará escuchando en `http://127.0.0.1:8000`. Al acceder a la ruta principal (`/`), el servicio devolverá un mensaje JSON confirmando su estado operativo.

## Prueba con Imágenes de Ejemplo
Con el servidor en ejecución, abre `http://127.0.0.1:8000/docs`, selecciona `POST /api/v1/describe` y pulsa **Try it out**. En el campo `file`, carga una imagen y ejecuta la solicitud. El resultado será la descripción estructurada en JSON estático.

El repositorio incluye tres imágenes para probar los tipos contemplados:
* `tests/images/grafica_barras.png`
* `tests/images/grafica_lineas.png`
* `tests/images/diagrama_flujo.png`

Sube cada imagen por separado para revisar su respuesta. La API rechaza archivos que no se envíen como JPEG, PNG o WEBP o cuyo contenido binario esté corrupto.
