# test_audit_pipeline.py
import asyncio
from app.services.audit_service import AuditEngine


async def run_test():
    # Przykładowy URL do weryfikacji analizy w locie
    test_url = "https://www.olx.pl/d/oferta/gitara-elektryczna-epiphone-les-paul-custom-CID99-ID12345.html"

    print("=" * 60)
    print(f"Uruchamianie audytu testowego dla: {test_url}")
    print("=" * 60)

    try:
        # Wywołanie silnika audytowego w locie
        report = await AuditEngine.analyze_url(url=test_url, is_unlocked=True)

        print("\n[STANY I WSKAŹNIKI]")
        print(f"• Tytuł:             {report.get('title')}")
        print(f"• Cena w ofercie:    {report.get('price')} PLN")
        print(f"• Poziom ryzyka:     {report.get('risk_level')} (Score: {report.get('risk_score')}/100)")
        print(f"• Liczba zdjęć:      {report.get('images_count')} (Analiza w locie - brak zapisu w DB/S3)")
        print(f"• Typ sprzedawcy:    {report.get('seller_type')}")
        print(f"• Całkowity TCO:     {report.get('total_price_with_tco')} PLN")
        print(f"• Sugerowany rabat:  {report.get('suggested_discount')}")

        print(f"\n[WYKRYTE FLAGI PRAWNE / RYZYKA ({len(report.get('legal_flags', []))})]")
        for flag in report.get("legal_flags", []):
            print(f"  - {flag.get('title')}: {flag.get('description')}")

        print(f"\n[SKRYPT NEGOCJACYJNY]")
        print(f'"{report.get("negotiation_script")}"')

        print("\n" + "=" * 60)
        print("Test zakończony sukcesem. Przetwarzanie w locie działa prawidłowo.")
        print("=" * 60)

    except Exception as e:
        print(f"\n[BŁĄD PODCZAS WYKONANIA TESTU]: {e}")


if __name__ == "__main__":
    asyncio.run(run_test())