from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings, get_settings
from app.db.factory import build_repo
from app.db.repository import Repository
from app.routes import include_all


def create_app(repo: Repository | None = None, settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(title="FinPilot API")
    app.state.settings = settings
    app.state.repo = repo or build_repo(settings)
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins,
                       allow_methods=["*"], allow_headers=["*"])

    @app.middleware('http')
    async def financial_cache_policy(request,call_next):
        response=await call_next(request)
        if request.url.path.startswith('/api/'):
            response.headers['Cache-Control']='no-store'
        return response

    @app.get("/healthz")
    def healthz():
        try:
            db = bool(app.state.repo.ping())
        except Exception:
            db = False
        return {"status": "ok", "database": db}

    include_all(app)
    return app


app = create_app()
