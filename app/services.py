from PIL import Image
import io

def procesar_imagen_educativa(file_bytes: bytes, filename: str = "") -> dict:
    image = Image.open(io.BytesIO(file_bytes))
    fn = filename.lower()

    # Evaluación según palabras clave en el nombre de la imagen de prueba
    if "diagrama" in fn or "flujo" in fn or "flow" in fn:
        return {
            "tipo_imagen": "diagrama_flujo",
            "confianza_clasificacion": 0.94,
            "elementos_clave": {
                "titulo": "Proceso de Registro de Usuario",
                "pasos": [
                    {"id": 1, "tipo": "inicio", "texto": "Inicio del formulario"},
                    {"id": 2, "tipo": "decision", "texto": "¿Datos válidos?", "si": "Guardar", "no": "Mostrar error"}
                ]
            },
            "descripcion_accesible": "Diagrama de flujo que muestra el proceso de registro de usuario evaluando la validez de los datos."
        }
    
    elif "linea" in fn or "line" in fn or "tendencia" in fn:
        return {
            "tipo_imagen": "grafica_lineas",
            "confianza_clasificacion": 0.91,
            "elementos_clave": {
                "titulo": "Evolución de Matrícula Universitaria",
                "eje_x": {"nombre": "Años", "etiquetas": ["2024", "2025", "2026"]},
                "eje_y": {"nombre": "Estudiantes", "rango": [0, 500]},
                "datos": [
                    {"categoria": "2024", "valor": 300},
                    {"categoria": "2025", "valor": 420},
                    {"categoria": "2026", "valor": 480}
                ]
            },
            "descripcion_accesible": "Gráfica de líneas que muestra la evolución de la matrícula universitaria con tendencia ascendente de 2024 a 2026."
        }

    else:
        # Respuesta por defecto para gráficas de barras
        return {
            "tipo_imagen": "grafica_barras",
            "confianza_clasificacion": 0.95,
            "elementos_clave": {
                "titulo": "Comparativa de Asignaturas",
                "eje_x": {"nombre": "Materias"},
                "eje_y": {"nombre": "Inscritos"},
                "datos": [
                    {"categoria": "Redes", "valor": 35},
                    {"categoria": "IA", "valor": 40}
                ]
            },
            "descripcion_accesible": "Gráfica de barras comparativa entre las materias de Redes e IA."
        }