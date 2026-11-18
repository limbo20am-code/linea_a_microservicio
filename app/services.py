"""
Capa de servicios para el procesamiento y análisis de imágenes educativas.

Este módulo valida la integridad binaria de la imagen recibida liberando de
inmediato el buffer en memoria y construye la respuesta utilizando una
estructura JSON estática (todas las llaves permanecen fijas sin importar el
tipo de imagen).
"""

import io
from PIL import Image, UnidentifiedImageError


def validar_imagen_en_memoria(file_bytes: bytes) -> None:
    """
    Verifica que los bytes recibidos correspondan a una imagen íntegra y válida.

    Utiliza un gestor de contexto (`with`) sobre el flujo en memoria para garantizar
    que los descriptores y buffers de Pillow se liberen inmediatamente después de
    la verificación, evitando fugas de memoria (memory leaks) entre peticiones.

    Args:
        file_bytes (bytes): Contenido binario del archivo de imagen.

    Raises:
        ValueError: Si el archivo está vacío o los bytes no corresponden a una
            imagen válida reconocible por Pillow.
    """
    if not file_bytes:
        raise ValueError("El archivo de imagen enviado está vacío.")

    try:
        with io.BytesIO(file_bytes) as buffer:
            with Image.open(buffer) as image:
                image.verify()
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("El archivo enviado está corrupto o no es una imagen válida.") from exc


def procesar_imagen_educativa(file_bytes: bytes, filename: str = "") -> dict:
    """
    Procesa una imagen educativa y devuelve su clasificación, elementos clave y
    descripción accesible en una estructura JSON estrictamente estática.

    Nota de estado actual (Sprint 1):
        La clasificación se determina de forma demostrativa mediante palabras clave
        en el nombre del archivo. En el Sprint 2 se integrará el modelo de visión (VLM)
        manteniendo exactamente esta misma estructura estática de salida.

    Args:
        file_bytes (bytes): Contenido binario de la imagen cargada.
        filename (str, opcional): Nombre original del archivo subido. Por defecto "".

    Returns:
        dict: Diccionario con esquema fijo compatible con `ImageDescriptionResponse`.
    """
    # 1. Validar integridad de la imagen y liberar el buffer inmediatamente
    validar_imagen_en_memoria(file_bytes)

    fn = (filename or "").lower()

    # 2. Clasificación demostrativa con estructura JSON 100% estática en todas las ramas
    if "diagrama" in fn or "flujo" in fn or "flow" in fn:
        return {
            "tipo_imagen": "diagrama_flujo",
            "confianza_clasificacion": 0.94,
            "elementos_clave": {
                "titulo": "Proceso de Registro de Usuario",
                "eje_x": {
                    "nombre": "",
                    "etiquetas": [],
                    "rango": [],
                },
                "eje_y": {
                    "nombre": "",
                    "etiquetas": [],
                    "rango": [],
                },
                "datos": [],
                "pasos": [
                    {
                        "id": 1,
                        "tipo": "inicio",
                        "texto": "Inicio del formulario",
                        "si": None,
                        "no": None,
                    },
                    {
                        "id": 2,
                        "tipo": "decision",
                        "texto": "¿Datos válidos?",
                        "si": "Guardar",
                        "no": "Mostrar error",
                    },
                ],
            },
            "descripcion_accesible": (
                "Diagrama de flujo que muestra el proceso de registro de usuario "
                "evaluando la validez de los datos."
            ),
        }

    if "linea" in fn or "line" in fn or "tendencia" in fn:
        return {
            "tipo_imagen": "grafica_lineas",
            "confianza_clasificacion": 0.91,
            "elementos_clave": {
                "titulo": "Evolución de Matrícula Universitaria",
                "eje_x": {
                    "nombre": "Años",
                    "etiquetas": ["2024", "2025", "2026"],
                    "rango": [],
                },
                "eje_y": {
                    "nombre": "Estudiantes",
                    "etiquetas": [],
                    "rango": [0.0, 500.0],
                },
                "datos": [
                    {"categoria": "2024", "valor": 300.0},
                    {"categoria": "2025", "valor": 420.0},
                    {"categoria": "2026", "valor": 480.0},
                ],
                "pasos": [],
            },
            "descripcion_accesible": (
                "Gráfica de líneas que muestra la evolución de la matrícula "
                "universitaria con tendencia ascendente de 2024 a 2026."
            ),
        }

    # Respuesta por defecto para gráficas de barras
    return {
        "tipo_imagen": "grafica_barras",
        "confianza_clasificacion": 0.95,
        "elementos_clave": {
            "titulo": "Comparativa de Asignaturas",
            "eje_x": {
                "nombre": "Materias",
                "etiquetas": ["Redes", "IA"],
                "rango": [],
            },
            "eje_y": {
                "nombre": "Inscritos",
                "etiquetas": [],
                "rango": [0.0, 40.0],
            },
            "datos": [
                {"categoria": "Redes", "valor": 35.0},
                {"categoria": "IA", "valor": 40.0},
            ],
            "pasos": [],
        },
        "descripcion_accesible": (
            "Gráfica de barras comparativa entre las materias de Redes e IA."
        ),
    }
