from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel

from app.models.schemas import SendMailRequest
from app.services import mail_service, session_store


class TestMailRequest(BaseModel):
    to: str

router = APIRouter(prefix="/api", tags=["mail"])


def _get_formula_or_404(session_id: str) -> dict:
    if session_store.get_session_meta(session_id) is None:
        raise HTTPException(status_code=404, detail="Session not found")
    formula = session_store.get_selected_formula(session_id)
    if formula is None:
        raise HTTPException(status_code=404, detail="No formula selected for this session")
    return formula


@router.get("/session/{session_id}/mail", response_class=HTMLResponse)
async def get_mail(session_id: str):
    """Return the mail HTML for in-browser display."""
    formula = _get_formula_or_404(session_id)
    html = mail_service.generate_mail_html(session_id, formula)
    return HTMLResponse(content=html)


@router.get("/session/{session_id}/mail/download")
async def download_mail(session_id: str):
    """Return the mail as a downloadable PDF."""
    formula = _get_formula_or_404(session_id)
    pdf_bytes = mail_service.generate_mail_pdf(session_id, formula)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="formule-{session_id}.pdf"'},
    )


@router.post("/mail/test")
async def test_mail(body: TestMailRequest):
    """Test SMTP connection and send a simple test email."""
    try:
        mail_service.send_test_mail(body.to)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"SMTP error: {exc}")
    return {"status": "ok", "to": body.to}


@router.post("/session/{session_id}/mail/send")
async def send_mail(session_id: str, body: SendMailRequest):
    """Send the mail HTML directly in the body of an email."""
    formula = _get_formula_or_404(session_id)
    try:
        mail_service.send_mail(body.to, session_id, formula)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {exc}")
    return {"status": "ok", "to": body.to}
