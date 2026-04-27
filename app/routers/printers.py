import asyncio
import base64
import os
import socket
import subprocess
import tempfile

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database.connection import get_db
from app.database import crud

router = APIRouter(prefix="/printers", tags=["printers"])

PROTOCOL_BY_PORT = {9100: "raw", 515: "lpd", 631: "cups"}

# Compteur de jobs actifs par printnode_id pour le load balancing
_job_counters: dict[int, int] = {}


class PrinterCreate(BaseModel):
    name: str
    location: str
    ip: str
    port: int = 631
    protocol: str = "printnode"
    cups_name: str | None = None
    printnode_id: int | None = None
    is_active: bool = True


class PrinterUpdate(BaseModel):
    name: str | None = None
    location: str | None = None
    ip: str | None = None
    port: int | None = None
    protocol: str | None = None
    cups_name: str | None = None
    printnode_id: int | None = None
    is_active: bool | None = None


class PrinterResponse(BaseModel):
    id: int
    name: str
    location: str
    ip: str
    port: int
    protocol: str
    cups_name: str | None
    printnode_id: int | None
    is_active: bool

    class Config:
        from_attributes = True


class PrintRequest(BaseModel):
    location: str
    content: str


class FormulaNotes(BaseModel):
    top: list[str] = []
    heart: list[str] = []
    base: list[str] = []


class FormulaData(BaseModel):
    profile: str
    notes: FormulaNotes
    date: str
    reference: str = ""


class PrintFormulaRequest(BaseModel):
    location: str
    formula: FormulaData


async def _print_printnode_pdf(printnode_id: int, pdf_bytes: bytes):
    api_key = get_settings().printnode_api_key
    if not api_key:
        raise RuntimeError("PRINTNODE_API_KEY non configurée")
    content_b64 = base64.b64encode(pdf_bytes).decode("utf-8")
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.printnode.com/printjobs",
            auth=(api_key, ""),
            json={
                "printer": printnode_id,
                "title": "Formule",
                "contentType": "pdf_base64",
                "content": content_b64,
                "source": "Lylo",
            },
        )
        if response.status_code not in (200, 201):
            raise RuntimeError(f"PrintNode error {response.status_code}: {response.text}")


async def _print_printnode(printnode_id: int, content: str):
    api_key = get_settings().printnode_api_key
    if not api_key:
        raise RuntimeError("PRINTNODE_API_KEY non configurée")
    content_b64 = base64.b64encode(content.encode("utf-8")).decode("utf-8")
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.printnode.com/printjobs",
            auth=(api_key, ""),
            json={
                "printer": printnode_id,
                "title": "Print job",
                "contentType": "raw_base64",
                "content": content_b64,
                "source": "Lylo",
            },
        )
        if response.status_code not in (200, 201):
            raise RuntimeError(f"PrintNode error {response.status_code}: {response.text}")


async def _print_cups_pdf(cups_name: str, pdf_bytes: bytes):
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(pdf_bytes)
        tmp_path = f.name
    try:
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: subprocess.run(
                ["lp", "-d", cups_name, tmp_path],
                capture_output=True,
                text=True,
            ),
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr)
    finally:
        os.unlink(tmp_path)


async def _print_cups(cups_name: str, content: str):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(content)
        tmp_path = f.name
    try:
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: subprocess.run(
                ["lp", "-d", cups_name, tmp_path],
                capture_output=True,
                text=True,
            ),
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr)
    finally:
        os.unlink(tmp_path)


async def _print_raw(ip: str, port: int, content: str):
    from escpos.printer import Network
    p = Network(ip, port=port)
    p.text(content + "\n\n\n")
    p.cut()


async def _register_cups(ip: str, cups_name: str):
    result = await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: subprocess.run(
            ["lpadmin", "-p", cups_name, "-E", "-v", f"ipp://{ip}/ipp/print", "-m", "everywhere"],
            capture_output=True,
            text=True,
        ),
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr)


@router.get("/network/scan")
async def scan_printers():
    try:
        local_ip = socket.gethostbyname(socket.gethostname())
    except Exception:
        local_ip = "192.168.1.1"

    base_ip = ".".join(local_ip.split(".")[:3])
    found = []

    def resolve_hostname(ip: str) -> str:
        try:
            return socket.gethostbyaddr(ip)[0]
        except Exception:
            return ip

    async def check_port(ip: str, port: int) -> bool:
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, port), timeout=0.3
            )
            writer.close()
            await writer.wait_closed()
            return True
        except Exception:
            return False

    async def check(ip: str):
        for port, protocol in PROTOCOL_BY_PORT.items():
            if await check_port(ip, port):
                hostname = await asyncio.get_event_loop().run_in_executor(None, resolve_hostname, ip)
                found.append({"ip": ip, "port": port, "protocol": protocol, "hostname": hostname})
                return

    await asyncio.gather(*[check(f"{base_ip}.{i}") for i in range(1, 255)])

    # Récupère les imprimantes PrintNode et associe par hostname
    printnode_by_hostname = {}
    printnode_list = []
    api_key = get_settings().printnode_api_key
    if api_key:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.printnode.com/printers",
                    auth=(api_key, ""),
                    timeout=5,
                )
                if response.status_code == 200:
                    for pn in response.json():
                        printnode_list.append({
                            "printnode_id": pn["id"],
                            "name": pn["name"],
                            "description": pn.get("description", ""),
                            "state": pn.get("state", ""),
                        })
                        printnode_by_hostname[pn["name"].lower()] = pn["id"]
        except Exception:
            pass

    # Associe par hostname réseau ou nom PrintNode
    for printer in found:
        hostname_clean = printer["hostname"].split(".")[0].lower()
        printnode_id = printnode_by_hostname.get(hostname_clean)
        # Fallback : cherche si le hostname est contenu dans un nom PrintNode
        if not printnode_id:
            for pn_name, pn_id in printnode_by_hostname.items():
                if hostname_clean in pn_name or pn_name in hostname_clean:
                    printnode_id = pn_id
                    break
        printer["printnode_id"] = printnode_id

    return {"printers": found, "printnode_printers": printnode_list}


@router.post("/register-cups")
async def register_cups(printer_id: int, db: AsyncSession = Depends(get_db)):
    printer = await crud.get_printer_by_id(db, printer_id)
    if not printer:
        raise HTTPException(status_code=404, detail="Imprimante introuvable")
    if not printer.cups_name:
        raise HTTPException(status_code=400, detail="cups_name manquant sur l'imprimante")
    try:
        await _register_cups(printer.ip, printer.cups_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur CUPS: {str(e)}")
    return {"status": "ok", "cups_name": printer.cups_name}


@router.get("/", response_model=list[PrinterResponse])
async def list_printers(db: AsyncSession = Depends(get_db)):
    return await crud.get_all_printers(db)


@router.get("/{printer_id}", response_model=PrinterResponse)
async def get_printer(printer_id: int, db: AsyncSession = Depends(get_db)):
    printer = await crud.get_printer_by_id(db, printer_id)
    if not printer:
        raise HTTPException(status_code=404, detail="Imprimante introuvable")
    return printer


@router.post("/", response_model=PrinterResponse, status_code=201)
async def create_printer(body: PrinterCreate, db: AsyncSession = Depends(get_db)):
    data = body.model_dump()

    if data["protocol"] == "cups":
        # Génère un cups_name depuis le nom si non fourni
        if not data.get("cups_name"):
            data["cups_name"] = body.name.lower().replace(" ", "_")
        try:
            await _register_cups(data["ip"], data["cups_name"])
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erreur enregistrement CUPS: {str(e)}")

    return await crud.create_printer(db, **data)


@router.patch("/{printer_id}", response_model=PrinterResponse)
async def update_printer(printer_id: int, body: PrinterUpdate, db: AsyncSession = Depends(get_db)):
    updated = await crud.update_printer(db, printer_id, **body.model_dump(exclude_none=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Imprimante introuvable")
    return updated


@router.delete("/{printer_id}", status_code=204)
async def delete_printer(printer_id: int, db: AsyncSession = Depends(get_db)):
    deleted = await crud.delete_printer(db, printer_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Imprimante introuvable")


@router.post("/print")
async def print_document(body: PrintRequest, db: AsyncSession = Depends(get_db)):
    printers = await crud.get_printers_by_location(db, body.location)
    if not printers:
        raise HTTPException(status_code=404, detail=f"Aucune imprimante active pour '{body.location}'")

    # Load balancing — choisit l'imprimante avec le moins de jobs actifs
    printer = min(printers, key=lambda p: _job_counters.get(p.id, 0))

    # Incrémente le compteur
    _job_counters[printer.id] = _job_counters.get(printer.id, 0) + 1

    try:
        if printer.protocol == "printnode":
            if not printer.printnode_id:
                raise HTTPException(status_code=400, detail="printnode_id manquant sur l'imprimante")
            await _print_printnode(printer.printnode_id, body.content)
        elif printer.protocol == "cups":
            if not printer.cups_name:
                raise HTTPException(status_code=400, detail="cups_name manquant sur l'imprimante")
            await _print_cups(printer.cups_name, body.content)
        elif printer.protocol == "raw":
            await _print_raw(printer.ip, printer.port, body.content)
        else:
            raise HTTPException(status_code=400, detail=f"Protocole inconnu : {printer.protocol}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur impression: {str(e)}")
    finally:
        # Décrémente le compteur quoi qu'il arrive
        _job_counters[printer.id] = max(0, _job_counters.get(printer.id, 1) - 1)

    return {"status": "ok", "printer": printer.name}


@router.post("/print-formula")
async def print_formula(body: PrintFormulaRequest, db: AsyncSession = Depends(get_db)):
    printers = await crud.get_printers_by_location(db, body.location)
    if not printers:
        raise HTTPException(status_code=404, detail=f"Aucune imprimante active pour '{body.location}'")

    printer = min(printers, key=lambda p: _job_counters.get(p.id, 0))
    _job_counters[printer.id] = _job_counters.get(printer.id, 0) + 1

    try:
        from app.services.pdf_service import generate_formula_pdf
        pdf_bytes = generate_formula_pdf(body.formula.model_dump())

        if printer.protocol == "printnode":
            if not printer.printnode_id:
                raise HTTPException(status_code=400, detail="printnode_id manquant sur l'imprimante")
            await _print_printnode_pdf(printer.printnode_id, pdf_bytes)
        elif printer.protocol == "cups":
            if not printer.cups_name:
                raise HTTPException(status_code=400, detail="cups_name manquant sur l'imprimante")
            await _print_cups_pdf(printer.cups_name, pdf_bytes)
        else:
            raise HTTPException(status_code=400, detail=f"Protocole non supporté pour PDF : {printer.protocol}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur impression: {str(e)}")
    finally:
        _job_counters[printer.id] = max(0, _job_counters.get(printer.id, 1) - 1)

    return {"status": "ok", "printer": printer.name}


class PrintMultiFormulaRequest(BaseModel):
    location: str
    formulas: list[FormulaData]


@router.post("/print-multi")
async def print_multi_formulas(body: PrintMultiFormulaRequest, db: AsyncSession = Depends(get_db)):
    """Imprime toutes les formules d'un groupe (mode multi-utilisateurs) sur l'imprimante de la location."""
    printers = await crud.get_printers_by_location(db, body.location)
    if not printers:
        raise HTTPException(status_code=404, detail=f"Aucune imprimante active pour '{body.location}'")

    printer = min(printers, key=lambda p: _job_counters.get(p.id, 0))
    _job_counters[printer.id] = _job_counters.get(printer.id, 0) + 1

    try:
        from app.services.pdf_service import generate_formula_pdf
        for formula in body.formulas:
            pdf_bytes = generate_formula_pdf(formula.model_dump())
            if printer.protocol == "printnode":
                if not printer.printnode_id:
                    raise HTTPException(status_code=400, detail="printnode_id manquant sur l'imprimante")
                await _print_printnode_pdf(printer.printnode_id, pdf_bytes)
            elif printer.protocol == "cups":
                if not printer.cups_name:
                    raise HTTPException(status_code=400, detail="cups_name manquant sur l'imprimante")
                await _print_cups_pdf(printer.cups_name, pdf_bytes)
            else:
                raise HTTPException(status_code=400, detail=f"Protocole non supporté pour PDF : {printer.protocol}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur impression: {str(e)}")
    finally:
        _job_counters[printer.id] = max(0, _job_counters.get(printer.id, 1) - 1)

    return {"status": "ok", "printer": printer.name, "count": len(body.formulas)}