import uuid
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.db_models import ReportModel, Voucher
from app.services.checklist_service import (
    load_checklist_by_industry,
    get_all_available_industries
)

router = APIRouter(prefix="/reports", tags=["Raporty i Analiza"])


class AnalyzeLinkRequest(BaseModel):
    url: str
    industry_id: Optional[str] = None


class VoucherUnlockRequest(BaseModel):
    voucher_code: str


async def detect_industry_from_url(url: str, available_industries: List[Dict[str, str]]) -> str:
    """Automatyczna klasyfikacja branży na podstawie adresu URL ogłoszenia."""
    url_lower = url.lower()
    
    if any(k in url_lower for k in ["maszyny", "rolnicze", "budowlane", "traktor", "koparka", "kombajn"]):
        return "sprzet_i_maszyny_rolnicze_oraz_budowlane"
    if any(k in url_lower for k in ["rower", "rowery", "bike"]):
        return "rowery"
    if any(k in url_lower for k in ["mieszkanie", "dom", "dzialka", "nieruchomosci", "otodom"]):
        return "nieruchomosci"
    if any(k in url_lower for k in ["auto", "samochod", "otomoto", "motoryzacja", "pojazd"]):
        return "motoryzacja"
    if any(k in url_lower for k in ["laptop", "telefon", "elektronika", "komputer", "it"]):
        return "elektronika_uzytkowa_i_sprzet_IT"
    if any(k in url_lower for k in ["medyczny", "uszg", "rentgen", "stomatologiczny", "aparat"]):
        return "sprzet_i_urzadzenia_medyczne"

    if available_industries:
        return available_industries[0]["id"]
    
    return "sprzet_i_maszyny_rolnicze_oraz_budowlane"


@router.get("/industries", summary="Pobierz listę dostępnych branż")
async def list_industries():
    """Zwraca listę wszystkich branż zarejestrowanych w systemie."""
    return {
        "status": "success",
        "industries": get_all_available_industries()
    }


@router.get("/checklists/{industry_id}", summary="Pobierz checklistę dla branży")
async def get_checklist(industry_id: str):
    """Zwraca znormalizowany plik JSON z punktami analizy dla podanego industry_id."""
    return load_checklist_by_industry(industry_id)


@router.post("/analyze", summary="Przeanalizuj link ogłoszenia (bez zapisu)")
async def analyze_report(payload: AnalyzeLinkRequest):
    """Szybka analiza linku bez tworzenia wpisu w bazie danych."""
    available_industries = get_all_available_industries()
    detected_industry = payload.industry_id or await detect_industry_from_url(payload.url, available_industries)
    checklist_data = load_checklist_by_industry(detected_industry)

    return {
        "status": "success",
        "url": payload.url,
        "industry_id": detected_industry,
        "industry_name": checklist_data.get("name") or checklist_data.get("title") or "Analiza Ogólna",
        "freemium_checkpoints": checklist_data.get("freemium_checkpoints") or checklist_data.get("public_free_summary"),
        "categories": checklist_data.get("categories") or checklist_data.get("paid_detailed_analysis", {}).get("categories", []),
        "paid_modules": checklist_data.get("paid_post_analysis_modules") or checklist_data.get("ai_generated_action_plan"),
        "available_industries": available_industries
    }


@router.post("", status_code=status.HTTP_201_CREATED, summary="Utwórz i zapisz nowy raport")
async def create_report(payload: AnalyzeLinkRequest, db: AsyncSession = Depends(get_db)):
    """Tworzy nowy raport w bazie danych i zwraca stan freemium."""
    available_industries = get_all_available_industries()
    detected_industry = payload.industry_id or await detect_industry_from_url(payload.url, available_industries)
    checklist_data = load_checklist_by_industry(detected_industry)

    industry_name = (
        checklist_data.get("name")
        or checklist_data.get("title")
        or checklist_data.get("industry_name")
        or "Analiza Ogólna"
    )
    freemium_checkpoints = (
        checklist_data.get("freemium_checkpoints")
        or checklist_data.get("public_free_summary", {})
    )

    generated_report_id = f"REP-{uuid.uuid4().hex[:8].upper()}"

    new_report = ReportModel(
        report_id=generated_report_id,
        target_url=payload.url,
        source_url=payload.url,
        title_raw=f"Analiza dla {payload.url}",
        category=detected_industry,
        industry_name=industry_name,
        is_paid=False,
        is_unlocked=False,
        risk_score=30,
        risk_level="NISKIE",
        freemium_preview={"checkpoints": freemium_checkpoints} if isinstance(freemium_checkpoints, list) else freemium_checkpoints,
        digital_footprint={},
        financial_analysis={},
        expert_checkpoints={},
        negotiation_assistant={},
    )

    db.add(new_report)
    await db.commit()
    await db.refresh(new_report)

    return {
        "report_id": new_report.report_id,
        "target_url": new_report.target_url,
        "industry_name": new_report.industry_name,
        "is_unlocked": new_report.is_unlocked,
        "is_paid": new_report.is_paid,
        "deep_analysis": {
            "verdict": "Zablokowana. Opłać raport lub użyj vouchera, aby odblokować pełną analizę."
        },
        "freemium_preview": new_report.freemium_preview
    }


@router.get("/{report_id}", summary="Pobierz raport po ID")
async def get_report(report_id: str, db: AsyncSession = Depends(get_db)):
    """Pobiera istniejący raport z bazy danych po jego czytelnym report_id."""
    stmt = select(ReportModel).where(ReportModel.report_id == report_id)
    result = await db.execute(stmt)
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Raport nie został znaleziony"
        )

    verdict_text = "Odblokowana" if report.is_unlocked else "Zablokowana. Opłać raport."

    return {
        "report_id": report.report_id,
        "target_url": report.target_url,
        "industry_name": report.industry_name,
        "is_unlocked": report.is_unlocked,
        "is_paid": report.is_paid,
        "freemium_preview": report.freemium_preview,
        "deep_analysis": {
            "verdict": verdict_text
        }
    }


@router.post("/{report_id}/mock-checkout", summary="Symulacja opłacenia raportu")
async def mock_checkout(report_id: str, db: AsyncSession = Depends(get_db)):
    """Odblokowuje raport w trybie testowym/mock."""
    stmt = select(ReportModel).where(ReportModel.report_id == report_id)
    result = await db.execute(stmt)
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Raport nie został znaleziony"
        )

    report.is_unlocked = True
    report.is_paid = True
    await db.commit()
    await db.refresh(report)

    return {
        "status": "success",
        "report_id": report.report_id,
        "is_unlocked": report.is_unlocked,
        "is_paid": report.is_paid,
        "message": "Raport został pomyślnie odblokowany."
    }


@router.post("/{report_id}/voucher", summary="Odblokuj raport voucherem")
async def unlock_with_voucher(
    report_id: str,
    payload: VoucherUnlockRequest,
    db: AsyncSession = Depends(get_db)
):
    """Weryfikuje kod vouchera i odblokowuje raport."""
    stmt = select(ReportModel).where(ReportModel.report_id == report_id)
    result = await db.execute(stmt)
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Raport nie został znaleziony"
        )

    voucher_stmt = select(Voucher).where(
        Voucher.code == payload.voucher_code,
        Voucher.is_active == True
    )
    v_result = await db.execute(voucher_stmt)
    voucher = v_result.scalar_one_or_none()

    if not voucher:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nieprawidłowy lub nieaktywny kod vouchera"
        )

    voucher.is_active = False
    report.is_unlocked = True
    report.is_paid = True

    await db.commit()
    await db.refresh(report)

    return {
        "status": "success",
        "report_id": report.report_id,
        "is_unlocked": report.is_unlocked,
        "is_paid": report.is_paid,
        "message": "Voucher został pomyślnie wykorzystany."
    }