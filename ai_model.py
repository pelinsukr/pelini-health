import base64
import json
import os
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai import errors
from ai_model import yemek_analiz_et, yapay_zeka_cevap, aktivite_ve_kalori_ajani

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("API anahtarı bulunamadı! Lütfen .env dosyasını kontrol edin.")

client = genai.Client(api_key=api_key)

# Yoğunluktan etkilenmeyen hızlı ve kararlı model
MODEL_NAME = "gemini-3.5-flash-lite"


def yapay_zeka_cevap(soru: str):
    for deneme in range(4):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=soru
            )
            return response.text
        except errors.ServerError as hata:
            if deneme < 3:
                time.sleep(3 * (deneme + 1))
            else:
                raise hata


def yemek_analiz_et(mesaj, fotograf=None, mime_type=None):
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
        model=MODEL_NAME,
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
    fark = alinan_kalori - gunluk_hedef_kalori
    durum = "kalori_fazlasi" if fark > 0 else "kalori_acigi"

    prompt = f"""
Sen PelinI adlı bütüncül beslenme ve spor asistanısın.

Kullanıcı Özeti:
- Hedef: {gunluk_hedef_kalori} kcal | Alınan: {alinan_kalori} kcal | Fark: {abs(fark)} kcal ({durum})
- Protein: {alinan_protein}g / {hedef_protein}g
- Not: {kullanici_notu}

Aşağıdaki JSON şablonunu doldur ve yalnızca bu JSON objesini döndür:
{{
  "ozet_yorum": "kısa durum değerlendirmesi",
  "durum_tipi": "{durum}",
  "onerilen_aktiviteler": [
    {{
      "aktivite_adi": "Aktivite Adı",
      "sure_dakika": 30,
      "tahmini_yakilan_kalori": 150,
      "aciklama": "Neden önerildiği"
    }}
  ],
  "beslenme_tavsiyesi": "kısa öneri"
}}
"""

    for deneme in range(4):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            return json.loads(response.text)
        except errors.ServerError as hata:
            if deneme < 3:
                bekleme = 3 * (deneme + 1)
                print(f"Sunucu yoğun, {bekleme} saniye sonra tekrar deneniyor...")
                time.sleep(bekleme)
            else:
                raise hata


if __name__ == "__main__":
    import pprint
    print("Ajan çağrılıyor, lütfen bekleyin...")
    sonuc = aktivite_ve_kalori_ajani(
        gunluk_hedef_kalori=1800,
        alinan_kalori=2050,
        alinan_protein=95.0,
        hedef_protein=110.0,
        kullanici_notu="Bugün evdeyim, ekipmansız egzersiz olsun"
    )
    print("\n--- AJAN YANITI ---")
    pprint.pprint(sonuc)

from pydantic import BaseModel

class AktiviteIstegi(BaseModel):
    gunluk_hedef_kalori: int = 1800
    alinan_kalori: int
    alinan_protein: float
    hedef_protein: float = 100.0
    kullanici_notu: str = ""

@app.post("/api/aktivite-onerisi")
def aktivite_tavsiyesi_al(istek: AktiviteIstegi):
    try:
        sonuc = aktivite_ve_kalori_ajani(
            gunluk_hedef_kalori=istek.gunluk_hedef_kalori,
            alinan_kalori=istek.alinan_kalori,
            alinan_protein=istek.alinan_protein,
            hedef_protein=istek.hedef_protein,
            kullanici_notu=istek.kullanici_notu
        )
        return {"success": True, "data": sonuc}
    except Exception as e:
        return {"success": False, "error": str(e)}