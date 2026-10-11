# Wiqaya server

FastAPI server that serves the website (`website/`) and runs the fire-risk model behind the API.
Installation, the model and the API are documented in the [main README](../README.md#8-run-the-proof-of-concept).

```bash
pip install -r server/requirements.txt
python server/app.py          # then open http://localhost:8000
```

- `modele.py`: the platform's version of the code208 model. It covers the 250 m grid, terrain and
  population features, fire history from FIRMS, yearly susceptibility with leave-one-year-out validation,
  the Open-Meteo weather danger index and the daily map.
- `app.py`: website and API routes (`/api/risque`, `/api/feux`, `/api/foret`, `/api/trpc/alerts.subscribe`).
- `cache/`: model preparation and alert sign-ups. It is created automatically and not versioned.

The code comments are in French.
