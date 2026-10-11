// Carte du risque d'incendie (modèle code208) : interroge l'API du serveur Wiqaya (serveur/app.py)
// et affiche les cellules de 250 m, le danger météo du jour et l'historique des détections FIRMS.
(function () {
  const conteneur = document.querySelector("#carteRisque");
  if (!conteneur || !window.L) return;

  // Traduction (i18n.js) : renvoie le texte français tel quel si i18n.js n'est pas chargé.
  const t = (texte, valeurs) => (window.wiqayaI18n ? window.wiqayaI18n.t(texte, valeurs) : texte.replace(/\{(\w+)\}/g, (m, k) => valeurs?.[k] ?? m));
  const locale = () => (window.wiqayaI18n ? window.wiqayaI18n.locale() : "fr-MA");

  const CLASSES = {
    1: { label: "Très faible", couleur: "#1a9850" },
    2: { label: "Faible", couleur: "#91cf60" },
    3: { label: "Modéré", couleur: "#fee08b" },
    4: { label: "Élevé", couleur: "#fc8d59" },
    5: { label: "Très élevé", couleur: "#d73027" },
  };
  // Classes de danger renvoyées par l'API -> libellé (français, traduit par t) et couleur
  const DANGER = {
    faible: ["Faible", "#1a9850"], "modéré": ["Modéré", "#d8b34c"], "élevé": ["Élevé", "#ec8a2a"],
    "très élevé": ["Très élevé", "#ff3131"], inconnu: ["Non disponible", "#81909a"],
  };

  const carte = L.map(conteneur, { preferCanvas: true, zoomControl: true, attributionControl: true }).setView([35.25, -5.45], 11);
  // Fond de carte : Esri World Topo, sans clé. Les serveurs d'OpenStreetMap.org refusent les sites lancés en
  // localhost (403 "Access blocked") et CARTO exige désormais une clé : OpenTopoMap sert de secours si Esri échoue.
  const SOURCES = " · NASA FIRMS · Open-Meteo";
  const fondEsri = L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}", {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.esri.com">Esri</a>, HERE, Garmin, &copy; OpenStreetMap' + SOURCES,
  }).addTo(carte);
  let erreursFond = 0;
  fondEsri.on("tileerror", () => {
    if (++erreursFond !== 4) return;
    carte.removeLayer(fondEsri);
    L.tileLayer("https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png", {
      maxZoom: 17,
      attribution: '&copy; <a href="https://opentopomap.org">OpenTopoMap</a> (CC-BY-SA), &copy; OpenStreetMap' + SOURCES,
    }).addTo(carte).bringToBack();
  });

  const deuxPoints = () => (window.wiqayaI18n?.langue() === "fr" || !window.wiqayaI18n ? " : " : ": ");
  const fmt = (v, d = 0) => (v === null || v === undefined ? "—" : Number(v).toLocaleString(locale(), { maximumFractionDigits: d, minimumFractionDigits: d }));

  function popupCellule(p) {
    const dernierFeu = p.annees_depuis_dernier_feu >= 20 ? t("aucun depuis 2005") : t("il y a {n} an(s)", { n: fmt(p.annees_depuis_dernier_feu, 1) });
    return `<div dir="auto">
      <strong>${t(CLASSES[p.classe_risque]?.label || "?")}</strong>${p.alerte_feu ? ` · <b style="color:#d73027">${t("zone en alerte")}</b>` : ""}<br>
      ${t("Susceptibilité")}${deuxPoints()}${fmt(100 * p.susceptibilite, 1)} %<br>
      ${t("Dernier feu connu")}${deuxPoints()}${dernierFeu}<br>
      ${t("Altitude")}${deuxPoints()}${fmt(p.altitude_m)} m · ${t("pente")}${deuxPoints()}${fmt(p.pente_pct)} %<br>
      ${t("Population")}${deuxPoints()}${fmt(p.population)} ${t("hab.")} · ${t("partie")} ${p.partie}</div>`;
  }

  const coucheForet = L.geoJSON(null, { style: { color: "#0b3446", weight: 1, opacity: 0.5, fill: false }, interactive: false }).addTo(carte);
  const coucheFeux = L.layerGroup().addTo(carte);
  const coucheRisque = L.geoJSON(null, {
    style: (f) => ({
      color: f.properties.alerte_feu ? "#7a0000" : "transparent",
      weight: f.properties.alerte_feu ? 1 : 0,
      fillColor: CLASSES[f.properties.classe_risque]?.couleur || "#ccc",
      fillOpacity: 0.62,
    }),
    // Contenu calculé à l'ouverture : la popup suit la langue choisie
    onEachFeature: (f, layer) => layer.bindPopup(() => popupCellule(f.properties)),
  }).addTo(carte);

  // Légende et danger météo (contrôles Leaflet, communs à index2.html et carte.html)
  const legende = L.control({ position: "bottomright" });
  legende.onAdd = () => {
    const div = L.DomUtil.create("div", "carte-legende");
    div.setAttribute("data-no-i18n", "");
    div.dir = "auto";
    return div;
  };
  legende.addTo(carte);
  const zoneLegende = conteneur.querySelector(".carte-legende");
  function afficherLegende() {
    zoneLegende.innerHTML = `<strong>${t("Risque de feu")}</strong>` +
      Object.values(CLASSES).reverse().map((c) => `<span><i style="background:${c.couleur}"></i>${t(c.label)}</span>`).join("") +
      `<span><i class="alerte"></i>${t("Zone en alerte (top 20 %)")}</span><span><i class="firms"></i>${t("Détection FIRMS")}</span>`;
  }

  const infoDanger = L.control({ position: "bottomleft" });
  infoDanger.onAdd = () => {
    const div = L.DomUtil.create("div", "carte-danger");
    div.setAttribute("data-no-i18n", "");
    div.dir = "auto";
    return div;
  };
  infoDanger.addTo(carte);
  const zoneDanger = conteneur.querySelector(".carte-danger");
  let dernierResume = null;
  let derniereErreur = null;

  function afficherDanger() {
    if (derniereErreur) {
      zoneDanger.innerHTML = `<strong style="color:#ff3131">${t("Modèle indisponible")}</strong><span>${t(derniereErreur.texte, derniereErreur.valeurs)}</span>`;
      return;
    }
    if (!dernierResume) { zoneDanger.textContent = t("Chargement du modèle…"); return; }
    const resume = dernierResume, d = resume.danger;
    const [libelle, couleur] = DANGER[d.classe] || DANGER.inconnu;
    const date = new Date(resume.date).toLocaleDateString(locale(), { day: "numeric", month: "long", year: "numeric" });
    const meteo = d.meteo
      ? `<span>${fmt(d.meteo.temperature_2m_max)} °C · ${t("HR min")} ${fmt(d.meteo.relative_humidity_2m_min)} % · ${t("vent")} ${fmt(d.meteo.wind_speed_10m_max)} ${t("km/h")}</span>`
      : "";
    // Comme dans le notebook : l'alerte n'est opérationnelle que si le danger météo est élevé ou très élevé
    const message = resume.alerte_operationnelle ? t("Alerte active sur les zones encadrées.")
      : d.classe === "inconnu" ? t("Open-Meteo n'a pas répondu : danger météo non calculé.")
        : d.classe === "modéré" ? t("Danger modéré : pas d'alerte, la carte montre les zones les plus sensibles.")
          : t("Journée peu dangereuse : la carte montre les zones les plus sensibles.");
    zoneDanger.innerHTML = `
      <small>${t("DANGER MÉTÉO")} · ${date}</small>
      <strong style="color:${couleur}">${t(libelle)}${d.indice !== null ? ` <em>${fmt(d.indice, 2)}</em>` : ""}</strong>
      ${meteo}<span>${message}</span>`;
  }

  function erreur(texte, valeurs) {
    derniereErreur = { texte, valeurs };
    afficherDanger();
  }

  afficherLegende();
  afficherDanger();
  window.addEventListener("wiqaya:langue", () => { afficherLegende(); afficherDanger(); carte.closePopup(); });

  fetch("/api/foret")
    .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
    .then((foret) => {
      coucheForet.addData(foret);
      carte.fitBounds(coucheForet.getBounds(), { padding: [10, 10] });
    })
    .catch(() => erreur("Lancez le serveur (python serveur/app.py) puis ouvrez http://localhost:8000."));

  fetch("/api/risque")
    .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
    .then((data) => {
      coucheRisque.addData(data);
      coucheForet.bringToFront();
      dernierResume = data.resume;
      afficherDanger();
      const maj = document.querySelector("#updatedAt");
      if (maj) maj.textContent = new Date().toLocaleTimeString(locale(), { hour: "2-digit", minute: "2-digit" });
      window.dispatchEvent(new CustomEvent("wiqaya:risque", { detail: data.resume }));
    })
    .catch((e) => erreur("L'API /api/risque ne répond pas ({e}).", { e }));

  // Historique : détections FIRMS d'une date (appelé par le calendrier de index2.html)
  window.wiqayaFeux = async function (isoDate) {
    const r = await fetch(`/api/feux?date=${isoDate}`);
    if (!r.ok) throw new Error(`API ${r.status}`);
    const data = await r.json();
    coucheFeux.clearLayers();
    L.geoJSON(data, {
      pointToLayer: (f, latlng) => L.circleMarker(latlng, {
        radius: 6, color: "#fff", weight: 1.5, fillColor: f.properties.dans_foret ? "#ff3131" : "#ec8a2a", fillOpacity: 0.95,
      }).bindPopup(() => `<div dir="auto"><strong>${t("Détection FIRMS")}</strong><br>${new Date(f.properties.date).toLocaleDateString(locale())} · FRP ${fmt(f.properties.frp, 1)} MW<br>${t(f.properties.dans_foret ? "dans la forêt" : "à moins de 5 km de la forêt")}</div>`),
    }).addTo(coucheFeux);
    if (data.features.length) carte.fitBounds(L.geoJSON(data).getBounds().pad(0.3), { maxZoom: 13 });
    return data.resume;
  };
})();
