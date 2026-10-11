"""Wiqaya web platform: serves the website and the fire-risk model API.

Run from the repository root:
    pip install -r requirements.txt
    python server/app.py            # then open http://localhost:8000
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

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'src'))
import wiqaya_model as wm  # noqa: E402

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
WEBSITE = wm.ROOT / 'website'
SIGNUPS = wm.CACHE / 'alert_signups.jsonl'

service = None


@asynccontextmanager
async def lifespan(_app):
    global service
    service = wm.RiskService()
    yield


app = FastAPI(title='Wiqaya — wildfire risk API', lifespan=lifespan)
app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.get('/api/risk')
def risk(date_: date | None = Query(None, alias='date')):
    """Risk map of today (or of `date`): 250 m cells as GeoJSON (WGS 84) + summary of the model and weather danger."""
    cells, summary = service.risk_map(date_)
    cells = cells.round({'susceptibility': 4, 'years_since_last_fire': 1, 'elevation_m': 0, 'slope_pct': 1, 'population': 1})
    geo = wm.to_geojson(cells, ['cell_id', 'part', 'susceptibility', 'risk_class', 'alert', 'years_since_last_fire',
                                'elevation_m', 'slope_pct', 'population'], simplify_m=5)
    return {**geo, 'summary': summary}


@app.get('/api/forest')
def forest():
    return wm.to_geojson(service.forest, ['part'], simplify_m=10)


@app.get('/api/fires')
def fires(date_: date = Query(..., alias='date'), days: int = Query(1, ge=1, le=366)):
    """NASA FIRMS detections within 5 km of the forest, from `date` included, over `days` days."""
    end = date_ + timedelta(days=days - 1)
    f = service.fires(date_, end)
    return {**wm.to_geojson(f, ['date', 'frp', 'inside_forest']),
            'summary': {'start': str(date_), 'end': str(end), 'detections': len(f), 'inside_forest': int(f.inside_forest.sum()),
                        'firms_until': str(service.firms.date.max().date())}}


class Signup(BaseModel):
    firstName: str = Field(min_length=1, max_length=100)
    lastName: str = Field(min_length=1, max_length=100)
    phone: str | None = Field(None, max_length=40)
    email: str | None = Field(None, max_length=200)
    forest: str | None = Field(None, max_length=100)
    notificationChannels: list[str] = Field(default_factory=list, max_length=5)
    allowLocation: bool = False


class TrpcEnvelope(BaseModel):
    json_: Signup = Field(alias='json')


@app.post('/api/trpc/alerts.subscribe')
def subscribe(body: TrpcEnvelope):
    """Called by the website's alert form (tRPC format): stores the sign-up locally."""
    s = body.json_
    if not (s.phone or s.email):
        raise HTTPException(422, 'A phone number or an email is required.')
    SIGNUPS.parent.mkdir(parents=True, exist_ok=True)
    with SIGNUPS.open('a', encoding='utf-8') as f:
        f.write(json.dumps({**s.model_dump(), 'received_at': datetime.now().isoformat(timespec='seconds')}, ensure_ascii=False) + '\n')
    return {'result': {'data': {'json': {'ok': True}}}}


@app.get('/')
def home():
    return FileResponse(WEBSITE / 'index2.html')


app.mount('/', StaticFiles(directory=WEBSITE), name='website')

if __name__ == '__main__':
    uvicorn.run(app, host=os.environ.get('HOST', '127.0.0.1'), port=int(os.environ.get('PORT', 8000)))
