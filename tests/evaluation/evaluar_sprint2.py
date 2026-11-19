"""
Script de evaluación automatizada para el Sprint 2 del Microservicio (Línea A).

GUÍA PARA DESARROLLADORES:
--------------------------
Este módulo permite verificar de forma reproducible que cualquier cambio en el
motor de visión (`app/vision.py`) o en los esquemas (`app/schemas.py`) mantenga:
1. La invarianza del contrato JSON estático (`ImageDescriptionResponse`).
2. La exactitud en la clasificación tipológica (`grafica_barras`, `grafica_lineas`,
   `diagrama_flujo`).
3. La precisión en la extracción OCR de títulos, nombres de ejes, series de datos
   numéricos y secuencia/ramificaciones de diagramas de flujo.
4. La calidad semántica de la descripción accesible (`descripcion_accesible`)
   conforme a WCAG 2.2 (Criterio 1.1.1).

Cómo agregar un nuevo caso de prueba:
- Coloca la nueva imagen en `tests/images/`.
- Crea un archivo `*_gt.json` en `tests/evaluation/ground_truth/` con las llaves
  `"imagen_relativa"` y `"ground_truth"`.
- Ejecuta desde la raíz del proyecto:
      python -m tests.evaluation.evaluar_sprint2
"""

from difflib import SequenceMatcher
import json
from pathlib import Path
import re
from typing import Dict, List

from app.schemas import ElementosClave, ImageDescriptionResponse
from app.services import procesar_imagen_educativa
from app.vision import GestorMotorOCR


# Rutas base resueltas dinámicamente respecto a la ubicación de este archivo
RAIZ_PROYECTO = Path(__file__).resolve().parents[2]
DIRECTORIO_GT = Path(__file__).resolve().parent / "ground_truth"


def similitud_texto(texto_a: str, texto_b: str) -> float:
    """
    Calcula la razón de similitud [0.0, 1.0] entre dos cadenas ignorando
    diferencias de mayúsculas/minúsculas y espacios extremos.
    """
    a = texto_a.strip().lower()
    b = texto_b.strip().lower()
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return round(SequenceMatcher(None, a, b).ratio(), 4)


def cobertura_tokens_clave(prediccion: str, referencia: str) -> float:
    """
    Mide qué proporción de las palabras significativas (sustantivos, cifras,
    categorías y verbos clave) del texto de referencia (Ground Truth) aparecen
    en la descripción accesible generada por el microservicio.
    """
    # Lista de conectores y preposiciones que no aportan peso semántico a la métrica
    palabras_vacias = {
        "de",
        "la",
        "el",
        "en",
        "y",
        "con",
        "por",
        "para",
        "una",
        "un",
        "los",
        "las",
        "del",
        "se",
        "que",
        "donde",
    }
    tokens_ref = {
        t
        for t in re.findall(r"[a-záéíóúñ0-9]+", referencia.lower())
        if t not in palabras_vacias
    }
    if not tokens_ref:
        return 1.0
    tokens_pred = set(re.findall(r"[a-záéíóúñ0-9]+", prediccion.lower()))
    coincidencias = len(tokens_ref.intersection(tokens_pred))
    return round(coincidencias / len(tokens_ref), 4)


def evaluar_extraccion_elementos(
    pred: ElementosClave, ref: ElementosClave, tipo_esperado: str
) -> float:
    """
    Evalúa la exactitud estructural de `ElementosClave` en el rango [0.0, 1.0].

    ponderación según el tipo de imagen:
    - Si es `diagrama_flujo`: 20% título + 80% exactitud de los pasos (evaluando
      en cada paso: rol del nodo, texto interno y destinos condicionales `si`/`no`).
    - Si es `grafica_barras` o `grafica_lineas`: 20% título + 15% nombre del eje X
      + 15% nombre del eje Y + 50% exactitud de los pares categoría-valor en `datos`.
    """
    sim_titulo = similitud_texto(pred.titulo, ref.titulo)

    if tipo_esperado == "diagrama_flujo":
        if not ref.pasos:
            return sim_titulo

        total_pasos = max(len(ref.pasos), len(pred.pasos))
        puntajes_pasos: List[float] = []
        for p_pred, p_ref in zip(pred.pasos, ref.pasos):
            acierto_tipo = 1.0 if p_pred.tipo == p_ref.tipo else 0.0
            sim_txt = similitud_texto(p_pred.texto, p_ref.texto)
            sim_si = similitud_texto(p_pred.si or "", p_ref.si or "")
            sim_no = similitud_texto(p_pred.no or "", p_ref.no or "")
            # Ponderación por paso: 25% rol + 45% texto del nodo + 15% rama 'si' + 15% rama 'no'
            puntajes_pasos.append(
                0.25 * acierto_tipo + 0.45 * sim_txt + 0.15 * sim_si + 0.15 * sim_no
            )

        exactitud_pasos = sum(puntajes_pasos) / total_pasos
        return round(0.20 * sim_titulo + 0.80 * exactitud_pasos, 4)

    # Evaluación para gráficas cartesianas (barras o líneas)
    sim_eje_x = similitud_texto(pred.eje_x.nombre, ref.eje_x.nombre)
    sim_eje_y = similitud_texto(pred.eje_y.nombre, ref.eje_y.nombre)

    if not ref.datos:
        return round((sim_titulo + sim_eje_x + sim_eje_y) / 3.0, 4)

    mapa_ref = {d.categoria.lower(): d.valor for d in ref.datos}
    mapa_pred = {d.categoria.lower(): d.valor for d in pred.datos}

    aciertos_datos: List[float] = []
    for cat_lower, val_esp in mapa_ref.items():
        if cat_lower not in mapa_pred:
            aciertos_datos.append(0.0)
            continue
        val_obt = mapa_pred[cat_lower]
        # Se otorga 1.0 si el valor coincide exactamente, o 0.85 si está dentro de una
        # tolerancia de interpolación visual del 10% (o ±1.0 unidad en escalas pequeñas)
        error_abs = abs(val_obt - val_esp)
        if error_abs == 0.0:
            aciertos_datos.append(1.0)
        elif error_abs <= max(1.0, abs(val_esp) * 0.10):
            aciertos_datos.append(0.85)
        else:
            aciertos_datos.append(max(0.0, 1.0 - error_abs / max(1.0, abs(val_esp))))

    exactitud_datos = sum(aciertos_datos) / max(len(mapa_ref), len(mapa_pred))
    return round(
        0.20 * sim_titulo
        + 0.15 * sim_eje_x
        + 0.15 * sim_eje_y
        + 0.50 * exactitud_datos,
        4,
    )


def evaluar_caso(ruta_gt: Path) -> Dict[str, object]:
    """
    Carga un archivo Ground Truth (`*_gt.json`), ejecuta el pipeline real de
    visión sobre la imagen asociada y calcula las métricas de desempeño.
    """
    with ruta_gt.open("r", encoding="utf-8") as archivo_gt:
        contenido_gt = json.load(archivo_gt)

    ruta_imagen = RAIZ_PROYECTO / str(contenido_gt["imagen_relativa"])
    esperado = ImageDescriptionResponse(**contenido_gt["ground_truth"])

    with ruta_imagen.open("rb") as archivo_img:
        bytes_imagen = archivo_img.read()

    try:
        obtenido = procesar_imagen_educativa(bytes_imagen, filename=ruta_imagen.name)
    finally:
        # Liberar el buffer binario de la imagen tras la evaluación del caso
        del bytes_imagen

    # 1. Verificar invarianza del contrato JSON estático en todos los niveles
    dict_esp = esperado.model_dump()
    dict_obt = obtenido.model_dump()
    contrato_estatico_valido = (
        tuple(dict_esp.keys()) == tuple(dict_obt.keys())
        and tuple(dict_esp["elementos_clave"].keys())
        == tuple(dict_obt["elementos_clave"].keys())
        and tuple(dict_esp["elementos_clave"]["eje_x"].keys())
        == tuple(dict_obt["elementos_clave"]["eje_x"].keys())
    )

    # 2. Calcular métricas cuantitativas individuales y puntaje global ponderado
    exactitud_clasificacion = (
        1.0 if obtenido.tipo_imagen == esperado.tipo_imagen else 0.0
    )
    exactitud_elementos = evaluar_extraccion_elementos(
        obtenido.elementos_clave,
        esperado.elementos_clave,
        esperado.tipo_imagen,
    )
    sim_textual = similitud_texto(
        obtenido.descripcion_accesible, esperado.descripcion_accesible
    )
    cobertura_wcag = cobertura_tokens_clave(
        obtenido.descripcion_accesible, esperado.descripcion_accesible
    )
    calidad_textual_wcag = round(0.50 * sim_textual + 0.50 * cobertura_wcag, 4)

    # Ponderación global: 25% clasificación + 45% extracción OCR + 30% calidad WCAG
    puntaje_global = round(
        0.25 * exactitud_clasificacion
        + 0.45 * exactitud_elementos
        + 0.30 * calidad_textual_wcag,
        4,
    )

    return {
        "caso": ruta_gt.stem,
        "imagen": ruta_imagen.name,
        "contrato_estatico_ok": contrato_estatico_valido,
        "exactitud_clasificacion": exactitud_clasificacion,
        "exactitud_elementos": exactitud_elementos,
        "calidad_textual_wcag": calidad_textual_wcag,
        "puntaje_global": puntaje_global,
    }


def ejecutar_suite_evaluacion() -> List[Dict[str, object]]:
    """
    Inicializa el motor OCR una única vez (Singleton), evalúa todos los casos
    de prueba en `tests/evaluation/ground_truth/` y libera la memoria al terminar.
    """
    GestorMotorOCR.inicializar()
    try:
        archivos_gt = sorted(DIRECTORIO_GT.glob("*_gt.json"))
        resultados = [evaluar_caso(ruta) for ruta in archivos_gt]
        return resultados
    finally:
        GestorMotorOCR.liberar()


if __name__ == "__main__":
    reporte = ejecutar_suite_evaluacion()
    print("=== REPORTE DE EVALUACIÓN SPRINT 2 (OCR + WCAG 2.2) ===")
    for item in reporte:
        print(json.dumps(item, indent=2, ensure_ascii=False))

    promedio = (
        round(sum(float(r["puntaje_global"]) for r in reporte) / len(reporte), 4)
        if reporte
        else 0.0
    )
    print(f"\nPuntaje Global Promedio: {promedio * 100:.2f}%")
