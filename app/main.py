from fastapi import FastAPI
from fastapi.responses import JSONResponse
from app.routers.pdf_router import router as pdf_router

app = FastAPI(title="NeunovaPDF FastAPI")

# Mount PDF router under /api
app.include_router(pdf_router, prefix="/api")

@app.get("/health")
def health():
    return {"status":"ok"}