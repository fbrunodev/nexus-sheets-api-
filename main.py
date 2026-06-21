from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.auth import router as auth_router
from app.api.v1.sheets import router as sheets_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.operators import router as operators_router
from app.api.v1.admin import router as admin_router
from app.api.v1 import platforms
from app.api.v1.costs import router as costs_router

app = FastAPI(
    title = settings.APP_NAME,
    version = settings.APP_VERSION,
    docs_url = "/docs",
    redoc_url = "/redoc"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://nexus-sheets-frontend.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registra os rotadores da API v1
app.include_router(auth_router, prefix="/api/v1")
app.include_router(sheets_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(operators_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(platforms.router, prefix="/api/v1")
app.include_router(costs_router, prefix="/api/v1")
@app.get("/health")
def health_check():
    """
    Endpoint de verificação de saúde do servidor
    Usado para confirmar que a API está respondendo
    """
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION
    }