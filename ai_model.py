
import os
import time
from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("API anahtarı bulunamadı!")

client = genai.Client(api_key=api_key)


def yapay_zeka_cevap(soru: str):
    for deneme in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=soru
            )
            return response.text

        except Exception as hata:
            if "503" in str(hata) and deneme < 2:
                time.sleep(5 * (deneme + 1))
            else:
                raise hata

import base64
from google.genai import types



def yemek_analiz_et(mesaj, fotograf=None, mime_type=None):
    import json

    prompt = f"""
    Sen PelinI adlı profesyonel bir beslenme analiz asistanısın.

    Kullanıcının öğününü analiz et.
    Kullanıcı açıklaması: {mesaj}

    Görsel varsa görseldeki yiyecekleri de incele.

    Her yiyeceği ayrı bir kayıt olarak değerlendir.
    Her yiyecek için şu alanları oluştur:
    - name: Yiyeceğin adı
    - portion: Tahmini porsiyon
    - calories: Kalori (kcal)
    - protein_g: Protein (gram)
    - carbs_g: Karbonhidrat (gram)
    - fat_g: Yağ (gram)

    Porsiyon belirsizse makul bir tahmin yap ve bunu açıkça belirt.
    Marka veya içerik bilinmiyorsa kesin değer iddiasında bulunma.
    Aynı yiyeceği iki kez sayma.

    Yalnızca aşağıdaki yapıda geçerli JSON döndür:
    {{
        "items": [
            {{
                "name": "Muz",
                "portion": "1 orta boy",
                "calories": 105,
                "protein_g": 1.3,
                "carbs_g": 27,
                "fat_g": 0.3
            }}
        ],
        "notes": ["Porsiyonlar tahminidir."]
    }}

    JSON dışında açıklama veya Markdown yazma.
    """

    icerik = [prompt]

    if fotograf:
        fotograf_bytes = base64.b64decode(fotograf)
        icerik.append(
            types.Part.from_bytes(
                data=fotograf_bytes,
                mime_type=mime_type
            )
        )

    response = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=icerik,
        config=types.GenerateContentConfig(
            response_mime_type="application/json"
        )
    )

    veri = json.loads(response.text)

    if not isinstance(veri.get("items"), list) or not veri["items"]:
        raise ValueError("Geçerli bir yiyecek analizi oluşturulamadı.")

    toplamlar = {
        "calories": 0,
        "protein_g": 0,
        "carbs_g": 0,
        "fat_g": 0
    }

    for item in veri["items"]:
        for alan in toplamlar:
            deger = float(item[alan])
            if deger < 0:
                raise ValueError("Besin değerleri negatif olamaz.")
            item[alan] = deger
            toplamlar[alan] += deger

    toplamlar["calories"] = round(toplamlar["calories"])
    for alan in ("protein_g", "carbs_g", "fat_g"):
        toplamlar[alan] = round(toplamlar[alan], 1)

    return {
        "items": veri["items"],
        "totals": toplamlar,
        "notes": veri.get("notes", [])
    }

def aktivite_ve_kalori_ajani(gunluk_hedef_kalori: int, alinan_kalori: int, alinan_protein: float, hedef_protein: float, kullanici_notu: str = ""):
    """
    Kullanıcının günlük enerji dengesini inceler, hedeflerine göre
    durumu analiz eder ve spesifik egzersiz/aktivite önerileri üretir.
    """
    import json

    fark = alinan_kalori - gunluk_hedef_kalori
    durum = "kalori_fazlasi" if fark > 0 else "kalori_acigi"

    prompt = f"""
    Sen PelinI adlı bütüncül beslenme ve aktif yaşam/fitness uzmanı bir yapay zekâ ajanısın.

    Kullanıcının Günlük Verileri:
    - Günlük Hedef Kalori: {gunluk_hedef_kalori} kcal
    - Şu Ana Kadar Alınan Kalori: {alinan_kalori} kcal
    - Kalori Dengesi: {abs(fark)} kcal {'fazla alındı' if fark > 0 else 'daha pay var (kalori açığı)'}
    - Alınan Protein / Hedef: {alinan_protein}g / {hedef_protein}g
    - Kullanıcının Tercihi veya Durum Notu: "{kullanici_notu}"

    GÖREVİN:
    1. Günlük beslenme ve kalori dengesini profesyonelce, motive edici bir dille özetle.
    2. Kullanıcının durumuna göre (kalori fazlası varsa bunu yakmak/dengelemek için, kalori açığı varsa yağ yakımını destekleyip kas kütlesini korumak için) 2 ila 3 adet uygulanabilir spor/aktivite seçeneği sun.
    3. Her aktivite için tahmini süre ve yakılacak yaklaşık kaloriyi belirle.
    4. Kalan protein ihtiyacına veya toparlanmaya (recovery) yönelik kısa bir ipucu ekle.

    Yalnızca aşağıdaki şemaya uygun geçerli bir JSON çıktısı üret:
    {{
        "ozet_yorum": "Bugün hedefin 250 kcal üzerindesin ancak protein hedefini harika yakalamışsın...",
        "durum_tipi": "{durum}",
        "onerilen_aktiviteler": [
            {{
                "aktivite_adi": "Tempolu Açık Hava Yürüyüşü",
                "sure_dakika": 40,
                "tahmini_yakilan_kalori": 180,
                "aciklama": "Akşam yemeği sonrası sindirimi kolaylaştırır ve kan şekerini dengeler."
            }},
            {{
                "aktivite_adi": "Evde HIIT veya Kardiyo",
                "sure_dakika": 20,
                "tahmini_yakilan_kalori": 200,
                "aciklama": "Kısa sürede etkili kalori yakımı ve metabolizma hızlandırma."
            }}
        ],
        "beslenme_tavsiyesi": "Protein hedefin tamamlandığı için gece acıkırsan sade maden suyu veya bitki çayı tercih edebilirsin."
    }}

    JSON dışında hiçbir giriş veya Markdown açıklaması yazma.
    """

    for deneme in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.3
                )
            )
            return json.loads(response.text)

        except Exception as hata:
            if "503" in str(hata) and deneme < 2:
                time.sleep(3 * (deneme + 1))
            else:
                raise hata
