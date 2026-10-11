# Wiqaya web platform (optional)

FastAPI server that serves the website (`website/`) and runs the model from `src/wiqaya_model.py` behind an API.

```bash
pip install -r requirements.txt
python server/app.py          # then open http://localhost:8000
```

| Route | Returns |
|---|---|
| `GET /api/risk[?date=YYYY-MM-DD]` | Risk cells as GeoJSON (WGS 84) and a summary: weather danger, model, validation and test scores |
| `GET /api/fires?date=YYYY-MM-DD[&days=N]` | NASA FIRMS detections within 5 km of the forest |
| `GET /api/forest` | Forest boundaries |
| `POST /api/trpc/alerts.subscribe` | Alert sign-up from the website form |

The first start prepares the model in 3 to 5 minutes. It is then cached in `server/cache/`, which is not versioned,
together with the alert sign-ups.

| Variable | Default | Purpose |
|---|---|---|
| `PORT` | `8000` | Port |
| `HOST` | `127.0.0.1` | Listening address |
| `WIQAYA_DATA` | `data/sample_input` | Input folder |
| `WIQAYA_CACHE` | `server/cache` | Cache folder |
