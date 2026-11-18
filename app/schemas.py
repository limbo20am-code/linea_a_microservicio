"""
Esquemas de datos y contratos JSON del Microservicio (Línea A).

Define una estructura JSON estrictamente estática e invariante para evitar la
asignación dinámica de diccionarios arbitrarios (Dict[str, Any]) en memoria.
Todas las respuestas del servicio conservan exactamente las mismas llaves y
tipos de datos sin importar la clasificación de la imagen, optimizando el uso
de memoria tanto en la serialización del orquestador como en la decodificación
guiada (Structured Outputs) de modelos de visión-lenguaje (VLM).
"""

from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


# Tipos de imagen soportados de forma estática por el microservicio
TipoImagen = Literal["grafica_barras", "grafica_lineas", "diagrama_flujo"]


class EjeGrafica(BaseModel):
    """
    Estructura estática para representar la información de un eje cartesiano (X o Y).

    Siempre mantiene las mismas tres llaves (`nombre`, `etiquetas`, `rango`).
    Cuando la imagen no utiliza un eje (p. ej. un diagrama de flujo), los campos
    permanecen con sus valores vacíos predeterminados en lugar de omitir el nodo.
    """

    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(
        default="",
        description="Título o etiqueta descriptiva del eje (cadena vacía si no aplica).",
    )
    etiquetas: List[str] = Field(
        default_factory=list,
        description="Lista de categorías o etiquetas discretas del eje.",
    )
    rango: List[float] = Field(
        default_factory=list,
        description="Límites numéricos [mínimo, máximo] del eje cuando representa una escala continua.",
    )


class DatoGrafica(BaseModel):
    """
    Estructura estática para un punto o barra de datos dentro de una gráfica.
    """

    model_config = ConfigDict(extra="forbid")

    categoria: str = Field(
        ...,
        description="Nombre de la categoría, serie o periodo en el eje correspondiente.",
    )
    valor: float = Field(
        ...,
        description="Valor numérico asociado a la categoría.",
    )


class PasoDiagrama(BaseModel):
    """
    Estructura estática para representar un nodo o etapa dentro de un diagrama de flujo.

    Incluye siempre las llaves de ramificación (`si` y `no`) con valor `None`
    por defecto para evitar que los nodos de decisión tengan una estructura de
    memoria distinta a los nodos secuenciales.
    """

    model_config = ConfigDict(extra="forbid")

    id: int = Field(
        ...,
        description="Identificador secuencial del paso dentro del diagrama.",
    )
    tipo: str = Field(
        ...,
        description="Rol del nodo en el diagrama (ej. 'inicio', 'proceso', 'decision', 'fin').",
    )
    texto: str = Field(
        ...,
        description="Contenido textual o instrucción dentro del nodo.",
    )
    si: Optional[str] = Field(
        default=None,
        description="Acción o nodo destino cuando la condición es afirmativa (solo en nodos de decisión).",
    )
    no: Optional[str] = Field(
        default=None,
        description="Acción o nodo destino cuando la condición es negativa (solo en nodos de decisión).",
    )


class ElementosClave(BaseModel):
    """
    Contenedor estático de los elementos extraídos de la imagen educativa.

    A diferencia de un esquema modular/polimórfico, todos los campos (`titulo`,
    `eje_x`, `eje_y`, `datos`, `pasos`) se encuentran siempre presentes y
    pre-estructurados con el mismo formato JSON.
    """

    model_config = ConfigDict(extra="forbid")

    titulo: str = Field(
        default="",
        description="Título principal identificado en la imagen educativa.",
    )
    eje_x: EjeGrafica = Field(
        default_factory=EjeGrafica,
        description="Información estructurada del eje horizontal (estática).",
    )
    eje_y: EjeGrafica = Field(
        default_factory=EjeGrafica,
        description="Información estructurada del eje vertical (estática).",
    )
    datos: List[DatoGrafica] = Field(
        default_factory=list,
        description="Lista de pares categoría-valor para gráficas de barras o líneas.",
    )
    pasos: List[PasoDiagrama] = Field(
        default_factory=list,
        description="Lista de pasos secuenciales o condicionales para diagramas de flujo.",
    )


class ImageDescriptionResponse(BaseModel):
    """
    Contrato principal de salida para el endpoint `POST /api/v1/describe`.

    Garantiza una estructura JSON fija para su consumo por el Orquestador de IA.
    """

    model_config = ConfigDict(extra="forbid")

    tipo_imagen: TipoImagen = Field(
        ...,
        description="Clasificación tipológica de la imagen educativa.",
    )
    confianza_clasificacion: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Nivel de confianza del clasificador en el rango [0.0, 1.0].",
    )
    elementos_clave: ElementosClave = Field(
        ...,
        description="Estructura estática con los componentes extraídos de la imagen.",
    )
    descripcion_accesible: str = Field(
        ...,
        description="Alternativa textual (alt-text) generada conforme a los criterios WCAG.",
    )
