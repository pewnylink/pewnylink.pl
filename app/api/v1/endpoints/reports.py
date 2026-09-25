import uuid
import re
import logging
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.db_models import ReportModel, Voucher, User
from app.services.checklist_service import (
    load_checklist_by_industry,
    get_all_available_industries
)

# Bezpieczny import AuditEngine do scrapingu / analizy URL
try:
    from app.services.audit_service import AuditEngine
except ImportError:
    class AuditEngine:
        @staticmethod
        async def analyze_url(url: str) -> Dict[str, Any]:
            return {}

# Import autoryzacji z modułu auth
try:
    from app.routers.auth import get_optional_current_user
except ImportError:
    try:
        from app.routers.auth import get_current_user as get_optional_current_user
    except ImportError:
        async def get_optional_current_user() -> Optional[User]:
            return None

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["Raporty i Analiza"])


class AnalyzeLinkRequest(BaseModel):
    url: str
    industry_id: Optional[str] = None


class VoucherUnlockRequest(BaseModel):
    voucher_code: str


def check_is_admin(user: Optional[User]) -> bool:
    """Niezawodna weryfikacja uprawnień administratora."""
    if not user:
        return False
    if getattr(user, "is_admin", False):
        return True
    
    role_attr = getattr(user, "role", "")
    role_str = str(getattr(role_attr, "value", role_attr)).upper()
    return role_str in ["ADMIN", "SUPER_ADMIN"]


def sanitize_and_truncate_title(title: str, max_length: int = 150) -> str:
    """
    Sanitizuje tytuł ogłoszenia z potencjalnych danych osobowych (RODO / Art. 51 Ust. 1)
    oraz ogranicza jego długość (minimalizacja przechowywanych danych).
    """
    if not title:
        return ""
    
    # 1. Anonimizacja numerów telefonów (różne formaty)
    title = re.sub(r'(?:\+\d{2}\s?)?(?:\d{3}[\s-]?\d{3}[\s-]?\d{3}|\d{9})', '[NUMER TELEFONU]', title)
    
    # 2. Anonimizacja adresów e-mail
    title = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '[E-MAIL]', title)
    
    # 3. Trim i obcięcie długości
    title = title.strip()
    if len(title) > max_length:
        title = title[:max_length] + "..."
        
    return title


# ------------------------------------------------------------------------------
# SILNIK KLASYFIKACJI BRANŻOWEJ (ANALIZA W LOCIE)
# ------------------------------------------------------------------------------

INDUSTRY_PATTERNS: Dict[str, List[str]] = {
    "sprzet_i_maszyny_rolnicze_oraz_budowlane": [
        r"ciągnik", r"traktor", r"koparka", r"kombajn", r"siewnik", r"pług", r"ładowarka",
        r"jcb", r"caterpillar", r"cat\b", r"kubota", r"ursus", r"john deere", r"claas", r"new holland",
        r"zagęszczarka", r"rusztowanie", r"betoniarka", r"minikoparka", r"wózek widłowy", r"silos",
        r"opryskiwacz", r"przetrząsacz", r"owijarka", r"podnośnik koszowy", r"agregat prądotwórczy"
    ],
    "rowery": [
        r"rower", r"bike", r"mtb", r"gravel", r"kolarzówka", r"e-bike", r"szosa", r"rama rowerowa",
        r"trek", r"giant", r"specialized", r"cannondale", r"scott", r"kross", r"romet", r"cube",
        r"shimano", r"sram", r"przerzutka", r"widelec amortyzowany", r"hulajnoga", r"przełajowy"
    ],
    "nieruchomosci": [
        r"mieszkanie", r"apartament", r"dom", r"działka", r"lokal", r"hala", r"magazyn",
        r"kawalerka", r"otodom", r"grunt", r"sprzedam dom", r"wynajmę mieszkanie", r"kamienica",
        r"działka budowlana", r"biuro", r"garaż", r"teren inwestycyjny"
    ],
    "motoryzacja": [
        r"samochód", r"auto\b", r"pojazd", r"otomoto", r"audi", r"bmw", r"mercedes", r"volkswagen",
        r"vw\b", r"toyota", r"ford", r"opel", r"skoda", r"renault", r"peugeot", r"motocykl",
        r"skuter", r"quad", r"silnik", r"skrzynia biegów", r"felgi", r"opony", r"zderzak",
        r"przebieg", r"bezwypadkowy", r"vin\b", r"honda shadow", r"virago", r"chopper"
    ],
    "elektronika_uzytkowa_i_sprzet_IT": [
        r"laptop", r"notebook", r"komputer", r"pc\b", r"telefon", r"smartfon", r"iphone",
        r"samsung", r"xiaomi", r"redmi", r"poco", r"pixel", r"ipad", r"tablet", r"monitor",
        r"procesor", r"karta graficzna", r"rtx", r"gtx", r"macbook", r"konsola", r"ps5", r"xbox",
        r"słuchawki", r"soundcore", r"sony wh", r"rtv", r"agd", r"telewizor", r"smartwatch"
    ],
    "sprzet_i_urzadzenia_medyczne": [
        r"medyczny", r"uszg", r"usg\b", r"rentgen", r"rtg\b", r"stomatologiczny", r"fotel stomatologiczny",
        r"kardiomonitor", r"defibrylator", r"autoklaw", r"ekg\b", r"pulsoksymetr", r"laser medyczny",
        r"sprzet rehabilitacyjny", r"wózek inwalidzki", r"aparat słuchowy", r"insuflator"
    ]
}


async def detect_industry_with_ai_fallback(title: str, description: str, available_industries: List[Dict[str, str]]) -> Optional[str]:
    """Miejsce na ewentualną integrację z zewnętrznym modelem LLM."""
    return None


async def classify_industry_smart(
    url: str,
    scraped_title: Optional[str] = None,
    scraped_description: Optional[str] = None,
    scraped_category: Optional[str] = None,
    available_industries: Optional[List[Dict[str, str]]] = None
) -> str:
    """
    Klasyfikacja przetwarzana wyłącznie w pamięci operacyjnej (in-memory):
    1. Dopasowanie wzorców (regex/stems) w pobranym Tytule, Opisie i Kategorii.
    2. Fallback do AI dla nietypowych opisów.
    3. Fallback do słów kluczowych w samym adresie URL.
    4. Domyślna kategoria w razie braku trafień.
    """
    industries = available_industries or get_all_available_industries()
    valid_industry_ids = {ind.get("id") for ind in industries if isinstance(ind, dict) and "id" in ind}

    text_to_analyze = " ".join(filter(None, [scraped_title, scraped_description, scraped_category])).lower()

    if text_to_analyze.strip():
        scores: Dict[str, int] = {ind_id: 0 for ind_id in INDUSTRY_PATTERNS.keys()}

        for ind_id, patterns in INDUSTRY_PATTERNS.items():
            for pattern in patterns:
                matches = len(re.findall(pattern, text_to_analyze))
                if matches > 0:
                    if scraped_title and re.search(pattern, scraped_title.lower()):
                        scores[ind_id] += matches * 3
                    else:
                        scores[ind_id] += matches

        best_industry = max(scores, key=scores.get)
        if scores[best_industry] > 0 and (not valid_industry_ids or best_industry in valid_industry_ids):
            return best_industry

        ai_detected = await detect_industry_with_ai_fallback(scraped_title or "", scraped_description or "", industries)
        if ai_detected and ai_detected in valid_industry_ids:
            return ai_detected

    url_lower = url.lower()
    for ind_id, patterns in INDUSTRY_PATTERNS.items():
        if any(re.search(p, url_lower) for p in patterns):
            if not valid_industry_ids or ind_id in valid_industry_ids:
                return ind_id

    if industries and isinstance(industries[0], dict) and "id" in industries[0]:
        return industries[0]["id"]

    return "elektronika_uzytkowa_i_sprzet_IT"


async def fetch_scraped_offer_details(url: str) -> Dict[str, Any]:
    """Pobieranie szczegółów z zewnętrznego URL bez zapisywania w bazie."""
    try:
        scraped_data = await AuditEngine.analyze_url(url=url)
        if isinstance(scraped_data, dict):
            return scraped_data
    except Exception as e:
        logger.warning(f"Błąd podczas scrapingu URL {url}: {e}")
    
    return {}


# ------------------------------------------------------------------------------
# ENDPOINTY API
# ------------------------------------------------------------------------------

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
    checklist_data = load_checklist_by_industry(industry_id)
    if not checklist_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Nie odnaleziono checklisty dla branży: {industry_id}"
        )
    return checklist_data


@router.post("/analyze", summary="Przeanalizuj link ogłoszenia (bez zapisu - ephemeral)")
async def analyze_report(payload: AnalyzeLinkRequest):
    """
    Szybka analiza linku w locie. Zero zapisu do bazy danych,
    co gwarantuje 100% zgodności z RODO i zasadą minimalizacji.
    """
    available_industries = get_all_available_industries()
    scraped_info = await fetch_scraped_offer_details(payload.url)

    if payload.industry_id:
        detected_industry = payload.industry_id
    else:
        detected_industry = await classify_industry_smart(
            url=payload.url,
            scraped_title=scraped_info.get("title"),
            scraped_description=scraped_info.get("description"),
            scraped_category=scraped_info.get("category"),
            available_industries=available_industries
        )

    checklist_data = load_checklist_by_industry(detected_industry) or {}

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
async def create_report(
    payload: AnalyzeLinkRequest, 
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """
    Tworzy nowy rekord raportu w bazie.
    Zapisuje wyłącznie zanonimizowany tytuł (sanitize_and_truncate_title) oraz metadane raportu.
    Opisy i surowe dane oferty są odrzucane z pamięci.
    """
    available_industries = get_all_available_industries()
    
    # 1. Scraping w pamięci RAM
    scraped_info = await fetch_scraped_offer_details(payload.url)
    
    # 2. Klasyfikacja
    if payload.industry_id:
        detected_industry = payload.industry_id
    else:
        detected_industry = await classify_industry_smart(
            url=payload.url,
            scraped_title=scraped_info.get("title"),
            scraped_description=scraped_info.get("description"),
            scraped_category=scraped_info.get("category"),
            available_industries=available_industries
        )

    checklist_data = load_checklist_by_industry(detected_industry) or {}

    # 3. Zgodność z RODO: Czyszczenie danych osobowych z tytułu przed zapisem do DB
    raw_scraped_title = scraped_info.get("title")
    if raw_scraped_title:
        real_title = sanitize_and_truncate_title(raw_scraped_title)
    else:
        real_title = f"Analiza dla {payload.url}"

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
    categories = checklist_data.get("categories") or checklist_data.get("paid_detailed_analysis", {}).get("categories", [])
    paid_modules = checklist_data.get("paid_post_analysis_modules") or checklist_data.get("ai_generated_action_plan")

    is_admin = check_is_admin(current_user)
    auto_unlock = is_admin

    generated_report_id = f"REP-{uuid.uuid4().hex[:8].upper()}"

    report_kwargs = {
        "report_id": generated_report_id,
        "target_url": payload.url,
        "source_url": payload.url,
        "title_raw": real_title,
        "category": detected_industry,
        "industry_name": industry_name,
        "is_paid": auto_unlock,
        "is_unlocked": auto_unlock,
        "risk_score": 30,
        "risk_level": "NISKIE",
        "freemium_preview": {"checkpoints": freemium_checkpoints} if isinstance(freemium_checkpoints, list) else freemium_checkpoints,
        "digital_footprint": {},
        "financial_analysis": {},
        "expert_checkpoints": {"categories": categories} if categories else {},
        "negotiation_assistant": {},
    }

    if current_user and hasattr(ReportModel, "user_id"):
        report_kwargs["user_id"] = current_user.id

    new_report = ReportModel(**report_kwargs)

    db.add(new_report)
    await db.commit()
    await db.refresh(new_report)

    verdict_text = "Odblokowana" if auto_unlock else "Zablokowana. Opłać raport lub użyj vouchera, aby odblokować pełną analizę."

    response_payload = {
        "report_id": new_report.report_id,
        "target_url": new_report.target_url,
        "title_raw": new_report.title_raw,
        "industry_name": new_report.industry_name,
        "is_unlocked": auto_unlock,
        "is_paid": auto_unlock,
        "freemium_preview": new_report.freemium_preview,
        "deep_analysis": {
            "verdict": verdict_text,
            "categories": categories if auto_unlock else [],
            "paid_modules": paid_modules if auto_unlock else []
        }
    }

    if auto_unlock:
        response_payload["categories"] = categories
        response_payload["paid_modules"] = paid_modules

    return response_payload


@router.get("/{report_id}", summary="Pobierz raport po ID")
async def get_report(
    report_id: str, 
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """Pobiera istniejący raport z bazy danych po czytelnym report_id."""
    stmt = select(ReportModel).where(ReportModel.report_id == report_id)
    result = await db.execute(stmt)
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Raport nie został znaleziony"
        )

    category = report.category or "elektronika_uzytkowa_i_sprzet_IT"
    checklist_data = load_checklist_by_industry(category) or {}
    categories = checklist_data.get("categories") or checklist_data.get("paid_detailed_analysis", {}).get("categories", [])
    paid_modules = checklist_data.get("paid_post_analysis_modules") or checklist_data.get("ai_generated_action_plan")

    is_admin = check_is_admin(current_user)
    effective_unlocked = report.is_unlocked or is_admin
    effective_paid = report.is_paid or is_admin

    verdict_text = "Odblokowana" if effective_unlocked else "Zablokowana. Opłać raport."

    response_payload = {
        "report_id": report.report_id,
        "target_url": report.target_url,
        "title_raw": getattr(report, "title_raw", report.target_url),
        "industry_name": report.industry_name or checklist_data.get("name") or "Analiza Ogólna",
        "is_unlocked": effective_unlocked,
        "is_paid": effective_paid,
        "freemium_preview": report.freemium_preview,
        "deep_analysis": {
            "verdict": verdict_text,
            "categories": categories if effective_unlocked else [],
            "paid_modules": paid_modules if effective_unlocked else []
        }
    }

    if effective_unlocked:
        response_payload["categories"] = categories
        response_payload["paid_modules"] = paid_modules

    return response_payload


@router.post("/{report_id}/mock-checkout", summary="Symulacja opłacenia raportu")
async def mock_checkout(report_id: str, db: AsyncSession = Depends(get_db)):
    """Odblokowuje raport w trybie testowym."""
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