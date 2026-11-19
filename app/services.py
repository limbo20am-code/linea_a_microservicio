"""
Capa de servicios para el procesamiento y análisis de imágenes educativas.

Este módulo actúa como puente entre los controladores HTTP de FastAPI y el
motor de visión por computadora (`app.vision`), garantizando que cada imagen
sea procesada en un único flujo de memoria seguro y devuelva una estructura
JSON 100% estática conforme al contrato `ImageDescriptionResponse`.
"""

from app.schemas import ImageDescriptionResponse
from app.vision import analizar_imagen_educativa


def procesar_imagen_educativa(
    file_bytes: bytes, filename: str = ""
) -> ImageDescriptionResponse:
    """
    Procesa una imagen educativa mediante el motor de visión y OCR en CPU,
    devolviendo su clasificación, elementos clave y descripción accesible WCAG
    bajo una estructura JSON estrictamente estática.

    Args:
        file_bytes (bytes): Contenido binario de la imagen cargada.
        filename (str, opcional): Nombre original del archivo subido (conservado
            por compatibilidad de firma con llamadas existentes). Por defecto "".

    Raises:
        ValueError: Si los bytes están vacíos o no corresponden a una imagen válida.

    Returns:
        ImageDescriptionResponse: Modelo validado con esquema JSON estático.
    """
    _ = filename
    return analizar_imagen_educativa(file_bytes)
