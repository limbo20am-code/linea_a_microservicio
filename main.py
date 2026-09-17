from fastapi import FastAPI

app = FastAPI(
    title="Microservicio de Descripción de Imágenes",
    description="API para generar alt-text",
    version="1.0.0"
)

@app.get("/")
def read_root():
    return {"mensaje": "Servidor de la Línea A funcionando correctamente"}