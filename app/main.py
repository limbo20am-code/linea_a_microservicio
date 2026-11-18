"""
Punto de entrada de la API REST para el Microservicio de Descripción de Imágenes (Línea A).

Expone los endpoints HTTP para la verificación de estado del servicio y la
generación de alternativas textuales (alt-text) estructuradas bajo un esquema
JSON estático conforme a las pautas de accesibilidad WCAG.
"""

from fastapi import FastAPI, File, HTTPException, UploadFile
from app.schemas import ImageDescriptionResponse
from app.services import procesar_imagen_educativa

# Tipos MIME permitidos por el microservicio
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}

app = FastAPI(
    title="Microservicio de Descripción de Imágenes (Línea A)",
    description=(
        "API REST para la generación de alternativas textuales (alt-text) "
        "conformes a WCAG mediante una estructura JSON estática."
    ),
    version="1.0.0",
)


@app.get("/", summary="Verificar estado del servicio")
def read_root() -> dict:
    """
    Endpoint de verificación de salud (health check) para comprobar que el
    microservicio de la Línea A se encuentra operativo.

    Returns:
        dict: Mensaje confirmando el estado activo del servidor.
    """
    return {"mensaje": "Servidor de la Línea A funcionando correctamente"}


@app.post(
    "/api/v1/describe",
    response_model=ImageDescriptionResponse,
    summary="Generar descripción accesible de una imagen educativa",
)
async def describe_image(file: UploadFile = File(...)) -> ImageDescriptionResponse:
    """
    Recibe un archivo de imagen educativa, valida su formato e integridad y
    devuelve su clasificación, elementos clave y descripción accesible en una
    estructura JSON estrictamente estática.

    Args:
        file (UploadFile): Imagen enviada mediante `multipart/form-data`
            (formatos soportados: JPEG, PNG, WEBP).

    Raises:
        HTTPException (400): Si el tipo MIME no está permitido o si los bytes
            del archivo no corresponden a una imagen íntegra.

    Returns:
        ImageDescriptionResponse: Objeto validado con estructura JSON estática.
    """
    # 1. Validar que el tipo MIME del archivo corresponda a una imagen permitida
    if file.content_type not in ALLOWED_MIME_TYPES:
        await file.close()
        raise HTTPException(
            status_code=400,
            detail="El archivo enviado no es una imagen válida (debe ser JPEG, PNG o WEBP).",
        )

    try:
        # 2. Leer los bytes de la imagen en memoria
        contents = await file.read()

        # 3. Procesar la imagen y construir la respuesta con esquema JSON estático
        resultado = procesar_imagen_educativa(contents, filename=file.filename or "")
        return resultado
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        # 4. Liberar explícitamente el archivo temporal de FastAPI/Starlette
        await file.close()
