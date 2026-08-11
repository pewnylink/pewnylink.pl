# test_voucher_unlock.py
import asyncio
import uuid
from datetime import datetime, timezone

from app.database import Base, engine, AsyncSessionLocal
from app.models.db_models import ReportModel, Voucher
from app.services.report_repository import ReportRepository


async def main():
    print("=== START TESTU VOUCHERA I REPOZYTORIUM ===")

    # 1. Tworzenie wszystkich tabel w bazie przed uruchomieniem testu
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        repo = ReportRepository(db)

        # [1/4] Tworzenie raportu testowego
        report_code = f"REP-TEST-{uuid.uuid4().hex[:6].upper()}"
        print(f"\n[1/4] Tworzenie raportu testowego ({report_code})...")

        dummy_report_data = {
            "report_id": report_code,
            "target_url": "https://example.com/test-offer",
            "source_url": "https://example.com",
            "title_raw": "Testowe Ogłoszenie dla Vouchera",
            "category": "test",
            "industry_name": "Testy Systemowe",
            "risk_score": 15,
            "risk_level": "NISKIE",
            "seller_type": "Prywatny",
            "is_paid": False,
            "is_unlocked": False,
            "freemium_preview": {"summary": "Wstępny podgląd"},
            "digital_footprint": {"score": 100},
            "financial_analysis": {"status": "ok"},
            "expert_checkpoints": [],
            "negotiation_assistant": {}
        }

        created_report = await repo.create_report(dummy_report_data)
        print(f"✓ Raport utworzony z ID bazy: {created_report.id} (kod biznesowy: {created_report.report_id})")

        # [2/4] Generowanie kodu vouchera
        voucher_code = f"TEST-{uuid.uuid4().hex[:4].upper()}"
        print(f"\n[2/4] Generowanie vouchera testowego: {voucher_code}...")

        new_voucher = Voucher(
            code=voucher_code,
            is_active=True
        )
        db.add(new_voucher)
        await db.commit()
        await db.refresh(new_voucher)
        print("✓ Voucher zapisany w bazie.")

        # [3/4] Odblokowywanie raportu za pomocą repozytorium
        print(f"\n[3/4] Realizacja vouchera {voucher_code} dla raportu {report_code}...")
        
        unlocked_report, error = await repo.unlock_with_voucher(report_code, voucher_code)

        if unlocked_report and not error:
            print("✓ Voucher aktywowany! Raport został odblokowany.")
        else:
            print(f"✗ Błąd: {error}")

        # [4/4] Weryfikacja końcowa stanu w bazie
        print("\n[4/4] Weryfikacja stanu końcowego...")
        updated_report = await repo.get_by_report_id(report_code)
        
        is_unlocked = getattr(updated_report, "is_unlocked", False) or getattr(updated_report, "is_paid", False)
        
        if updated_report and is_unlocked:
            print(f" SUCCESS: Raport {report_code} ma status odblokowany (is_unlocked=True)!")
        else:
            print(f" FAILURE: Raport {report_code} nadal jest zablokowany.")

    print("\n=== ZAKOŃCZONO TEST ===")


if __name__ == "__main__":
    asyncio.run(main())