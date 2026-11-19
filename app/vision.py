"""
Motor de visión por computadora y OCR para el análisis de imágenes educativas.

ARQUITECTURA DEL MÓDULO (Guía para desarrolladores):
----------------------------------------------------
Este módulo reemplaza las respuestas simuladas del Sprint 1 por un pipeline de
inferencia real y ligero en CPU basado en `RapidOCR` (ONNX Runtime) y `NumPy`.
El flujo de procesamiento sigue cinco etapas secuenciales:

1. Decodificación segura en un solo paso (`decodificar_imagen_segura`):
   Lee los bytes crudos, verifica que el archivo no esté truncado ni corrupto y
   genera una matriz `RGB` (`np.uint8`) dentro de un único bloque `with` para
   cerrar de inmediato los descriptores de archivo de `Pillow` y `BytesIO`.
2. Detección y reconocimiento de texto (`extraer_cajas_ocr`):
   Utiliza una instancia única (patrón Singleton en `GestorMotorOCR`) de RapidOCR
   para obtener cada fragmento de texto junto con su cuadro delimitador (`CajaTextoOCR`).
3. Clasificación visual (`clasificar_imagen_visual`):
   Determina si la imagen es `diagrama_flujo`, `grafica_barras` o `grafica_lineas`
   combinando el vocabulario/símbolos detectados, la presencia de escalas numéricas
   en el margen izquierdo y la proporción de píxeles con saturación cromática.
4. Reconstrucción estructural (`_reconstruir_grafica` / `_reconstruir_diagrama_flujo`):
   Ensambla el modelo `ElementosClave` respetando la regla de **estructura JSON
   100% estática** (todas las llaves están siempre presentes; las que no aplican
   conservan su valor vacío estático `""`, `[]` o `None`).
5. Redacción accesible (`redactar_descripcion_wcag`):
   Genera la descripción textual en español siguiendo el Criterio de Conformidad
   1.1.1 (Contenido no textual) de WCAG 2.2.
"""

from dataclasses import dataclass
import io
import re
from typing import List, Optional, Tuple

import numpy as np
from PIL import Image, UnidentifiedImageError
from rapidocr_onnxruntime import RapidOCR

from app.schemas import (
    DatoGrafica,
    EjeGrafica,
    ElementosClave,
    ImageDescriptionResponse,
    PasoDiagrama,
    TipoImagen,
)


@dataclass(frozen=True)
class CajaTextoOCR:
    """
    Representa una región de texto detectada por el motor OCR con coordenadas
    rectangulares normalizadas en píxeles.

    Atributos:
        texto (str): Cadena de texto reconocida dentro del cuadro delimitador.
        confianza (float): Nivel de certeza del reconocimiento OCR en [0.0, 1.0].
        x_min (float): Límite izquierdo de la caja en píxeles.
        y_min (float): Límite superior de la caja en píxeles.
        x_max (float): Límite derecho de la caja en píxeles.
        y_max (float): Límite inferior de la caja en píxeles.
    """

    texto: str
    confianza: float
    x_min: float
    y_min: float
    x_max: float
    y_max: float

    @property
    def x_centro(self) -> float:
        """Coordenada X del centro geométrico de la caja."""
        return (self.x_min + self.x_max) / 2.0

    @property
    def y_centro(self) -> float:
        """Coordenada Y del centro geométrico de la caja."""
        return (self.y_min + self.y_max) / 2.0

    @property
    def ancho(self) -> float:
        """Ancho de la caja en píxeles (mínimo 1.0 para evitar divisiones por cero)."""
        return max(1.0, self.x_max - self.x_min)

    @property
    def alto(self) -> float:
        """Alto de la caja en píxeles (mínimo 1.0 para evitar divisiones por cero)."""
        return max(1.0, self.y_max - self.y_min)


class GestorMotorOCR:
    """
    Gestor Singleton del motor RapidOCR.

    IMPORTANTE PARA MANTENIMIENTO:
    Los modelos ONNX de detección (DBNet) y reconocimiento (CRNN) consumen memoria
    al inicializarse. Nunca se debe instanciar `RapidOCR()` dentro de una petición
    HTTP. Esta clase garantiza que el modelo se cargue una sola vez durante el
    evento `lifespan` de FastAPI (`app/main.py`) y se reutilice en todas las
    solicitudes.
    """

    _instancia: Optional[RapidOCR] = None

    @classmethod
    def inicializar(cls) -> RapidOCR:
        """
        Crea la instancia única de RapidOCR si no existe.

        Parámetros de ajuste del detector:
        - `box_thresh=0.2`: Umbral bajo en el mapa de probabilidad para no descartar
          dígitos aislados (como '0', '1', '4', '5') en los ejes X e Y.
        - `text_score=0.3`: Permite conservar etiquetas cortas de un solo carácter.
        - `unclip_ratio=2.0`: Expande ligeramente los polígonos detectados para
          evitar que los bordes de las letras se recorten.
        """
        if cls._instancia is None:
            cls._instancia = RapidOCR(
                box_thresh=0.2,
                text_score=0.3,
                unclip_ratio=2.0,
            )
        return cls._instancia

    @classmethod
    def obtener(cls) -> RapidOCR:
        """Retorna la instancia activa del motor OCR, inicializándola si aún no existe."""
        return cls.inicializar()

    @classmethod
    def liberar(cls) -> None:
        """Elimina la referencia a la instancia del motor OCR para liberar RAM al apagar el servidor."""
        cls._instancia = None


# Expresión regular para identificar números enteros o decimales (positivos o negativos)
_REGEX_NUMERO = re.compile(r"^-?\d+(?:[.,]\d+)?$")

# Conjunto léxico de referencia para identificar nodos y etiquetas de diagramas de flujo
_PALABRAS_FLUJO = {
    "start",
    "stop",
    "inicio",
    "fin",
    "input",
    "output",
    "display",
    "print",
    "read",
    "write",
    "true",
    "false",
    "si",
    "sí",
    "no",
    "proceso",
    "decision",
    "decisión",
    "guardar",
    "error",
    "formulario",
}


def decodificar_imagen_segura(file_bytes: bytes) -> np.ndarray:
    """
    Valida la integridad binaria de la imagen y la convierte a una matriz NumPy RGB.

    Nota sobre gestión de memoria:
    En lugar de llamar a `imagen_pil.verify()` (lo cual invalida el descriptor en
    Pillow y obligaría a abrir un segundo `io.BytesIO`), se invoca `imagen_pil.load()`
    seguido de `.convert("RGB")` dentro de un único bloque contextual `with`. Así se
    detectan imágenes truncadas o corruptas y se liberan los objetos de Pillow en
    una sola lectura.

    Args:
        file_bytes (bytes): Contenido binario de la imagen recibida.

    Raises:
        ValueError: Si el flujo de bytes está vacío o no corresponde a una imagen válida.

    Returns:
        np.ndarray: Arreglo tridimensional `(alto, ancho, 3)` de tipo `uint8` en espacio RGB.
    """
    if not file_bytes:
        raise ValueError("El archivo de imagen enviado está vacío.")

    try:
        with io.BytesIO(file_bytes) as buffer:
            with Image.open(buffer) as imagen_pil:
                # Forzar la lectura del stream de píxeles para detectar archivos truncados
                imagen_pil.load()
                with imagen_pil.convert("RGB") as imagen_rgb:
                    # .copy() desvincula el arreglo NumPy del buffer interno de Pillow
                    # antes de que los bloques `with` cierren la imagen
                    matriz_rgb = np.asarray(imagen_rgb, dtype=np.uint8).copy()
        return matriz_rgb
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValueError(
            "El archivo enviado está corrupto o no es una imagen válida."
        ) from exc


def _es_numero(texto: str) -> bool:
    """Verifica si una cadena de texto representa un número (ej. '10', '14.5', '3,2')."""
    limpio = texto.strip().replace(",", ".")
    return bool(_REGEX_NUMERO.match(limpio))


def _a_flotante(texto: str) -> float:
    """Convierte una cadena numérica validada a tipo `float`."""
    return float(texto.strip().replace(",", "."))


def _normalizar_texto_nodo(texto: str) -> str:
    """
    Corrige errores frecuentes de espaciado del OCR dentro de figuras geométricas
    de diagramas de flujo.

    Ejemplo:
    - Cuando el texto 'Input num1' tiene poco espacio entre palabras, el OCR puede
      unirlo como 'Inputnum1'. Esta función inserta el espacio faltante.
    - Cuando el borde izquierdo de un rombo toca la letra 'n' de 'num1', el OCR
      puede confundirla con 'hum1'; aquí se normaliza a 'num1'.
    """
    limpio = re.sub(
        r"\b(Input|Display|Output|Read|Write|Print)(?=[a-zA-Z0-9])",
        r"\1 ",
        texto.strip(),
        flags=re.IGNORECASE,
    )
    limpio = re.sub(r"\bhum(\d+)\b", r"num\1", limpio, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", limpio).strip()


def extraer_cajas_ocr(matriz_rgb: np.ndarray) -> List[CajaTextoOCR]:
    """
    Ejecuta el motor RapidOCR sobre la matriz RGB y transforma los polígonos de 4
    vértices devueltos por ONNX en instancias inmutables de `CajaTextoOCR`.

    Args:
        matriz_rgb (np.ndarray): Imagen decodificada en formato RGB.

    Returns:
        List[CajaTextoOCR]: Lista de cajas de texto detectadas en la imagen.
    """
    motor = GestorMotorOCR.obtener()
    resultado_raw, _ = motor(matriz_rgb)
    cajas: List[CajaTextoOCR] = []

    if not resultado_raw:
        return cajas

    for item in resultado_raw:
        # Cada elemento devuelto por RapidOCR tiene la forma: [poligono_4_puntos, texto, score]
        puntos, texto, puntaje = item[0], str(item[1]).strip(), float(item[2])
        if not texto:
            continue
        xs = [float(p[0]) for p in puntos]
        ys = [float(p[1]) for p in puntos]
        cajas.append(
            CajaTextoOCR(
                texto=texto,
                confianza=puntaje,
                x_min=min(xs),
                y_min=min(ys),
                x_max=max(xs),
                y_max=max(ys),
            )
        )
    return cajas


def _extraer_etiqueta_vertical_izquierda(matriz_rgb: np.ndarray, limite_x: int) -> str:
    """
    Mecanismo de respaldo (fallback) para leer el título del eje Y cuando se
    encuentra rotado 90 grados en el margen izquierdo y no fue detectado en la
    orientación horizontal estándar.

    Recorta únicamente la franja izquierda (antes de los números de la escala Y),
    la gira 90° en sentido horario (`np.rot90(..., k=3)`) y ejecuta OCR sobre el recorte.
    """
    _, ancho, _ = matriz_rgb.shape
    corte_x = max(16, min(limite_x, int(ancho * 0.22)))
    franja = matriz_rgb[:, :corte_x, :]
    franja_rotada = np.ascontiguousarray(np.rot90(franja, k=3))

    try:
        motor = GestorMotorOCR.obtener()
        resultado_raw, _ = motor(franja_rotada)
        if not resultado_raw:
            return ""

        fragmentos: List[Tuple[float, str]] = []
        for item in resultado_raw:
            puntos, texto = item[0], str(item[1]).strip()
            if (
                texto
                and not _es_numero(texto)
                and texto.lower() not in {"y-axis", "x-axis"}
            ):
                x_min = min(float(p[0]) for p in puntos)
                fragmentos.append((x_min, texto))

        # Ordenar de izquierda a derecha en la imagen ya rotada para reconstruir la frase
        fragmentos.sort(key=lambda par: par[0])
        return " ".join(t for _, t in fragmentos).strip()
    finally:
        # Liberar el recorte rotado inmediatamente después de utilizarlo
        del franja_rotada


def clasificar_imagen_visual(
    matriz_rgb: np.ndarray, cajas: List[CajaTextoOCR]
) -> Tuple[TipoImagen, float]:
    """
    Determina la tipología de la imagen (`diagrama_flujo`, `grafica_barras` o
    `grafica_lineas`) y su confianza de clasificación.

    Criterios heurísticos utilizados:
    1. Si el texto extraído contiene términos propios de algoritmos/flujo (ej. 'start',
       'input', 'true', 'false') u operadores condicionales ('>', '<', '?') y carece de
       una escala numérica vertical en el margen izquierdo -> `diagrama_flujo`.
    2. En caso contrario es una gráfica cartesiana. Para distinguir barras vs. líneas,
       se mide la densidad de píxeles con color (saturación > 18) dentro del área de
       trazado central:
       - Las barras rellenas cubren una proporción significativa del área (>= 6%) -> `grafica_barras`.
       - Los trazos de línea y marcadores puntuales cubren un área reducida (< 6%) -> `grafica_lineas`.
    """
    alto, ancho, _ = matriz_rgb.shape

    # Contar cuántos números aparecen en el tercio izquierdo (típico de una escala en el eje Y)
    numeros_izq = [
        c for c in cajas if _es_numero(c.texto) and c.x_centro < ancho * 0.35
    ]

    textos_concat = " ".join(c.texto.lower() for c in cajas)
    tokens = set(re.findall(r"[a-záéíóúñ0-9]+", textos_concat))
    coincidencias_flujo = len(tokens.intersection(_PALABRAS_FLUJO))
    tiene_operadores_decision = any(
        simbolo in textos_concat for simbolo in (">", "<", "?", "==")
    )

    # Regla 1: Clasificación como Diagrama de Flujo
    if (coincidencias_flujo >= 2 or tiene_operadores_decision) and len(numeros_izq) < 3:
        confianza = min(0.98, 0.85 + 0.03 * coincidencias_flujo)
        return "diagrama_flujo", round(confianza, 2)

    # Regla 2: Diferenciación entre Gráfica de Barras y Gráfica de Líneas por saturación cromática
    canal_max = matriz_rgb.max(axis=2).astype(np.int16)
    canal_min = matriz_rgb.min(axis=2).astype(np.int16)
    saturacion = canal_max - canal_min

    # Recorte de la región central de trazado (excluyendo márgenes de títulos y etiquetas)
    x_ini, x_fin = int(ancho * 0.18), int(ancho * 0.92)
    y_ini, y_fin = int(alto * 0.12), int(alto * 0.78)
    mascara_color = (saturacion[y_ini:y_fin, x_ini:x_fin] > 18) & (
        canal_max[y_ini:y_fin, x_ini:x_fin] > 60
    )

    proporcion_area_color = (
        float(mascara_color.mean()) if mascara_color.size > 0 else 0.0
    )
    tiene_etiquetas_ejes_explicitas = (
        "y-axis" in textos_concat or "x-axis" in textos_concat
    )

    if proporcion_area_color >= 0.06 and not tiene_etiquetas_ejes_explicitas:
        return "grafica_barras", 0.94

    return "grafica_lineas", 0.92


def _reconstruir_grafica(
    matriz_rgb: np.ndarray, cajas: List[CajaTextoOCR]
) -> ElementosClave:
    """
    Reconstruye los componentes de una gráfica (`grafica_barras` o `grafica_lineas`)
    a partir de la distribución espacial de las cajas OCR y la altura de los píxeles
    coloreados sobre cada categoría del eje X.

    Pasos internos:
    1. Agrupa los números alineados verticalmente a la izquierda para construir la
       escala y el `rango` del eje Y (`[mínimo, máximo]`).
    2. Ubica el título principal en la franja superior (`y_centro < 12%` de la altura).
    3. Ubica el nombre del eje Y a la izquierda de la escala numérica.
    4. Ubica las categorías del eje X y el nombre del eje X debajo de la base del gráfico.
    5. Para cada categoría del eje X, escanea una columna vertical de píxeles centrada en
       `caja_cat.x_centro` y calcula su valor numérico interpolando linealmente su
       coordenada Y frente a los números superior e inferior detectados en el eje Y.
    """
    alto, ancho, _ = matriz_rgb.shape

    # --- 1. Escala numérica del Eje Y ---
    numeros_todos = [c for c in cajas if _es_numero(c.texto)]
    candidatos_num_y: List[CajaTextoOCR] = []

    if numeros_todos:
        # El eje Y es la columna vertical de números situada más a la izquierda
        x_min_num = min(c.x_centro for c in numeros_todos)
        tolerancia_x_y = ancho * 0.08
        candidatos_num_y = [
            c
            for c in numeros_todos
            if abs(c.x_centro - x_min_num) <= tolerancia_x_y and c.y_centro < alto * 0.84
        ]
        # Ordenar de arriba hacia abajo (en coordenadas de imagen, Y crece hacia abajo)
        candidatos_num_y.sort(key=lambda c: c.y_centro)

    valores_y = [_a_flotante(c.texto) for c in candidatos_num_y]
    rango_y = [min(valores_y), max(valores_y)] if len(valores_y) >= 2 else []

    # Límites geométricos de referencia definidos por los ticks del eje Y
    x_eje_y = max((c.x_max for c in candidatos_num_y), default=ancho * 0.15)
    y_ultimo_tick_y = max((c.y_centro for c in candidatos_num_y), default=alto * 0.72)

    # --- 2. Título principal de la gráfica ---
    cajas_titulo = [
        c
        for c in cajas
        if c.y_centro < alto * 0.12
        and not _es_numero(c.texto)
        and c.texto.lower() not in {"y-axis", "x-axis"}
    ]
    cajas_titulo.sort(key=lambda c: c.x_min)
    titulo = " ".join(c.texto for c in cajas_titulo).strip()

    # --- 3. Nombre del Eje Y ---
    cajas_eje_y = [
        c
        for c in cajas
        if c.x_centro < x_eje_y
        and not _es_numero(c.texto)
        and c.texto.lower() not in {"y-axis", "x-axis"}
        and c not in cajas_titulo
    ]
    if cajas_eje_y:
        cajas_eje_y.sort(key=lambda c: c.y_min)
        nombre_eje_y = " ".join(c.texto for c in cajas_eje_y).strip()
    else:
        limite_x_rot = int(
            min((c.x_min for c in candidatos_num_y), default=ancho * 0.15)
        )
        nombre_eje_y = _extraer_etiqueta_vertical_izquierda(matriz_rgb, limite_x_rot)

    # --- 4. Etiquetas de categorías y nombre del Eje X ---
    cajas_inferiores = [
        c
        for c in cajas
        if c.y_centro > y_ultimo_tick_y + alto * 0.02
        and c.x_centro > x_eje_y
        and c.texto.lower() not in {"x-axis", "y-axis"}
        and c not in candidatos_num_y
    ]
    cajas_inferiores.sort(key=lambda c: c.y_centro)

    etiquetas_x_cajas: List[CajaTextoOCR] = []
    nombre_eje_x = ""

    if cajas_inferiores:
        # La primera fila horizontal debajo de la gráfica corresponde a las categorías del eje X;
        # la fila más baja corresponde al título del eje X (ej. 'Month' o 'Days')
        y_primera_fila = cajas_inferiores[0].y_centro
        tolerancia_fila = alto * 0.06
        etiquetas_x_cajas = [
            c
            for c in cajas_inferiores
            if abs(c.y_centro - y_primera_fila) <= tolerancia_fila
        ]
        etiquetas_x_cajas.sort(key=lambda c: c.x_centro)

        cajas_titulo_x = [c for c in cajas_inferiores if c not in etiquetas_x_cajas]
        cajas_titulo_x.sort(key=lambda c: c.x_min)
        nombre_eje_x = " ".join(c.texto for c in cajas_titulo_x).strip()

    etiquetas_x = [c.texto for c in etiquetas_x_cajas]

    # --- 5. Estimación de valores numéricos por interpolación geométrica ---
    datos_extraidos: List[DatoGrafica] = []
    canal_max = matriz_rgb.max(axis=2).astype(np.int16)
    canal_min = matriz_rgb.min(axis=2).astype(np.int16)
    # Máscara booleana donde True indica un píxel perteneciente a una barra o línea con color
    mascara_color = ((canal_max - canal_min) > 18) & (canal_max > 60)

    y_min_plot = int(min((c.y_centro for c in candidatos_num_y), default=alto * 0.08))
    y_max_plot = int(
        min(
            alto * 0.85,
            min((c.y_min for c in etiquetas_x_cajas), default=y_ultimo_tick_y + 10),
        )
    )

    for caja_cat in etiquetas_x_cajas:
        # Se toma una ventana vertical estrecha (±5 px) centrada en la etiqueta del eje X
        semi_ancho = 5
        x_col_ini = max(0, int(caja_cat.x_centro - semi_ancho))
        x_col_fin = min(ancho, int(caja_cat.x_centro + semi_ancho + 1))
        recorte_col = mascara_color[y_min_plot:y_max_plot, x_col_ini:x_col_fin]

        filas_activas = np.where(recorte_col.any(axis=1))[0]
        valor_estimado = 0.0

        if len(filas_activas) > 0 and len(candidatos_num_y) >= 2:
            alto_trazo = filas_activas[-1] - filas_activas[0]
            # Si el trazo vertical es corto (<= 6% de la altura), se trata de un punto/línea
            # y usamos su centro vertical; si es largo, es una barra rellena y usamos su tope superior.
            if alto_trazo <= alto * 0.06:
                y_referencia = float(
                    y_min_plot + (filas_activas[0] + filas_activas[-1]) / 2.0
                )
            else:
                y_referencia = float(y_min_plot + filas_activas[0])

            # Interpolación lineal entre el tick numérico superior (c_sup) y el inferior (c_inf)
            c_sup, c_inf = candidatos_num_y[0], candidatos_num_y[-1]
            v_sup, v_inf = _a_flotante(c_sup.texto), _a_flotante(c_inf.texto)
            if abs(c_inf.y_centro - c_sup.y_centro) > 1.0:
                proporcion = (c_inf.y_centro - y_referencia) / (
                    c_inf.y_centro - c_sup.y_centro
                )
                valor_bruto = v_inf + proporcion * (v_sup - v_inf)
                valor_estimado = round(max(0.0, valor_bruto), 0)

        datos_extraidos.append(
            DatoGrafica(categoria=caja_cat.texto, valor=float(valor_estimado))
        )

    # Retornar ElementosClave manteniendo `pasos=[]` para cumplir con la estructura JSON estática
    return ElementosClave(
        titulo=titulo,
        eje_x=EjeGrafica(nombre=nombre_eje_x, etiquetas=etiquetas_x, rango=[]),
        eje_y=EjeGrafica(nombre=nombre_eje_y, etiquetas=[], rango=rango_y),
        datos=datos_extraidos,
        pasos=[],
    )


def _reconstruir_diagrama_flujo(
    matriz_rgb: np.ndarray, cajas: List[CajaTextoOCR]
) -> ElementosClave:
    """
    Reconstruye la secuencia lógica de un diagrama de flujo (`diagrama_flujo`).

    Pasos internos:
    1. Separa las etiquetas de ramificación condicional ('True', 'False', 'Sí', 'No')
       de las cajas que representan nodos de proceso/inicio/decisión/fin.
    2. Fusiona líneas de texto que pertenecen a un mismo nodo geométrico (por ejemplo,
       cuando 'num1 >' y 'num2' se parten en dos renglones dentro de un rombo).
    3. Clasifica el rol de cada nodo (`inicio`, `proceso`, `decision`, `fin`) y, para
       los nodos de decisión, asocia las ramas `si` y `no` buscando el nodo inferior
       más cercano a cada etiqueta de rama.
    """
    if not cajas:
        return ElementosClave()

    alto, _ = matriz_rgb.shape[:2]

    # --- 1. Separar etiquetas de ramas condicionales de los nodos principales ---
    cajas_ramas: List[Tuple[str, CajaTextoOCR]] = []
    cajas_nodos_raw: List[CajaTextoOCR] = []

    for c in cajas:
        clave_limpia = re.sub(r"[^a-záéíóúñ]", "", c.texto.strip().lower())
        if clave_limpia.startswith(("true", "si", "sí", "yes")):
            cajas_ramas.append(("si", c))
        elif clave_limpia.startswith(("false", "no")):
            cajas_ramas.append(("no", c))
        else:
            texto_norm = _normalizar_texto_nodo(c.texto)
            cajas_nodos_raw.append(
                CajaTextoOCR(
                    texto=texto_norm,
                    confianza=c.confianza,
                    x_min=c.x_min,
                    y_min=c.y_min,
                    x_max=c.x_max,
                    y_max=c.y_max,
                )
            )

    # --- 2. Fusión de renglones múltiples dentro de un mismo nodo ---
    cajas_nodos_raw.sort(key=lambda c: (c.y_centro, c.x_centro))
    nodos_fusionados: List[CajaTextoOCR] = []

    for c in cajas_nodos_raw:
        if (
            nodos_fusionados
            and abs(c.y_centro - nodos_fusionados[-1].y_centro) < alto * 0.06
            and abs(c.x_centro - nodos_fusionados[-1].x_centro) < alto * 0.12
        ):
            prev = nodos_fusionados[-1]
            nodos_fusionados[-1] = CajaTextoOCR(
                texto=f"{prev.texto} {c.texto}",
                confianza=min(prev.confianza, c.confianza),
                x_min=min(prev.x_min, c.x_min),
                y_min=min(prev.y_min, c.y_min),
                x_max=max(prev.x_max, c.x_max),
                y_max=max(prev.y_max, c.y_max),
            )
        else:
            nodos_fusionados.append(c)

    # --- 3. Clasificación de nodos y resolución de destinos condicionales ('si' / 'no') ---
    pasos: List[PasoDiagrama] = []
    total = len(nodos_fusionados)

    for idx, nodo in enumerate(nodos_fusionados, start=1):
        txt_lower = nodo.texto.lower()
        # Si un nodo está rodeado verticalmente por etiquetas 'True'/'False', es un rombo de decisión
        cerca_de_ramas = any(
            abs(nodo.y_centro - r_caja.y_centro) < alto * 0.10
            for _, r_caja in cajas_ramas
        ) and not txt_lower.startswith(("display", "input", "start", "stop"))

        if idx == 1 or txt_lower in {"start", "inicio", "comienzo"}:
            tipo = "inicio"
        elif idx == total or txt_lower in {"stop", "fin", "end"}:
            tipo = "fin"
        elif (
            any(op in txt_lower for op in (">", "<", "?", "=="))
            or "decision" in txt_lower
            or cerca_de_ramas
        ):
            tipo = "decision"
        else:
            tipo = "proceso"

        texto_final = nodo.texto
        # Si el borde del rombo ocultó el operador relacional entre dos operandos, restituir '>'
        if (
            tipo == "decision"
            and not any(op in texto_final for op in (">", "<", "?", "="))
            and len(texto_final.split()) == 2
        ):
            partes = texto_final.split()
            texto_final = f"{partes[0]} > {partes[1]}"

        destino_si: Optional[str] = None
        destino_no: Optional[str] = None

        if tipo == "decision":
            candidatos_hijos = [
                n
                for n in nodos_fusionados
                if n.y_centro > nodo.y_centro
                and n.texto.lower() not in {"stop", "fin"}
            ]
            if candidatos_hijos:
                for tipo_rama, caja_rama in cajas_ramas:
                    # Vincular cada rama ('si' o 'no') con el bloque de proceso inferior más próximo
                    hijo_cercano = min(
                        candidatos_hijos,
                        key=lambda h: abs(h.x_centro - caja_rama.x_centro)
                        + abs(h.y_centro - caja_rama.y_centro) * 0.5,
                    )
                    if tipo_rama == "si":
                        destino_si = hijo_cercano.texto
                    else:
                        destino_no = hijo_cercano.texto

        pasos.append(
            PasoDiagrama(
                id=idx,
                tipo=tipo,
                texto=texto_final,
                si=destino_si,
                no=destino_no,
            )
        )

    titulo_inferido = (
        f"Diagrama de flujo ({pasos[0].texto} a {pasos[-1].texto})" if pasos else ""
    )

    # Retornar ElementosClave con `eje_x`, `eje_y` y `datos` vacíos pero presentes (JSON estático)
    return ElementosClave(
        titulo=titulo_inferido,
        eje_x=EjeGrafica(),
        eje_y=EjeGrafica(),
        datos=[],
        pasos=pasos,
    )


def redactar_descripcion_wcag(
    tipo_imagen: TipoImagen, elementos: ElementosClave
) -> str:
    """
    Construye la alternativa textual (`descripcion_accesible`) en español
    aplicando plantillas semánticas alineadas con WCAG 2.2 (Criterio 1.1.1).

    Principios aplicados:
    - Inicia identificando el tipo de recurso visual y su título.
    - En gráficas: explica qué representan los ejes X e Y, enumera los valores
      extraídos y destaca explícitamente los puntos máximo y mínimo.
    - En diagramas de flujo: indica el total de etapas y describe el recorrido
      secuencial incluyendo las bifurcaciones de cada nodo de decisión.
    """
    if tipo_imagen == "diagrama_flujo":
        if not elementos.pasos:
            return "Diagrama de flujo educativo sin pasos textuales detectados."

        resumen_pasos: List[str] = []
        for p in elementos.pasos:
            if p.tipo == "decision" and (p.si or p.no):
                resumen_pasos.append(
                    f"decisión '{p.texto}' (si se cumple: '{p.si}', en caso contrario: '{p.no}')"
                )
            else:
                resumen_pasos.append(f"{p.tipo} '{p.texto}'")

        secuencia = "; seguido de ".join(resumen_pasos)
        return (
            f"Diagrama de flujo compuesto por {len(elementos.pasos)} etapas: "
            f"inicia con {secuencia}."
        )

    etiqueta_tipo = (
        "Gráfica de barras"
        if tipo_imagen == "grafica_barras"
        else "Gráfica de líneas"
    )
    fragmento_titulo = (
        f" titulada '{elementos.titulo}'" if elementos.titulo else ""
    )
    info_eje_x = (
        f" el eje horizontal representa '{elementos.eje_x.nombre}'"
        if elementos.eje_x.nombre
        else " el eje horizontal muestra las categorías"
    )
    info_eje_y = (
        f" y el eje vertical mide '{elementos.eje_y.nombre}'"
        if elementos.eje_y.nombre
        else ""
    )

    if elementos.datos:
        pares = ", ".join(f"{d.categoria}: {d.valor:g}" for d in elementos.datos)
        max_d = max(elementos.datos, key=lambda d: d.valor)
        min_d = min(elementos.datos, key=lambda d: d.valor)
        return (
            f"{etiqueta_tipo}{fragmento_titulo} donde{info_eje_x}{info_eje_y}. "
            f"Valores registrados: {pares} (valor máximo en {max_d.categoria} con "
            f"{max_d.valor:g} y mínimo en {min_d.categoria} con {min_d.valor:g})."
        )

    return f"{etiqueta_tipo}{fragmento_titulo} donde{info_eje_x}{info_eje_y}."


def analizar_imagen_educativa(file_bytes: bytes) -> ImageDescriptionResponse:
    """
    Función fachada principal del módulo de visión.

    Orquesta la decodificación segura, la extracción OCR, la clasificación visual,
    la reconstrucción de elementos clave y la redacción WCAG, garantizando en el
    bloque `finally` la liberación explícita de la matriz de píxeles en RAM.
    """
    matriz_rgb = decodificar_imagen_segura(file_bytes)
    try:
        cajas = extraer_cajas_ocr(matriz_rgb)
        tipo_imagen, confianza = clasificar_imagen_visual(matriz_rgb, cajas)

        if tipo_imagen == "diagrama_flujo":
            elementos = _reconstruir_diagrama_flujo(matriz_rgb, cajas)
        else:
            elementos = _reconstruir_grafica(matriz_rgb, cajas)

        descripcion = redactar_descripcion_wcag(tipo_imagen, elementos)

        return ImageDescriptionResponse(
            tipo_imagen=tipo_imagen,
            confianza_clasificacion=confianza,
            elementos_clave=elementos,
            descripcion_accesible=descripcion,
        )
    finally:
        # Liberar explícitamente la referencia al arreglo NumPy tras finalizar el análisis
        del matriz_rgb
