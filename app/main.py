"""
Punto de entrada de la API REST para el Microservicio de Descripción de Imágenes (Línea A).

Expone los endpoints HTTP para la verificación de estado del servicio y la
generación de alternativas textuales (alt-text) estructuradas bajo un esquema
JSON estático conforme a las pautas de accesibilidad WCAG 2.2.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, File, HTTPException, UploadFile
from app.schemas import ImageDescriptionResponse
from app.services import procesar_imagen_educativa
from app.vision import GestorMotorOCR

# Tipos MIME permitidos por el microservicio
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}

# Límite máximo de tamaño de imagen en memoria (10 MB) para prevenir saturación de RAM
MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """
    Gestor del ciclo de vida de la aplicación FastAPI.

    Inicializa una única instancia del motor OCR en memoria al arrancar el
    servidor y libera su referencia al finalizar el proceso.
    """
    GestorMotorOCR.inicializar()
    yield
    GestorMotorOCR.liberar()


app = FastAPI(
    title="Microservicio de Descripción de Imágenes (Línea A)",
    description=(
        "API REST para la generación de alternativas textuales (alt-text) "
        "conformes a WCAG 2.2 mediante una estructura JSON estática."
    ),
    version="1.1.0",
    lifespan=lifespan,
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
    Recibe un archivo de imagen educativa, valida su formato, tamaño e integridad,
    y devuelve su clasificación, elementos clave y descripción accesible en una
    estructura JSON estrictamente estática.

    Args:
        file (UploadFile): Imagen enviada mediante `multipart/form-data`
            (formatos soportados: JPEG, PNG, WEBP; tamaño máximo: 10 MB).

    Raises:
        HTTPException (400): Si el tipo MIME no está permitido, si excede el
            tamaño máximo permitido o si los bytes no corresponden a una imagen íntegra.

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

    contents = b""
    try:
        # 2. Leer hasta MAX_IMAGE_SIZE_BYTES + 1 para evitar saturación de RAM
        contents = await file.read(MAX_IMAGE_SIZE_BYTES + 1)
        if len(contents) > MAX_IMAGE_SIZE_BYTES:
            raise HTTPException(
                status_code=400,
                detail="El archivo excede el tamaño máximo permitido de 10 MB.",
            )

        # 3. Procesar la imagen mediante el motor de visión y construir respuesta estática
        resultado = procesar_imagen_educativa(contents, filename=file.filename or "")
        return resultado
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        # 4. Liberar explícitamente el buffer de bytes y el archivo temporal de FastAPI
        del contents
        await file.close()
