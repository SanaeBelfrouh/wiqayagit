WIQAYA — WEBSITE (HTML / CSS / JAVASCRIPT)

Files:
- index2.html : home page
- carte.html : full-screen fire-risk map
- carte-risque.js / carte-risque.css : fire-risk map (Leaflet) fed by the server API
- i18n.js : English / French / Arabic translations (language button in the header, or ?lang=en|fr|ar)
- wiqaya.js / wiqaya.css : page interactions, alert form, styles and responsive design

Usage:
1. From the repository root: pip install -r server/requirements.txt then python server/app.py
2. Open http://localhost:8000 (home page) or http://localhost:8000/carte.html (full-screen map).
   See the main README.md for the model and the API.

The map, the weather danger and the fire history (calendar -> NASA FIRMS detections) come from the server.
The "active fires" list on the home page is still sample data. The alert form sends sign-ups to the
server (/api/trpc/alerts.subscribe) and keeps a local copy if the API is not available.
