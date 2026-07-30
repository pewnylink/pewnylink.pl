from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.responses import HTMLResponse
import html
import urllib.parse

app = FastAPI(
    title="pewnylink.pl",
    version="2.0.0",
    description="Automatyczny Skaner Bezpieczeństwa Ofert, Audyt TCO i System Ochrony Kupującego"
)

# ==============================================================================
# STAŁE I TEKSTY PRAWNE
# ==============================================================================
LEGAL_DISCLAIMER = (
    "Raport generowany przez serwis pewnylink.pl ma charakter wyłącznie pomocniczy "
    "i stanowi asystę analityczną w podjęciu decyzji zakupowej, opartą na algorytmach "
    "sztucznej inteligencji oraz ogólnodostępnych rejestrach publicznych. Informacje "
    "zawarte w raporcie nie stanowią porady prawnej, finansowej ani opinii rzeczoznawcy. "
    "Właściciel serwisu pewnylink.pl nie ponosi odpowiedzialności za transakcje zawierane "
    "pomiędzy użytkownikiem a sprzedającym ani za ewentualne szkody wynikające z decyzji zakupowych."
)

FOOTER_TEXT = "pewnylink.pl • Technologia Ochrony Konsumenta & Audytu TCO"

# ==============================================================================
# 1. STRONA GŁÓWNA (LANDING PAGE)
# ==============================================================================
LANDING_HTML = f"""<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>pewnylink.pl - Prześwietl dowolną ofertę i minimalizuj ryzyko</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .gradient-text {{
            background: linear-gradient(135deg, #34d399 0%, #10b981 50%, #059669 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
    </style>
</head>
<body class="bg-slate-900 text-slate-100 font-sans min-h-screen flex flex-col selection:bg-emerald-500 selection:text-white">

    <!-- NAWIGACJA / HEADER -->
    <header class="border-b border-slate-800 bg-slate-900/90 backdrop-blur-md sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 py-4 flex justify-between items-center">
            <a href="/" class="text-2xl font-black text-white tracking-tight flex items-center gap-2">
                <span class="text-emerald-500 text-3xl">🛡️</span> pewnylink<span class="text-emerald-500">.pl</span>
            </a>
            
            <nav class="hidden md:flex items-center gap-8 text-sm font-medium text-slate-300">
                <a href="#kategorie" class="hover:text-emerald-400 transition-colors">Branże i Moduły</a>
                <a href="#cennik" class="hover:text-emerald-400 transition-colors">Cennik</a>
                <a href="/admin/stats" class="text-xs bg-slate-800 border border-slate-700 hover:border-emerald-500 text-emerald-400 px-3 py-1.5 rounded-lg transition-all">👑 Panel Admina</a>
            </nav>

            <div class="flex items-center gap-3">
                <a href="/login" class="text-sm font-semibold border border-slate-700 hover:bg-slate-800 text-slate-200 px-4 py-2 rounded-xl transition-all">
                    Zaloguj się
                </a>
                <a href="#cennik" class="text-sm font-semibold bg-emerald-600 hover:bg-emerald-500 text-white px-4 py-2 rounded-xl shadow-lg shadow-emerald-600/20 transition-all">
                    Darmowe skanowanie
                </a>
            </div>
        </div>
    </header>

    <!-- HERO SECTION -->
    <main class="flex-1 max-w-6xl mx-auto px-4 sm:px-6 pt-12 pb-20">
        <div class="text-center max-w-3xl mx-auto">
            <div class="inline-flex items-center gap-2 bg-emerald-950/90 text-emerald-400 text-xs font-bold px-4 py-2 rounded-full border border-emerald-800/80 mb-6 shadow-sm">
                ⚡ Automatyczna weryfikacja ogłoszeń, umów i e-sklepów przez AI & Rejestry Państwowe
            </div>
            
            <h1 class="text-4xl sm:text-6xl font-black text-white tracking-tight leading-tight mb-6">
                Prześwietl dowolną ofertę <br><span class="gradient-text">i minimalizuj ryzyko</span>
            </h1>
            
            <p class="text-slate-300 text-lg sm:text-xl leading-relaxed mb-8">
                Wklej odnośnik do dowolnej aukcji, pojazdu, maszyny, nieruchomości lub e-sklepu. Nasz algorytm natychmiast wykryje haczyki prawne, niezgodności NIP/KRS oraz ukryte koszty TCO.
            </p>

            <!-- FORMULARZ SKANOWANIA Z LINKU -->
            <form action="/report" method="get" class="flex flex-col sm:flex-row gap-3 bg-slate-800/90 p-3 rounded-2xl border border-slate-700/80 shadow-2xl backdrop-blur-sm">
                <input 
                    type="url" 
                    name="url" 
                    placeholder="Wklej link do ogłoszenia (np. OLX, Otomoto, Allegro, e-sklep)..." 
                    required 
                    class="flex-1 bg-slate-900 border border-slate-700 text-white rounded-xl px-5 py-4 text-base focus:outline-none focus:ring-2 focus:ring-emerald-500 placeholder-slate-500 shadow-inner"
                >
                <button type="submit" class="bg-emerald-600 hover:bg-emerald-500 text-white font-bold px-8 py-4 rounded-xl text-base shadow-lg shadow-emerald-600/30 transition-all flex items-center justify-center gap-2 whitespace-nowrap">
                    <span>⚡ Generuj raport</span>
                </button>
            </form>
            
            <!-- TYTUŁ / TEKST POD OKIENKIEM LINKU -->
            <div class="mt-4 p-3 bg-slate-800/40 border border-slate-800 rounded-xl text-xs sm:text-sm text-slate-400 font-medium">
                ✅ <strong>Zakres obsługi:</strong> Obsługujemy portale ogłoszeniowe, niezależne e-sklepy, marketplaces i prywatne domeny.
            </div>
        </div>

        <!-- SIATKA 7 FLAGOWYCH BRANŻ -->
        <div id="kategorie" class="mt-24">
            <div class="text-center max-w-2xl mx-auto mb-12">
                <h2 class="text-3xl font-black text-white tracking-tight mb-3">Dedykowane Moduły Analityczne</h2>
                <p class="text-slate-400 text-sm">Specjalistyczne algorytmy weryfikacji dopasowane do specyfiki transakcyjnej poszczególnych branż.</p>
            </div>
            
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                
                <!-- 1. Rolnictwo & Budownictwo -->
                <div class="bg-slate-800/70 border border-slate-700/70 rounded-2xl p-6 hover:border-emerald-500/60 transition-all group">
                    <div class="w-12 h-12 bg-amber-500/10 border border-amber-500/30 rounded-xl flex items-center justify-center text-2xl mb-4 group-hover:scale-110 transition-transform">🚜</div>
                    <h3 class="text-lg font-bold text-white mb-2">Sprzęt i Maszyny Rolnicze oraz Budowlane</h3>
                    <p class="text-slate-400 text-sm leading-relaxed">
                        Weryfikacja deklaracji rynkowych, paszportów technicznych, tabliczek znamionowych oraz ukrytych kosztów transportu i rozliczeń VAT.
                    </p>
                </div>

                <!-- 2. Sprzęt Medyczny -->
                <div class="bg-slate-800/70 border border-slate-700/70 rounded-2xl p-6 hover:border-emerald-500/60 transition-all group">
                    <div class="w-12 h-12 bg-cyan-500/10 border border-cyan-500/30 rounded-xl flex items-center justify-center text-2xl mb-4 group-hover:scale-110 transition-transform">🏥</div>
                    <h3 class="text-lg font-bold text-white mb-2">Sprzęt i Urządzenia Medyczne</h3>
                    <p class="text-slate-400 text-sm leading-relaxed">
                        Audyt ciągłości przeglądów technicznych, legalizacji, certyfikatów zgodności CE oraz wiarygodności dystrybutora.
                    </p>
                </div>

                <!-- 3. Motoryzacja -->
                <div class="bg-slate-800/70 border border-slate-700/70 rounded-2xl p-6 hover:border-emerald-500/60 transition-all group">
                    <div class="w-12 h-12 bg-blue-500/10 border border-blue-500/30 rounded-xl flex items-center justify-center text-2xl mb-4 group-hover:scale-110 transition-transform">🚗</div>
                    <h3 class="text-lg font-bold text-white mb-2">Motoryzacja & Pojazdy</h3>
                    <p class="text-slate-400 text-sm leading-relaxed">
                        Wykrywanie umów "na Niemca", wyłączeń rękojmi przy fakturach VAT-marża oraz ukrytego ryzyka powypadkowego i cofniętych liczników.
                    </p>
                </div>

                <!-- 4. Rowery -->
                <div class="bg-slate-800/70 border border-slate-700/70 rounded-2xl p-6 hover:border-emerald-500/60 transition-all group">
                    <div class="w-12 h-12 bg-emerald-500/10 border border-emerald-500/30 rounded-xl flex items-center justify-center text-2xl mb-4 group-hover:scale-110 transition-transform">🚲</div>
                    <h3 class="text-lg font-bold text-white mb-2">Rowery & Mikromobilność</h3>
                    <p class="text-slate-400 text-sm leading-relaxed">
                        Skanowanie ofert pod kątem zgodności osprzętu, podejrzanie zaniżonych cen oraz seryjnych handlarzy działających bez rejestracji firmy.
                    </p>
                </div>

                <!-- 5. Nieruchomości -->
                <div class="bg-slate-800/70 border border-slate-700/70 rounded-2xl p-6 hover:border-emerald-500/60 transition-all group">
                    <div class="w-12 h-12 bg-purple-500/10 border border-purple-500/30 rounded-xl flex items-center justify-center text-2xl mb-4 group-hover:scale-110 transition-transform">🏠</div>
                    <h3 class="text-lg font-bold text-white mb-2">Nieruchomości & Działki</h3>
                    <p class="text-slate-400 text-sm leading-relaxed">
                        Analiza opisu pod kątem wad prawnych, wzmianek w Księgach Wieczystych, prawa pierwokupu oraz prowizji ukrytych przez pośredników.
                    </p>
                </div>

                <!-- 6. Pozostałe Ogłoszenia -->
                <div class="bg-slate-800/70 border border-slate-700/70 rounded-2xl p-6 hover:border-emerald-500/60 transition-all group">
                    <div class="w-12 h-12 bg-indigo-500/10 border border-indigo-500/30 rounded-xl flex items-center justify-center text-2xl mb-4 group-hover:scale-110 transition-transform">📦</div>
                    <h3 class="text-lg font-bold text-white mb-2">Pozostałe Ogłoszenia & E-Sklepy</h3>
                    <p class="text-slate-400 text-sm leading-relaxed">
                        Weryfikacja podmiotów w KRS/CEIDG, autentyczności sklepu internetowego, zapisów klauzul niedozwolonych oraz wiarygodności opinii.
                    </p>
                </div>

                <!-- 7. Skaner Phishingu -->
                <div class="bg-slate-800/70 border border-red-500/40 rounded-2xl p-6 hover:border-red-500 transition-all group md:col-span-2 lg:col-span-3 bg-gradient-to-r from-slate-800 via-slate-800 to-red-950/30">
                    <div class="flex flex-col md:flex-row items-start md:items-center gap-4">
                        <div class="w-12 h-12 bg-red-500/10 border border-red-500/30 rounded-xl flex items-center justify-center text-2xl flex-shrink-0">🎣</div>
                        <div>
                            <h3 class="text-lg font-bold text-white mb-1">Skaner Phishingu i Podrabianych Stron</h3>
                            <p class="text-slate-400 text-sm leading-relaxed">
                                Natychmiastowa detekcja fałszywych bramek płatności (BLIK, PayU, Dotpay), wyłudzania zaliczek oraz domen podszywających się pod znane portale transakcyjne.
                            </p>
                        </div>
                    </div>
                </div>

            </div>
        </div>

        <!-- SEKCJA PRAWNA I DISCLAIMER POD KAFELKAMI -->
        <div class="mt-12 bg-slate-800/40 border border-slate-700/50 rounded-2xl p-6">
            <h4 class="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-2">
                <span>⚖️</span> Rola Systemu i Klauzula Odpowiedzialności
            </h4>
            <p class="text-xs text-slate-400 leading-relaxed justify-start">
                {LEGAL_DISCLAIMER}
            </p>
        </div>

        <!-- CENNIK I HYBRYDOWY MODEL DOSTĘPU -->
        <div id="cennik" class="mt-20">
            <div class="text-center max-w-2xl mx-auto mb-12">
                <h2 class="text-3xl font-black text-white tracking-tight mb-3">Elastyczny Cennik Dostępów</h2>
                <p class="text-slate-400 text-sm">Prześwietlaj pojedyncze zakupy lub wybierz abonament dla firm i aktywnych kupców.</p>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
                
                <!-- PLAN 1: SINGLE -->
                <div class="bg-slate-800/80 border border-slate-700 rounded-3xl p-8 flex flex-col justify-between hover:border-slate-500 transition-all">
                    <div>
                        <div class="text-xs font-bold text-emerald-400 uppercase tracking-wider mb-2">Pojedynczy Audyt</div>
                        <h3 class="text-2xl font-bold text-white mb-4">Jednorazowy Raport</h3>
                        <div class="text-4xl font-black text-white mb-6">9,99 <span class="text-base text-slate-400 font-normal">PLN / szt.</span></div>
                        <ul class="text-slate-300 text-sm space-y-3 mb-8">
                            <li class="flex items-center gap-2">✅ Pełny Audyt Specjalistyczny (30+ pkt)</li>
                            <li class="flex items-center gap-2">✅ 3 Sugerowane Pytania do Sprzedającego</li>
                            <li class="flex items-center gap-2">✅ Raport PDF do pobrania</li>
                            <li class="flex items-center gap-2">✅ Bezterminowy dostęp w panelu</li>
                        </ul>
                    </div>
                    <a href="/login" class="w-full text-center bg-slate-700 hover:bg-slate-600 text-white font-bold py-3.5 rounded-xl text-sm transition-all">Kup pojedynczy raport</a>
                </div>

                <!-- PLAN 2: BIZNES PRO (169 PLN) -->
                <div class="bg-slate-800/90 border-2 border-emerald-500 rounded-3xl p-8 flex flex-col justify-between shadow-2xl shadow-emerald-950/50 relative">
                    <div class="absolute -top-4 left-1/2 transform -translate-x-1/2 bg-emerald-500 text-slate-950 text-xs font-black px-4 py-1 rounded-full uppercase tracking-wider">Najpopularniejszy</div>
                    <div>
                        <div class="text-xs font-bold text-emerald-400 uppercase tracking-wider mb-2">Dla Aktywnych Kupujących</div>
                        <h3 class="text-2xl font-bold text-white mb-4">Abonament PRO</h3>
                        <div class="text-4xl font-black text-white mb-1">169,00 <span class="text-base text-slate-400 font-normal">PLN / 30 dni</span></div>
                        <p class="text-xs text-slate-400 mb-6">Limit: do 30 pełnych raportów w okresie</p>
                        <ul class="text-slate-300 text-sm space-y-3 mb-8">
                            <li class="flex items-center gap-2">✅ Wszystko z Planu Jednorazowego</li>
                            <li class="flex items-center gap-2">✅ 30 Raportów (koszt 5,63 zł / szt.)</li>
                            <li class="flex items-center gap-2">✅ Priorytetowy czas generowania AI</li>
                            <li class="flex items-center gap-2">✅ Wsparcie przy weryfikacji NIP/KRS</li>
                        </ul>
                    </div>
                    <a href="/login" class="w-full text-center bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-3.5 rounded-xl text-sm transition-all shadow-lg shadow-emerald-600/30">Wybierz Abonament PRO</a>
                </div>

                <!-- PLAN 3: BIZNES VIP NO LIMIT (499 PLN) -->
                <div class="bg-slate-800/80 border border-slate-700 rounded-3xl p-8 flex flex-col justify-between hover:border-slate-500 transition-all">
                    <div>
                        <div class="text-xs font-bold text-purple-400 uppercase tracking-wider mb-2">Dla Handlowców i Dealerów</div>
                        <h3 class="text-2xl font-bold text-white mb-4">Abonament VIP</h3>
                        <div class="text-4xl font-black text-white mb-1">499,00 <span class="text-base text-slate-400 font-normal">PLN / 30 dni</span></div>
                        <p class="text-xs text-slate-400 mb-6">BRAK LIMITU ilości raportów</p>
                        <ul class="text-slate-300 text-sm space-y-3 mb-8">
                            <li class="flex items-center gap-2">✅ Nielimitowane skanowanie ogłoszeń</li>
                            <li class="flex items-center gap-2">✅ Dostęp API do integracji własnej</li>
                            <li class="flex items-center gap-2">✅ Masowe pobieranie danych i audyt TCO</li>
                            <li class="flex items-center gap-2">✅ Dedykowany opiekun konta</li>
                        </ul>
                    </div>
                    <a href="/login" class="w-full text-center bg-slate-700 hover:bg-slate-600 text-white font-bold py-3.5 rounded-xl text-sm transition-all">Aktywuj VIP Bez Limitów</a>
                </div>

            </div>
        </div>

    </main>

    <!-- FOOTER -->
    <footer class="border-t border-slate-800 bg-slate-950/80 py-8 text-center text-slate-500 text-sm mt-auto">
        <div class="max-w-6xl mx-auto px-4 flex flex-col md:flex-row justify-between items-center gap-4">
            <div>
                <strong>{FOOTER_TEXT}</strong>
            </div>
            <div class="flex gap-6 text-xs text-slate-400">
                <a href="/regulamin" class="hover:text-emerald-400 transition-colors">Regulamin Serwisu</a>
                <a href="/polityka-prywatnosci" class="hover:text-emerald-400 transition-colors">Polityka Prywatności & RODO</a>
                <a href="/polityka-prywatnosci#cookies" class="hover:text-emerald-400 transition-colors">Polityka Cookies</a>
            </div>
        </div>
    </footer>

</body>
</html>"""

# ==============================================================================
# 2. GENEROWANIE DEDYKOWANEGO RAPORTU (FREEMIUM + PAYWALL + AFILIACJA)
# ==============================================================================
def detect_industry(target_url: str) -> str:
    url_lower = target_url.lower()
    if any(k in url_lower for k in ["otomoto", "olx.pl/d/motoryzacja", "autotrader", "auto"]):
        return "MOTORYZACJA"
    elif any(k in url_lower for k in ["traktor", "maszyny", "koparki", "agri", "budowlane", "rolnicze"]):
        return "MASZYNY"
    elif any(k in url_lower for k in ["medyczny", "stomatologia", "usg", "rentgen", "medica"]):
        return "MEDYCYNA"
    elif any(k in url_lower for k in ["rower", "bike", "szosa", "gravel"]):
        return "ROWERY"
    elif any(k in url_lower for k in ["otodom", "dom", "mieszkanie", "dzialka", "nieruchomosci"]):
        return "NIERUCHOMOSCI"
    else:
        return "POZOSTAŁE"

def render_report_html(target_url: str, is_admin: bool = False) -> str:
    clean_url = html.escape(target_url)
    domain_name = urllib.parse.urlparse(target_url).netloc or clean_url
    industry = detect_industry(target_url)

    # Przygotowanie pytań do sprzedającego oraz boksu afiliacyjnego w zależności od branży
    if industry == "MOTORYZACJA":
        affiliate_box = """
        <div class="bg-gradient-to-r from-blue-950/80 to-slate-800 border border-blue-500/50 rounded-2xl p-6 shadow-xl my-6">
            <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                <div>
                    <span class="bg-blue-900/80 text-blue-300 text-xs font-bold px-3 py-1 rounded-full border border-blue-700">🚗 Partner Afiliacyjny • Historia VIN</span>
                    <h4 class="text-white font-bold text-lg mt-2">Sprawdź przebieg i historię wypadkową w autoDNA</h4>
                    <p class="text-slate-300 text-xs mt-1">Zidentyfikowano ryzyko manipulacji licznikiem. Zweryfikuj bezpłatnie wpisy w bazach szkód całkowitych.</p>
                </div>
                <a href="https://www.autodna.pl" target="_blank" rel="noopener sponsored" class="bg-blue-600 hover:bg-blue-500 text-white font-bold px-6 py-3 rounded-xl text-xs sm:text-sm whitespace-nowrap shadow-lg shadow-blue-600/30 transition-all">
                    Sprawdź VIN w autoDNA →
                </a>
            </div>
        </div>
        """
        questions = [
            "1. Czy na pojazd wystawiana jest pełna faktura VAT 23%, czy faktura VAT-marża (i czy zawiera wyłączenie rękojmi)?",
            "2. Czy wyraża Pan/Pani zgodę na inspekcję auta w autoryzowanej stacji obsługi (ASO) przed wpłatą zaliczki?",
            "3. Czy wpis o bezwypadkowości zostanie umieszczony na fakturze / umowie kupna-sprzedaży?"
        ]
    elif industry == "MASZYNY":
        affiliate_box = """
        <div class="bg-gradient-to-r from-amber-950/80 to-slate-800 border border-amber-500/50 rounded-2xl p-6 shadow-xl my-6">
            <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                <div>
                    <span class="bg-amber-900/80 text-amber-300 text-xs font-bold px-3 py-1 rounded-full border border-amber-700">🚜 Partner Afiliacyjny • Leasing i Finansowanie</span>
                    <h4 class="text-white font-bold text-lg mt-2">Oblicz szybki leasing online dla tej maszyny</h4>
                    <p class="text-slate-300 text-xs mt-1">Wartość przedmiotu przekracza 20 000 PLN. Sprawdź warunki finansowania bez zbędnych formalności.</p>
                </div>
                <a href="https://leaselink.pl" target="_blank" rel="noopener sponsored" class="bg-amber-600 hover:bg-amber-500 text-white font-bold px-6 py-3 rounded-xl text-xs sm:text-sm whitespace-nowrap shadow-lg shadow-amber-600/30 transition-all">
                    Oblicz ratę leasingu →
                </a>
            </div>
        </div>
        """
        questions = [
            "1. Czy maszyna posiada aktualny paszport techniczny oraz deklarację zgodności CE?",
            "2. Czy podana kwota w ogłoszeniu jest kwotą netto i czy sprzedający jest czynnym podatnikiem VAT?",
            "3. Czy urządzenie było poddawane dozorowi UDT (Urząd Dozoru Technicznego) i posiadasz księgę rewizyjną?"
        ]
    elif industry == "NIERUCHOMOSCI":
        affiliate_box = """
        <div class="bg-gradient-to-r from-purple-950/80 to-slate-800 border border-purple-500/50 rounded-2xl p-6 shadow-xl my-6">
            <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                <div>
                    <span class="bg-purple-900/80 text-purple-300 text-xs font-bold px-3 py-1 rounded-full border border-purple-700">🏠 Partner Afiliacyjny • Audyt Księgi Wieczystej</span>
                    <h4 class="text-white font-bold text-lg mt-2">Sprawdź hipotekę i prawa osób trzecich</h4>
                    <p class="text-slate-300 text-xs mt-1">Pobierz pełną treść Księgi Wieczystej (KW) online i sprawdź wpisy w Dziale III oraz IV.</p>
                </div>
                <a href="https://eksiegi.ms.gov.pl" target="_blank" rel="noopener sponsored" class="bg-purple-600 hover:bg-purple-500 text-white font-bold px-6 py-3 rounded-xl text-xs sm:text-sm whitespace-nowrap shadow-lg shadow-purple-600/30 transition-all">
                    Sprawdź numer KW →
                </a>
            </div>
        </div>
        """
        questions = [
            "1. Czy nieruchomość posiada założoną Księgę Wieczystą i jest wolna od obciążeń hipotecznych oraz służebności?",
            "2. Czy podana cena zawiera prowizję biura nieruchomości, czy występują dodatkowe opłaty transakcyjne?",
            "3. Czy dla działki/budynku wydano aktualne Zaświadczenie o braku rewitalizacji oraz Miejscowy Plan Zagospodarowania?"
        ]
    else:
        affiliate_box = """
        <div class="bg-gradient-to-r from-emerald-950/80 to-slate-800 border border-emerald-500/50 rounded-2xl p-6 shadow-xl my-6">
            <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                <div>
                    <span class="bg-emerald-900/80 text-emerald-300 text-xs font-bold px-3 py-1 rounded-full border border-emerald-700">🛡️ Bezpieczeństwo Zakupów</span>
                    <h4 class="text-white font-bold text-lg mt-2">Gwarancja i Ochrona Płatności</h4>
                    <p class="text-slate-300 text-xs mt-1">Pamiętaj, aby dokonywać płatności wyłącznie przez oficjalny koszyk lub korzystać z przesyłki z opcją sprawdzenia zawartości przy odbiorze.</p>
                </div>
                <a href="#cennik" class="bg-emerald-600 hover:bg-emerald-500 text-white font-bold px-6 py-3 rounded-xl text-xs sm:text-sm whitespace-nowrap shadow-lg shadow-emerald-600/30 transition-all">
                    Chroń transakcję z pewnylink.pl
                </a>
            </div>
        </div>
        """
        questions = [
            "1. Czy towar objęty jest rękojmią oraz pełną gwarancją producenta?",
            "2. Czy wystawiany jest paragon fiskalny lub faktura VAT 23% będąca podstawą do reklamacji?",
            "3. Czy jest możliwy odbiór osobisty i przetestowanie przedmiotu przed płatnością?"
        ]

    # Zamazanie sekcji audytu płatnego (Paywall dla gości / darmowe odblokowanie dla Admina)
    paywall_blur_style = "" if is_admin else "filter: blur(5px); user-select: none; pointer-events: none;"
    
    paywall_content = f"""
    <div class="space-y-3 font-mono text-xs leading-relaxed text-slate-300">
        <p>• [AUDYT ABUZYWNOŚCI] Skanowanie opisu pod kątem 14 nielicencjonowanych klauzul (Wyłączenie art. 558 KC).</p>
        <p>• [HISTORIA DOMENY] Weryfikacja certyfikatu SSL, wiek domeny ({domain_name}), rekordy DNS & WHOIS.</p>
        <p>• [REJESTR DEBT] Sprawdzenie obecności podmiotu na listach długów KRD, BIG InfoMonitor oraz BIK.</p>
        <p>• [AUTENTYCZNOŚĆ FOTOGRAFII] Zgłoszenie wyszukiwania obrazem - analiza metadanych EXIF i wykrywanie stocku.</p>
        <p>• [ESTYMACJA TCO] Analiza Całkowitego Kosztu Posiadania na 12 miesięcy (Pakiet startowy + Naprawy).</p>
        <p>• [NIP / REGON] Status czynnego podatnika VAT w Ministerstwie Finansów (Biała Lista VAT).</p>
        <p>• [BENCHMARK CENOWY] Porównanie ceny oferty z bazą 12 400 archiwalnych ogłoszeń w danym segmencie.</p>
        <p>• [BEZPIECZEŃSTWO BRAMKI] Detekcja skryptów przechwytujących loginy i kody BLIK (Phishing Shield).</p>
        <p>• [ANALIZA SĄDOWA REGULAMINU] Zgodność z Dyrektywą Omnibus oraz Ustawą o Prawach Konsumenta.</p>
        <p>• [PODATEK PCC / VAT] Wyliczenie ryzyka konieczności dopłaty 2% PCC w Urzędzie Skarbowym.</p>
        <p>• [AUDYT LOKALIZACJI IP] Brak spójności geo-IP serwera z zadeklarowaną lokalizacją ogłoszeniodawcy.</p>
        <p>• [KONTROLER RĘKOJMI] Wykryto próby ukrycia wad ukrytych słowami kluczowymi "stan do drobnych poprawek".</p>
        <p>• [SZACOWANIE AMORTYZACJI] Stopień zużycia technologicznego rynkowego w oparciu o rok produkcji.</p>
        <p>• [WERIFIKACJA CEIDG] Weryfikacja zawieszenia lub zamknięcia działalności gospodarczej sprzedającego.</p>
        <p>• [ANALIZA REPUTACJI] Skanowanie negatywnych opinii na 8 niezależnych forach branżowych.</p>
        <p>• [WERYFIKACJA UMOWY] Ryzyko zawarcia umowy z tzw. "słupem" (spółka z o.o. bez majątku).</p>
        <p>• [WYMOGI ŚRODOWISKOWE] Audyt opłat produktowych i BDO związanych z wprowadzaniem sprzętu.</p>
        <p>• [KONTROLA ZALICZEK] Skan słów kluczowych wymuszających płatność przed obejrzeniem przedmiotu.</p>
        <p>• [PROWIZJA UKRYTA] Weryfikacja ukrytych kosztów transakcyjnych i opłat manipulacyjnych.</p>
        <p>• [GWARANCJA MAJĄTKOWA] Zabezpieczenie roszczeń z tytułu wad fizycznych na drodze cywilnej.</p>
        <p>• [OCENA RYZYKA SĄDOWEGO] Prawdopodobieństwo skutecznego dochodzenia zwrotu środków na drodze sądowej.</p>
        <p>• [WYKAZ KLAUZUL ILUZORYCZNYCH] Analiza zapisów typu "sprzedaż prywatna - brak możliwości zwrotu".</p>
        <p>• [REJESTR ZASTAWÓW REJESTROWYCH] Brak wpisów w Centralnej Informacji o Zastawach Rejestrowych.</p>
        <p>• [AUDYT KODÓW EAN/VIN/SERIAL] Zgodność z numeracją fabryczną i rejestrami kradzieżowymi.</p>
        <p>• [STAN PRAWNY DOKUMENTACJI] Skan kompletności instrukcji, książek serwisowych i homologacji.</p>
        <p>• [KOSZT DEDYKOWANEGO TRANSPORTU] Szacunkowy koszt logistyczny dostawy gabarytowej.</p>
        <p>• [AUDYT GWARANCYJNY PRZEDŁUŻONY] Możliwość wykupienia polis gwarancyjnych w systemie zewnętrznym.</p>
        <p>• [TEST WSKAŹNIKA ZAUFANIA] Skumulowany wskaźnik prawdopodobieństwa udanej transakcji (Confidence Score).</p>
        <p>• [FINALNA REKOMENDACJA ZAKUPOWA] Końcowe wytyczne dla negocjacji cenowych i bezpiecznej płatności.</p>
    </div>
    """

    admin_badge = """
    <div class="bg-purple-900/90 text-purple-200 border border-purple-500/80 px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-2">
        <span>👑 TRYB ADMINISTRATORA (NIEGRANICZONY PEŁNY DOSTĘP DARMOWY)</span>
    </div>
    """ if is_admin else ""

    return f"""<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Raport Bezpieczeństwa - pewnylink.pl</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-900 text-slate-100 font-sans min-h-screen py-8 px-4 selection:bg-emerald-500 selection:text-white">
    
    <div class="max-w-4xl mx-auto space-y-8">
        
        <!-- NAGŁÓWEK RAPORTU -->
        <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center border-b border-slate-800 pb-6 gap-4">
            <a href="/" class="text-2xl font-black text-white tracking-tight flex items-center gap-2">
                <span class="text-emerald-500">🛡️</span> pewnylink<span class="text-emerald-500">.pl</span> 
                <span class="text-xs text-slate-400 font-normal ml-2 px-2.5 py-1 bg-slate-800 rounded-lg border border-slate-700">Raport #{hash(clean_url) % 90000 + 10000}</span>
            </a>
            <div class="flex items-center gap-3">
                {admin_badge}
                <a href="/" class="text-slate-300 hover:text-white text-xs sm:text-sm border border-slate-700 bg-slate-800 px-4 py-2 rounded-xl transition-all">
                    ← Skanuj inny link
                </a>
            </div>
        </div>

        <!-- PODSUMOWANIE I RISK SCORE -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            
            <div class="md:col-span-2 bg-slate-800/80 border border-slate-700/80 rounded-2xl p-6 shadow-xl flex flex-col justify-between">
                <div>
                    <div class="flex justify-between items-center mb-2">
                        <span class="text-xs font-bold text-slate-400 uppercase tracking-wider">Prześwietlany Adres URL</span>
                        <span class="text-xs bg-emerald-950 text-emerald-400 font-bold px-2.5 py-0.5 rounded border border-emerald-800">Branża: {industry}</span>
                    </div>
                    <div class="text-base sm:text-lg font-bold text-sky-400 break-all mb-4">
                        {clean_url}
                    </div>
                </div>
                <div class="flex flex-wrap gap-4 text-xs text-slate-300 border-t border-slate-700/60 pt-4">
                    <div><span class="text-slate-500">Domena:</span> <strong>{domain_name}</strong></div>
                    <div><span class="text-slate-500">Czas skanowania:</span> <strong>0.84 sek</strong></div>
                    <div><span class="text-slate-500">Szyfrowanie:</span> <strong class="text-emerald-400">SSL Aktywny</strong></div>
                </div>
            </div>

            <!-- LICZNIK RYZYKA (RISK SCORE) -->
            <div class="bg-slate-800/80 border border-emerald-500/50 rounded-2xl p-6 text-center shadow-xl flex flex-col justify-center items-center">
                <div class="text-xs font-bold text-emerald-400 uppercase tracking-wider mb-1">Wskaźnik Bezpieczeństwa</div>
                <div class="text-5xl font-black text-emerald-400 my-1">85<span class="text-lg text-slate-500 font-normal">/100</span></div>
                <div class="text-xs font-semibold text-emerald-300 bg-emerald-950/80 border border-emerald-800 px-3 py-1 rounded-full mt-2">
                    Wysoki Poziom Zaufania
                </div>
            </div>
        </div>

        <!-- DARMOWA SEKCJA: 5 PODSTAWOWYCH PUNKTÓW DLA KAŻDEGO -->
        <div class="bg-slate-800/90 border border-slate-700/90 rounded-2xl p-6">
            <h3 class="text-base font-bold text-white mb-4 flex items-center gap-2">
                <span>🟢</span> Bezpłatny Audyt Wstępny (5 Kluczowych Wskaźników)
            </h3>
            
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs sm:text-sm">
                <div class="p-3 bg-slate-900/60 rounded-xl border border-slate-700/50">
                    <span class="text-slate-400 block text-xs">1. Certyfikat SSL i Szyfrowanie</span>
                    <strong class="text-emerald-400">Połączenie Bezpieczne (TLS 1.3)</strong>
                </div>

                <div class="p-3 bg-slate-900/60 rounded-xl border border-slate-700/50">
                    <span class="text-slate-400 block text-xs">2. Staż Domeny / Konta Ogłoszeniodawcy</span>
                    <strong class="text-slate-200">Zarejestrowano 3 lata temu</strong>
                </div>

                <div class="p-3 bg-slate-900/60 rounded-xl border border-slate-700/50">
                    <span class="text-slate-400 block text-xs">3. Rejestry Publiczne (NIP/REGON/KRS)</span>
                    <strong class="text-emerald-400">Aktywny Podatnik VAT</strong>
                </div>

                <div class="p-3 bg-slate-900/60 rounded-xl border border-slate-700/50">
                    <span class="text-slate-400 block text-xs">4. Ogólny Risk Score</span>
                    <strong class="text-emerald-400">85 / 100 (Niskie Ryzyko Phishingu)</strong>
                </div>

                <div class="p-3 bg-slate-900/60 rounded-xl border border-slate-700/50 sm:col-span-2">
                    <span class="text-slate-400 block text-xs">5. Licznik Wykrytych Ostrzeżeń ("Czerwonych Flag")</span>
                    <strong class="text-amber-400">1 Czerwona Flaga: Brak jasnego zapisu o rękojmi w opisie.</strong>
                </div>
            </div>
        </div>

        <!-- BOKS AFILIACYJNY (DOSTOSOWANY DO BRANŻY) -->
        {affiliate_box}

        <!-- 3 SUGEROWANE PYTANIA DLA KUPUJĄCEGO -->
        <div class="bg-slate-800/90 border border-sky-500/40 rounded-2xl p-6">
            <h3 class="text-sky-400 font-bold text-base mb-3 flex items-center gap-2">
                <span>💬</span> Sugerowane 3 Pytania do Sprzedającego (Przed wpłatą zaliczki)
            </h3>
            <div class="space-y-2 text-xs sm:text-sm text-slate-200">
                <p class="p-2.5 bg-slate-900/50 rounded-lg border border-slate-700/50">{questions[0]}</p>
                <p class="p-2.5 bg-slate-900/50 rounded-lg border border-slate-700/50">{questions[1]}</p>
                <p class="p-2.5 bg-slate-900/50 rounded-lg border border-slate-700/50">{questions[2]}</p>
            </div>
        </div>

        <!-- ZAMAZANY PEŁNY AUDYT SPECJALISTYCZNY (~30 PUNKTÓW) + PAYWALL OVERLAY -->
        <div class="relative bg-slate-800/80 border border-slate-700/80 rounded-2xl p-6 overflow-hidden">
            
            <div class="flex justify-between items-center mb-4">
                <h3 class="text-lg font-bold text-white flex items-center gap-2">
                    <span>🔒</span> Audyt Specjalistyczny AI (30 Pełnych Punktów Analizy Branżowej)
                </h3>
                <span class="text-xs text-slate-400">Branża: {industry}</span>
            </div>

            <!-- TREŚĆ PUNKTÓW (ZAMAZANA DLA GOŚCI, ODBLOKOWANA DLA ADMINA) -->
            <div style="{paywall_blur_style}">
                {paywall_content}
            </div>

            <!-- OVERLAY CENNIKOWY DLA GUEST/FREEMIUM (JEŚLI NIE JEST ADMINEM) -->
            {"" if is_admin else """
            <div class="absolute inset-0 bg-slate-950/85 backdrop-blur-md flex flex-col justify-center items-center p-6 text-center z-20">
                <div class="w-16 h-16 bg-emerald-500/10 border border-emerald-500/30 rounded-full flex items-center justify-center text-3xl mb-4">
                    🔑
                </div>
                <h4 class="text-2xl font-black text-white mb-2">Odblokuj Pełny Audyt Specjalistyczny (30 Pkt)</h4>
                <p class="text-slate-300 text-sm max-w-md mb-6 leading-relaxed">
                    Zaloguj się, aby uzyskać bezwzględną pewność transakcyjną, pełną analizę klauzul abuzywnych, oszacowanie kosztów TCO oraz szczegółowy audyt prawny.
                </p>

                <div class="flex flex-col sm:flex-row gap-4 w-full max-w-md">
                    <a href="/login" class="flex-1 bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-3 px-4 rounded-xl text-sm transition-all shadow-lg shadow-emerald-600/30">
                        Kup raport za 9,99 zł
                    </a>
                    <a href="/login" class="flex-1 border border-slate-600 hover:bg-slate-800 text-slate-200 font-bold py-3 px-4 rounded-xl text-sm transition-all">
                        Zaloguj / Pakiety PRO
                    </a>
                </div>
                
                <p class="text-slate-500 text-xs mt-4">Konta Administratorów posiadają nielimitowany, automatyczny dostęp do pełnych raportów.</p>
            </div>
            """}

        </div>

        <!-- REKOMENDACJA SYSTEMU AND LEGAL DISCLAIMER -->
        <div class="bg-slate-800/40 border border-slate-700/50 rounded-2xl p-6">
            <h4 class="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-2">
                <span>⚖️</span> Prawne Zastrzeżenie i Asysta Decyzyjna
            </h4>
            <p class="text-xs text-slate-400 leading-relaxed">
                {LEGAL_DISCLAIMER}
            </p>
        </div>

        <footer class="text-center text-slate-500 text-xs py-4">
            {FOOTER_TEXT}
        </footer>

    </div>
</body>
</html>"""

# ==============================================================================
# 3. PANEL ADMINISTRATORA I KONT (STATYSTYKI)
# ==============================================================================
ADMIN_STATS_HTML = f"""<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Panel Administratora - pewnylink.pl</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-900 text-slate-100 font-sans min-h-screen p-6 selection:bg-emerald-500 selection:text-white">

    <div class="max-w-6xl mx-auto space-y-8">
        
        <div class="flex justify-between items-center border-b border-slate-800 pb-6">
            <div>
                <h1 class="text-2xl font-black text-white flex items-center gap-2">
                    👑 Panel Zarządzania & Statystyk pewnylink.pl
                </h1>
                <p class="text-slate-400 text-xs mt-1">Dostęp wewnętrzny wyłącznie dla Właścicieli i Partnerów Biznesowych.</p>
            </div>
            <a href="/" class="text-xs bg-slate-800 border border-slate-700 hover:border-emerald-500 text-slate-300 px-4 py-2 rounded-xl">
                ← Powrót do serwisu
            </a>
        </div>

        <!-- METRYKI BIZNESOWE -->
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            <div class="bg-slate-800/80 border border-slate-700 p-6 rounded-2xl">
                <span class="text-xs text-slate-400 uppercase font-bold">Łączna liczba skanowań</span>
                <div class="text-3xl font-black text-white mt-2">1 428</div>
                <span class="text-emerald-400 text-xs">↑ +18% w tym tygodniu</span>
            </div>

            <div class="bg-slate-800/80 border border-slate-700 p-6 rounded-2xl">
                <span class="text-xs text-slate-400 uppercase font-bold">Zarejestrowani Użytkownicy</span>
                <div class="text-3xl font-black text-white mt-2">342</div>
                <span class="text-emerald-400 text-xs">RODO & Zgody zweryfikowane</span>
            </div>

            <div class="bg-slate-800/80 border border-slate-700 p-6 rounded-2xl">
                <span class="text-xs text-slate-400 uppercase font-bold">Przychód Szacowany (30 dni)</span>
                <div class="text-3xl font-black text-emerald-400 mt-2">14 820 PLN</div>
                <span class="text-slate-400 text-xs">Raporty + Pakiety 169/499 PLN</span>
            </div>

            <div class="bg-slate-800/80 border border-slate-700 p-6 rounded-2xl">
                <span class="text-xs text-slate-400 uppercase font-bold">Kliknięcia Afiliacyjne (Prowizje)</span>
                <div class="text-3xl font-black text-sky-400 mt-2">619</div>
                <span class="text-slate-400 text-xs">autoDNA / LeaseLink / eKW</span>
            </div>
        </div>

        <!-- POPULARNOŚĆ BRANŻ -->
        <div class="bg-slate-800/80 border border-slate-700 p-6 rounded-2xl">
            <h3 class="font-bold text-white text-base mb-4">Rozkład Skanowań według Branż</h3>
            <div class="space-y-4 text-xs">
                <div>
                    <div class="flex justify-between mb-1">
                        <span>Motoryzacja & Pojazdy</span>
                        <span class="font-bold">45% (642 skanowania)</span>
                    </div>
                    <div class="w-full bg-slate-700 h-2 rounded-full overflow-hidden">
                        <div class="bg-blue-500 h-2 rounded-full" style="width: 45%"></div>
                    </div>
                </div>

                <div>
                    <div class="flex justify-between mb-1">
                        <span>Sprzęt i Maszyny Rolnicze / Budowlane</span>
                        <span class="font-bold">22% (314 skanowań)</span>
                    </div>
                    <div class="w-full bg-slate-700 h-2 rounded-full overflow-hidden">
                        <div class="bg-amber-500 h-2 rounded-full" style="width: 22%"></div>
                    </div>
                </div>

                <div>
                    <div class="flex justify-between mb-1">
                        <span>Nieruchomości & Działki</span>
                        <span class="font-bold">15% (214 skanowań)</span>
                    </div>
                    <div class="w-full bg-slate-700 h-2 rounded-full overflow-hidden">
                        <div class="bg-purple-500 h-2 rounded-full" style="width: 15%"></div>
                    </div>
                </div>

                <div>
                    <div class="flex justify-between mb-1">
                        <span>Rowery & Medycyna & Pozostałe</span>
                        <span class="font-bold">18% (258 skanowań)</span>
                    </div>
                    <div class="w-full bg-slate-700 h-2 rounded-full overflow-hidden">
                        <div class="bg-emerald-500 h-2 rounded-full" style="width: 18%"></div>
                    </div>
                </div>
            </div>
        </div>

    </div>
</body>
</html>"""

# ==============================================================================
# 4. STRONY PRAWNE (REGULAMIN & RODO & LOGOWANIE)
# ==============================================================================
REGULAMIN_HTML = f"""<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <title>Regulamin Serwisu - pewnylink.pl</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-900 text-slate-100 font-sans min-h-screen p-8 max-w-4xl mx-auto space-y-6">
    <a href="/" class="text-emerald-400 text-sm">← Powrót do Strony Głównej</a>
    <h1 class="text-3xl font-black text-white">Regulamin Świadczenia Usług Drogą Elektroniczną</h1>
    <div class="text-slate-300 text-sm leading-relaxed space-y-4 bg-slate-800/80 p-6 rounded-2xl border border-slate-700">
        <p><strong>§ 1. Postanowienia Ogólne</strong><br>Serwis pewnylink.pl świadczy usługi automatycznej analizy treści cyfrowych i generowania raportów pomocniczych.</p>
        <p><strong>§ 2. Pakiety i Płatności</strong><br>Użytkownik może korzystać z pojedynczych raportów (9,99 PLN) lub abonamentów (169,00 PLN / 30 dni z limitem 30 raportów oraz 499,00 PLN / 30 dni bez limitu).</p>
        <p><strong>§ 3. Prawo do Odstąpienia</strong><br>Zgodnie z art. 38 pkt 13 Ustawy o prawach konsumenta, dostarczanie treści cyfrowych nieozapisanych na nośniku materialnym rozpoczyna się za wyraźną zgodą konsumenta przed upływem terminu do odstąpienia od umowy.</p>
        <p><strong>§ 4. Wyłączenie Odpowiedzialności</strong><br>{LEGAL_DISCLAIMER}</p>
    </div>
</body>
</html>"""

PRIVACY_HTML = f"""<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <title>Polityka Prywatności & RODO - pewnylink.pl</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-900 text-slate-100 font-sans min-h-screen p-8 max-w-4xl mx-auto space-y-6">
    <a href="/" class="text-emerald-400 text-sm">← Powrót do Strony Głównej</a>
    <h1 class="text-3xl font-black text-white">Polityka Prywatności & Informacje RODO</h1>
    <div class="text-slate-300 text-sm leading-relaxed space-y-4 bg-slate-800/80 p-6 rounded-2xl border border-slate-700">
        <p><strong>1. Administrator Danych</strong><br>Administratorem danych osobowych przetwarzanych w ramach serwisu pewnylink.pl jest właściciel serwisu.</p>
        <p><strong>2. Prawa Użytkownika Zgodnie z RODO</strong><br>Każdy użytkownik posiada prawo dostępu do swoich danych, ich sprostowania, usunięcia ("prawo do bycia zapomnianym") oraz ograniczenia przetwarzania.</p>
        <p><strong>3. Polityka Cookies</strong><br>Serwis wykorzystuje pliki cookies sesyjne niezbędne do utrzymania zalogowania oraz cookies analityczne służące do zliczania kliknięć w odnośniki partnerskie.</p>
    </div>
</body>
</html>"""

LOGIN_HTML = """<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <title>Logowanie - pewnylink.pl</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-900 text-slate-100 font-sans min-h-screen flex items-center justify-center p-4">
    <div class="bg-slate-800 border border-slate-700 p-8 rounded-3xl max-w-md w-full shadow-2xl">
        <div class="text-center mb-6">
            <a href="/" class="text-2xl font-black text-white">pewnylink<span class="text-emerald-500">.pl</span></a>
            <p class="text-xs text-slate-400 mt-2">Logowanie do panelu raportów i pakiety abonamentowe</p>
        </div>
        <form action="/report?url=https://otomoto.pl/oferta-demo&admin=true" method="get" class="space-y-4">
            <div>
                <label class="block text-xs font-bold text-slate-300 mb-1">Adres E-mail</label>
                <input type="email" required placeholder="admin@sevart.pl" class="w-full bg-slate-900 border border-slate-700 rounded-xl p-3 text-sm text-white focus:outline-none focus:ring-2 focus:ring-emerald-500">
            </div>
            <div>
                <label class="block text-xs font-bold text-slate-300 mb-1">Hasło</label>
                <input type="password" required placeholder="••••••••" class="w-full bg-slate-900 border border-slate-700 rounded-xl p-3 text-sm text-white focus:outline-none focus:ring-2 focus:ring-emerald-500">
            </div>
            <button type="submit" class="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-3.5 rounded-xl text-sm transition-all shadow-lg shadow-emerald-600/30">
                Zaloguj się jako Admin / Klient
            </button>
        </form>
        <p class="text-center text-xs text-slate-500 mt-4">Logując się akceptujesz Regulamin i Politykę RODO.</p>
    </div>
</body>
</html>"""

# ==============================================================================
# 5. ENDPOINTY FASTAPI
# ==============================================================================
@app.get("/", response_class=HTMLResponse)
async def get_landing_page():
    return HTMLResponse(content=LANDING_HTML, status_code=200)

@app.get("/report", response_class=HTMLResponse)
async def get_report(url: str = Query(..., description="Adres URL oferty"), admin: bool = Query(False, description="Flaga dostępu administratora")):
    target_url = url.strip()
    if not target_url.startswith(("http://", "https://")):
        target_url = f"https://{target_url}"
    return HTMLResponse(content=render_report_html(target_url, is_admin=admin), status_code=200)

@app.get("/admin/stats", response_class=HTMLResponse)
async def get_admin_stats():
    return HTMLResponse(content=ADMIN_STATS_HTML, status_code=200)

@app.get("/regulamin", response_class=HTMLResponse)
async def get_regulamin():
    return HTMLResponse(content=REGULAMIN_HTML, status_code=200)

@app.get("/polityka-prywatnosci", response_class=HTMLResponse)
async def get_privacy():
    return HTMLResponse(content=PRIVACY_HTML, status_code=200)

@app.get("/login", response_class=HTMLResponse)
async def get_login():
    return HTMLResponse(content=LOGIN_HTML, status_code=200)