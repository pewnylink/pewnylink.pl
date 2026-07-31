# test_scraper.py
import asyncio
from app.scrapers.scraper_engine import ScraperEngine

async def test_connection():
    print("🚀 Rozpoczynamy test połączenia ze ScraperAPI...\n")
    
    scraper = ScraperEngine()
    
    # Testowy URL (używamy serwisu zwracającego IP, aby sprawdzić rotację proxy)
    test_url = "https://httpbin.org/ip"
    
    result = await scraper.execute(test_url)
    
    print("=== WYNIK TESTU ===")
    if result.get("scraped_success"):
        print("✅ SUKCES! ScraperAPI nawiązał połączenie.")
        print(f"🔗 Przeprocesowany URL: {result.get('source_url')}")
        print("🎉 Twój klucz API działa prawidłowo!")
    else:
        print("❌ BŁĄD POŁĄCZENIA:")
        print(result.get("error_details"))

if __name__ == "__main__":
    asyncio.run(test_connection())