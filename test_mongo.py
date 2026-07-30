# test_mongo.py
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings

async def test_db_connection():
    print("🔌 Łączenie z bazą MongoDB Atlas...")
    try:
        client = AsyncIOMotorClient(settings.MONGODB_URL)
        db = client[settings.DATABASE_NAME]
        
        # Ping bazy danych
        await client.admin.command('ping')
        print("✅ SUKCES! Połączenie z MongoDB Atlas działa poprawnie.")
        
        # Test zapisu i odczytu w kolekcji testowej
        test_collection = db["test_connection"]
        await test_collection.insert_one({"status": "ok", "project": "bezpiecznik.pl"})
        print("📝 Pomyślnie zapisano dokument testowy w bazie!")
        
        # Czyszczenie wpisu testowego
        await test_collection.delete_many({"project": "bezpiecznik.pl"})
        print("🧹 Wpis testowy usunięty. Baza danych jest gotowa do pracy.")
        
    except Exception as e:
        print("❌ BŁĄD POŁĄCZENIA Z BAZĄ MONGO:")
        print(e)

if __name__ == "__main__":
    asyncio.run(test_db_connection())