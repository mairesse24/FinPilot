"""Public demo context; never exposes provider credentials."""
from fastapi import APIRouter, Depends, Request
from app.calc.models import FinancialProfile
from app.deps import get_profile

router = APIRouter(prefix="/api", tags=["context"])


@router.get("/context")
def context(request: Request, p: FinancialProfile = Depends(get_profile)):
    repo = request.app.state.repo
    return {"user": {"id": p.user.id, "name": p.user.name}, "as_of": p.as_of,
            "data_source": getattr(repo, "source", "configured repository" if request.app.state.settings.database_url else "generated demo"),
            "warnings": getattr(repo, "warnings", []),
            "loaded_at": getattr(repo, "loaded_at", None),
            "synthetic": True}
