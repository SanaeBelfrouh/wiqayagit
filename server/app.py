"""Serveur Wiqaya : sert le site web et l'API du modèle de risque d'incendie code208.

Lancement (depuis la racine du dépôt) :
    pip install -r server/requirements.txt
    python server/app.py            # puis ouvrir http://localhost:8000
"""
import json
import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).resolve().parent))
import modele as m  # noqa: E402

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s : %(message)s')
SITE = m.RACINE / 'website'
INSCRIPTIONS = m.CACHE / 'inscriptions.jsonl'

modele = None


@asynccontextmanager
async def lifespan(_app):
    global modele
    modele = m.ModeleRisque()
    yield


app = FastAPI(title='Wiqaya — API du modèle de risque d\'incendie', lifespan=lifespan)
app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.get('/api/risque')
def risque(date_: date | None = Query(None, alias='date')):
    """Carte du risque du jour (ou d'une date donnée) : cellules de 250 m en GeoJSON WGS 84 + résumé du modèle."""
    t, resume = modele.carte_du_jour(date_)
    t = t.round({'susceptibilite': 4, 'annees_depuis_dernier_feu': 1, 'altitude_m': 0, 'pente_pct': 1, 'population': 1})
    geo = m.vers_geojson(t, ['id_cell', 'partie', 'susceptibilite', 'classe_risque', 'alerte_feu',
                             'annees_depuis_dernier_feu', 'altitude_m', 'pente_pct', 'population'], simplification_m=5)
    return {**geo, 'resume': resume}


@app.get('/api/foret')
def foret():
    return m.vers_geojson(modele.forest, ['partie'], simplification_m=10)


@app.get('/api/feux')
def feux(date_: date = Query(..., alias='date'), jours: int = Query(1, ge=1, le=366)):
    """Détections FIRMS (NASA) à moins de 5 km de la forêt, du `date` inclus sur `jours` jours."""
    fin = date_ + timedelta(days=jours - 1)
    f = modele.feux(date_, fin)
    return {**m.vers_geojson(f, ['date', 'frp', 'dans_foret']),
            'resume': {'debut': str(date_), 'fin': str(fin), 'detections': len(f), 'dans_foret': int(f.dans_foret.sum()),
                       'firms_jusqu_au': str(modele.firms.date.max().date())}}


class Inscription(BaseModel):
    firstName: str = Field(min_length=1, max_length=100)
    lastName: str = Field(min_length=1, max_length=100)
    phone: str | None = Field(None, max_length=40)
    email: str | None = Field(None, max_length=200)
    forest: str | None = Field(None, max_length=100)
    notificationChannels: list[str] = Field(default_factory=list, max_length=5)
    allowLocation: bool = False


class EnveloppeTrpc(BaseModel):
    json_: Inscription = Field(alias='json')


@app.post('/api/trpc/alerts.subscribe')
def inscrire(corps: EnveloppeTrpc):
    """Endpoint appelé par le formulaire d'alerte du site (format tRPC) : enregistre l'inscription en local."""
    i = corps.json_
    if not (i.phone or i.email):
        raise HTTPException(422, 'Un téléphone ou un e-mail est requis.')
    INSCRIPTIONS.parent.mkdir(parents=True, exist_ok=True)
    with INSCRIPTIONS.open('a', encoding='utf-8') as f:
        f.write(json.dumps({**i.model_dump(), 'recu_le': datetime.now().isoformat(timespec='seconds')}, ensure_ascii=False) + '\n')
    return {'result': {'data': {'json': {'ok': True}}}}


@app.get('/')
def accueil():
    return FileResponse(SITE / 'index2.html')


app.mount('/', StaticFiles(directory=SITE), name='site')

if __name__ == '__main__':
    uvicorn.run(app, host=os.environ.get('HOST', '127.0.0.1'), port=int(os.environ.get('PORT', 8000)))
