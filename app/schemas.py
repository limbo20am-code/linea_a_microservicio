from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class ElementosClave(BaseModel):
    titulo: Optional[str] = None
    eje_x: Optional[Dict[str, Any]] = None
    eje_y: Optional[Dict[str, Any]] = None
    datos: Optional[List[Dict[str, Any]]] = None
    pasos: Optional[List[Dict[str, Any]]] = None

class ImageDescriptionResponse(BaseModel):
    tipo_imagen: str
    confianza_clasificacion: float
    elementos_clave: ElementosClave
    descripcion_accesible: str