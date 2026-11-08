
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


