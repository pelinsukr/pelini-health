
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from ai_model import yapay_zeka_cevap, yemek_analiz_et
from datetime import datetime
import sqlite3
import json

app = FastAPI(title="PelinI - Health Assistant")

DB_NAME = "pelini.db"


def veritabani_olustur():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS meals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                meal_date TEXT NOT NULL,
                items TEXT NOT NULL,
                totals TEXT NOT NULL,
                notes TEXT
            )
        """)


veritabani_olustur()


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
        print("Soru hatası:", hata)
        raise HTTPException(
            status_code=502,
            detail="Yanıt oluşturulamadı."
        )


@app.post("/yemek-analiz")
def yemek_analizi(istek: YemekAnalizi):
    if not istek.mesaj.strip() and not istek.fotograf:
        raise HTTPException(
            status_code=400,
            detail="Lütfen yemek yazın veya fotoğraf yükleyin."
        )

    try:
        analiz = yemek_analiz_et(
            mesaj=istek.mesaj,
            fotograf=istek.fotograf,
            mime_type=istek.mime_type
        )

        simdi = datetime.now().astimezone()
        tarih_saat = simdi.isoformat(timespec="seconds")
        tarih = simdi.date().isoformat()

        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.execute(
                """
                INSERT INTO meals
                (created_at, meal_date, items, totals, notes)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    tarih_saat,
                    tarih,
                    json.dumps(analiz["items"], ensure_ascii=False),
                    json.dumps(analiz["totals"], ensure_ascii=False),
                    json.dumps(analiz.get("notes", []), ensure_ascii=False)
                )
            )
            kayit_id = cursor.lastrowid

        return {
            "kayit_id": kayit_id,
            "tarih_saat": tarih_saat,
            "analiz": analiz
        }

    except Exception as hata:
        print("Yemek analiz hatası:", hata)
        raise HTTPException(
            status_code=502,
            detail="Yemek analizi veya kayıt işlemi yapılamadı."
        )


@app.get("/gunluk-ozet")
def gunluk_ozet(tarih: str | None = None):
    if tarih is None:
        tarih = datetime.now().astimezone().date().isoformat()

    try:
        datetime.strptime(tarih, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Tarih YYYY-AA-GG formatında olmalıdır."
        )

    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        kayitlar = conn.execute(
            """
            SELECT * FROM meals
            WHERE meal_date = ?
            ORDER BY created_at ASC
            """,
            (tarih,)
        ).fetchall()

    toplamlar = {
        "calories": 0,
        "protein_g": 0,
        "carbs_g": 0,
        "fat_g": 0
    }

    ogunler = []

    for kayit in kayitlar:
        degerler = json.loads(kayit["totals"])

        for alan in toplamlar:
            toplamlar[alan] += degerler.get(alan, 0)

        ogunler.append({
            "id": kayit["id"],
            "tarih_saat": kayit["created_at"],
            "items": json.loads(kayit["items"]),
            "totals": degerler,
            "notes": json.loads(kayit["notes"] or "[]")
        })

    toplamlar["calories"] = round(toplamlar["calories"])
    for alan in ("protein_g", "carbs_g", "fat_g"):
        toplamlar[alan] = round(toplamlar[alan], 1)

    return {
        "tarih": tarih,
        "ogun_sayisi": len(ogunler),
        "ogunler": ogunler,
        "toplamlar": toplamlar
    }
