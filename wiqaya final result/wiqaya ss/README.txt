WIQAYA — VERSION HTML / CSS / JAVASCRIPT

Contenu :
- index2.html : structure de la page
- wiqaya.css : styles et responsive design
- wiqaya.js : interactions de la carte, localisation et formulaire d’alerte
- carte-risque.js / carte-risque.css : carte du risque d’incendie (modèle code208) avec Leaflet
- i18n.js : traduction du site en français, anglais et arabe (bouton 🌐 de l’en-tête, ou ?lang=fr|en|ar)

Utilisation :
1. Depuis la racine du dépôt : pip install -r serveur/requirements.txt puis python serveur/app.py
2. Ouvrez http://localhost:8000 (page index2.html) ou http://localhost:8000/carte.html (carte plein écran).
   Voir serveur/README.md pour le détail du modèle et de l’API.

La carte, le danger météo du jour et l’historique (calendrier -> détections FIRMS) viennent du serveur.
La liste « incendies en cours » reste une donnée de démonstration. Le formulaire d’alerte envoie les inscriptions
au serveur (/api/trpc/alerts.subscribe) et garde une sauvegarde locale si l’API n’est pas disponible.
