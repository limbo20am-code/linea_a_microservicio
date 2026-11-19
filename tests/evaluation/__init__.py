"""
Paquete de evaluación cuantitativa y validación de contrato para el Sprint 2.

Permite comparar las salidas reales del motor de visión (`app.vision`) frente
a los archivos de referencia (Ground Truth) verificando:
1. Cumplimiento estricto del contrato JSON estático (`ImageDescriptionResponse`).
2. Exactitud en la clasificación tipológica y extracción de datos/pasos OCR.
3. Calidad semántica de la descripción accesible conforme a WCAG 2.2.
"""
