from fastapi import FastAPI, UploadFile, File, HTTPException
from app.schemas import ImageDescriptionResponse
from app.services import procesar_imagen_educativa

app = FastAPI(
    title="Microservicio de Descripción de Imágenes (Línea A)",
    description="API REST para la generación de alternativas textuales (alt-text) conformes a WCAG.",
    version="1.0.0"
)

@app.get("/")
def read_root():
    """Endpoint verificación de que el servicio esté funcionando."""
    return {"mensaje": "Servidor de la Línea A funcionando correctamente"}

@app.post("/api/v1/describe", response_model=ImageDescriptionResponse)
async def describe_image(file: UploadFile = File(...)):
    """
    Endpoint principal del Sprint 1: Recibe una imagen y devuelve su 
    clasificación y elementos estructurados en formato JSON.
    """
    # 1. Validar que el archivo sea una imagen
    if file.content_type not in ["image/jpeg", "image/png", "image/webp"]:
        raise HTTPException(
            status_code=400, 
            detail="El archivo enviado no es una imagen válida (debe ser JPEG, PNG o WEBP)."
        )
    
    # 2. Leer los bytes de la imagen
    contents = await file.read()
    
    # 3. Procesar la imagen mediante el servicio enviando el nombre de archivo
    resultado = procesar_imagen_educativa(contents, filename=file.filename)
    
    # 4. FastAPI valida automáticamente con ImageDescriptionResponse y responde en JSON
    return resultado