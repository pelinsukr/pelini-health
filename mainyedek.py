
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from ai_model import yapay_zeka_cevap, yemek_analiz_et

app = FastAPI(title="PelinI - Health Assistant")


class Soru(BaseModel):
    mesaj: str


class YemekAnalizi(BaseModel):
    mesaj: str = ""
    fotograf: str | None = None
    mime_type: str | None = None


@app.get("/")
def ana_sayfa():
    return FileResponse("static/index.html")


@app.post("/sor")
def soru_sor(soru: Soru):
    try:
        cevap = yapay_zeka_cevap(soru.mesaj)
        return {"soru": soru.mesaj, "cevap": cevap}
    except Exception as hata:
        print("Hata:", hata)
        raise HTTPException(status_code=502, detail="Yanıt oluşturulamadı.")


@app.post("/yemek-analiz")
def yemek_analizi(istek: YemekAnalizi):
    if not istek.mesaj.strip() and not istek.fotograf:
        raise HTTPException(
            status_code=400,
            detail="Lütfen yemek yazın veya fotoğraf yükleyin."
        )

    try:
        cevap = yemek_analiz_et(
            mesaj=istek.mesaj,
            fotograf=istek.fotograf,
            mime_type=istek.mime_type
        )
        return {"analiz": cevap}

    except Exception as hata:
        print("Yemek analiz hatası:", hata)
        raise HTTPException(
            status_code=502,
            detail="Yemek analizi şu anda yapılamadı."
        )
