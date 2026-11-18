# AI Project Context: Microservicio de Descripción de Imágenes (Línea A)

> **Propósito de este archivo:** Este documento proporciona el contexto técnico, arquitectónico y de reglas de negocio necesario para que cualquier asistente o agente de Inteligencia Artificial comprenda de inmediato el estado, las restricciones de memoria y los contratos del proyecto antes de generar o modificar código.

---

## 1. Resumen del Proyecto y Contexto de Tesis

- **Nombre:** Microservicio de Descripción de Imágenes (Línea A).
- **Objetivo:** Recibir imágenes de contenidos educativos digitales y generar automáticamente descripciones textuales accesibles (*alt-text*) conformes al estándar **WCAG**, además de extraer sus elementos estructurales clave.
- **Arquitectura Global:** Forma parte de una **arquitectura híbrida de remediación de accesibilidad** gobernada por un **Orquestador de Inteligencia Artificial**. Este microservicio actúa como un nodo especializado (Línea A) que se comunica vía API REST con el orquestador.
- **Alcance de Clasificación:** Soporta tres tipologías de imágenes educativas:
  1. `grafica_barras` (Gráficas de barras)
  2. `grafica_lineas` (Gráficas de líneas / tendencias)
  3. `diagrama_flujo` (Diagramas de flujo de procesos/decisiones)

---

## 2. Stack Tecnológico

- **Lenguaje:** Python 3.10+
- **Framework Web / API:** FastAPI (`0.141.1`)
- **Servidor ASGI:** Uvicorn (`0.46.0`)
- **Validación de Contratos y Esquemas:** Pydantic v2 (`>=2.6.0`)
- **Procesamiento de Imágenes:** Pillow (`>=10.2.0`)
- **Recepción de Archivos (`multipart/form-data`):** `python-multipart` (`>=0.0.9`)

---

## 3. Estructura del Repositorio

```text
microservicio-alt-text/
├── app/
│   ├── __init__.py      # Documentación del paquete principal
│   ├── main.py          # Instancia FastAPI, endpoints HTTP y liberación de archivos en memoria
│   ├── schemas.py       # Modelos Pydantic con contrato JSON 100% estático (extra="forbid")
│   └── services.py      # Validación binaria con Pillow y lógica de análisis/descripción
├── tests/
│   └── images/          # Dataset de imágenes de prueba para validar el contrato
│       ├── diagrama_flujo.png
│       ├── grafica_barras.png
│       └── grafica_lineas.png
├── requirements.txt     # Dependencias fijadas del entorno virtual
├── README.md            # Guía de instalación, uso y documentación general
└── AI_CONTEXT.md        # Este archivo de contexto para asistentes de IA
```

---

## 4. Reglas Arquitectónicas Inquebrantables (CRÍTICO)

Cualquier modificación o nueva funcionalidad que una IA proponga **DEBE** respetar estas tres reglas:

### Regla 1: Estructura JSON Estrictamente Estática (Sin Esquemas Modulares/Dinámicos)
- **Contexto de diseño:** Por requerimiento de arquitectura y optimización de memoria con el Orquestador y los motores de inferencia (VLM *Guided Decoding / Structured Outputs*), **la estructura JSON de salida debe ser 100% estática**.
- **Prohibición:** No utilizar `Dict[str, Any]`, `List[Dict[str, Any]]`, ni omitir llaves según el tipo de imagen.
- **Implementación obligatoria:**
  - Todas las respuestas de `POST /api/v1/describe` deben devolver **exactamente las mismas llaves** en la raíz y en todos los sub-objetos (`elementos_clave`, `eje_x`, `eje_y`, `datos`, `pasos`).
  - Cuando un campo no aplica a un tipo de imagen (por ejemplo, `eje_x` o `datos` en un `diagrama_flujo`, o `pasos` en una `grafica_barras`), el campo **se mantiene presente** con su valor vacío estático (`""`, `[]` o `null`), nunca se elimina del JSON.
  - Todos los modelos Pydantic en `app/schemas.py` deben conservar `model_config = ConfigDict(extra="forbid")`.

### Regla 2: Gestión Estricta de Memoria (Prevención de Memory Leaks)
- Todo flujo de bytes (`io.BytesIO`) e instancia de `PIL.Image` debe abrirse dentro de bloques contextuales (`with`) para garantizar la liberación inmediata de buffers en RAM.
- En los endpoints de `app/main.py`, el objeto `UploadFile` (`SpooledTemporaryFile`) siempre debe cerrarse explícitamente con `await file.close()` dentro de un bloque `finally`.

### Regla 3: Enfoque en Accesibilidad WCAG
- El campo `descripcion_accesible` debe redactarse siguiendo las buenas prácticas de accesibilidad web (identificar el tipo de recurso visual, su propósito/título y la tendencia, comparación o secuencia principal sin redundancias innecesarias).

---

## 5. Contrato Actual de la API y Esquema JSON Estático

### Endpoints Disponibles
1. **`GET /`**
   - **Propósito:** Health check del servicio.
   - **Respuesta:** `{"mensaje": "Servidor de la Línea A funcionando correctamente"}`
2. **`POST /api/v1/describe`**
   - **Entrada:** `multipart/form-data` con el campo `file` (`image/jpeg`, `image/png` o `image/webp`).
   - **Errores:** `HTTP 400` si el tipo MIME no es válido, si el archivo está vacío o si el binario de la imagen está corrupto.
   - **Salida (`200 OK`):** Validada por `ImageDescriptionResponse`.

### Plantilla Invariante del JSON de Salida (`ImageDescriptionResponse`)
```json
{
  "tipo_imagen": "grafica_barras | grafica_lineas | diagrama_flujo",
  "confianza_clasificacion": 0.95,
  "elementos_clave": {
    "titulo": "Texto del título o cadena vacía",
    "eje_x": {
      "nombre": "Nombre del eje o cadena vacía",
      "etiquetas": ["etiqueta1", "etiqueta2"],
      "rango": []
    },
    "eje_y": {
      "nombre": "Nombre del eje o cadena vacía",
      "etiquetas": [],
      "rango": [0.0, 100.0]
    },
    "datos": [
      {
        "categoria": "Nombre categoría",
        "valor": 35.0
      }
    ],
    "pasos": [
      {
        "id": 1,
        "tipo": "inicio | proceso | decision | fin",
        "texto": "Descripción del paso",
        "si": "Destino afirmativo o null",
        "no": "Destino negativo o null"
      }
    ]
  },
  "descripcion_accesible": "Descripción textual accesible conforme a WCAG."
}
```

---

## 6. Estado Actual del Proyecto y Hoja de Ruta (Sprints)

- **Porcentaje de avance global:** **~35%**
- **Sprint 0 (100% Completado):** Configuración inicial del repositorio, entorno virtual, FastAPI base y health check.
- **Sprint 1 (100% Completado):**
  - Modularización en el paquete `app/` (`main.py`, `schemas.py`, `services.py`).
  - Validación de tipos MIME e integridad binaria con `Pillow`.
  - Refactorización hacia **estructura JSON estática** para control de memoria.
  - Respuestas demostrativas (*mock*) basadas en palabras clave del nombre de archivo (`diagrama`/`flujo`/`flow`, `linea`/`line`/`tendencia`, o `grafica_barras` por defecto).
  - Dataset inicial en `tests/images/`.
- **Sprint 2 (Próximo Paso - Pendiente):**
  - Sustituir la heurística basada en `filename` dentro de `procesar_imagen_educativa()` (`app/services.py`) por inferencia visual real (VLM / clasificador + OCR) manteniendo intacta la firma de salida y el contrato `ImageDescriptionResponse`.
- **Sprint 3 y 4 (Pendientes):**
  - Refinamiento de prompts/plantillas WCAG, límites de tamaño de archivo en bytes, pruebas automatizadas con `pytest` y contenerización (`Dockerfile`) para integración con el Orquestador.

---

## 7. Comandos Útiles para Desarrollo

- **Activar entorno virtual (Windows PowerShell):**
  ```powershell
  .\venv\Scripts\activate
  ```
- **Ejecutar servidor de desarrollo:**
  ```powershell
  python -m uvicorn app.main:app --reload
  ```
- **Documentación interactiva (Swagger UI):**
  `http://127.0.0.1:8000/docs`

---

## 8. Directrices para la IA al Continuar el Proyecto

1. **Idioma:** Todo el código, comentarios, *docstrings* (formato PEP 257 / Google), nombres de campos del JSON y mensajes de error HTTP deben mantenerse en **español**.
2. **Punto de extensión para IA/Visión:** Al integrar el modelo de visión en el Sprint 2, hazlo de forma desacoplada en `app/services.py` (o en un submódulo `app/vision.py` invocado desde `procesar_imagen_educativa`), asegurándote de que la salida del modelo se valide directamente contra `ImageDescriptionResponse` sin alterar las llaves estáticas definidas en `app/schemas.py`.
