// Traduction du site Wiqaya : français (texte d'origine de la page), anglais et arabe (de droite à gauche).
// Chaque texte de la page est retrouvé par sa version française : pas besoin d'annoter le HTML.
// Les scripts qui écrivent du texte (carte, calendrier, liste des feux) utilisent wiqayaI18n.t()
// et se redessinent à l'événement "wiqaya:langue".
(function () {
  const LANGUES = ["fr", "en", "ar"];
  const LOCALES = { fr: "fr-MA", en: "en-GB", ar: "ar-MA" };
  const BOUTON = { fr: "🌐 FR", en: "🌐 EN", ar: "🌐 AR" };

  // [français, anglais, arabe]. {n}, {date}… sont remplacés par wiqayaI18n.t(texte, valeurs).
  const TEXTES = [
    // En-tête et navigation
    ["Wiqaya — Surveillance des incendies au Maroc", "Wiqaya — Wildfire monitoring in Morocco", "وقاية: معلومات حول حرائق الغابات في المغرب"],
    ["Incendies en cours", "Active fires", "الحرائق المشتعلة"],
    ["Vigilance journalière", "Daily vigilance", "مستوى اليقظة اليومي"],
    ["Prévention", "Prevention", "الوقاية"],
    ["Recevoir les alertes", "Get alerts", "تلقي التنبيهات"],
    ["FORÊTS", "FORESTS", "الغابات"],
    ["Wiqaya informe sur les incendies au Maroc", "Wiqaya provides wildfire information in Morocco", "وقاية: معلومات حول حرائق الغابات في المغرب"],
    ["Une plateforme de surveillance et d’alerte pour Bouhachem, Derdara et Tazekka.", "A monitoring and alert platform for Bouhachem, Derdara and Tazekka.", "منصة لمراقبة الحرائق وإرسال التنبيهات لغابات بوهاشم ودردارة وتازكة."],
    ["Activer mes alertes", "Turn on my alerts", "تفعيل تنبيهاتي"],
    ["Recevez les alertes incendie de votre zone", "Get fire alerts for your area", "تلقَّ تنبيهات الحرائق في منطقتك"],
    ["Inscription gratuite par SMS et e-mail, sans publicité ni engagement.", "Free sign-up by SMS and email, no ads, no commitment.", "تسجيل مجاني عبر الرسائل القصيرة والبريد الإلكتروني، بدون إعلانات ولا التزام."],
    ["S’inscrire gratuitement", "Sign up for free", "سجّل مجانًا"],

    // Carte
    ["⌖ Ma position", "⌖ My location", "⌖ موقعي"],
    ["Carte du risque d'incendie", "Wildfire risk map", "خريطة خطر الحرائق"],
    ["⌁ Carte du risque d’incendie", "⌁ Wildfire risk map", "⌁ خريطة خطر الحرائق"],
    ["Source : modèle code208 · NASA FIRMS · Open-Meteo · mise à jour", "Source: code208 model · NASA FIRMS · Open-Meteo · updated", "المصدر: نموذج code208 · NASA FIRMS · Open-Meteo · آخر تحديث"],
    ["à l’instant", "just now", "الآن"],
    ["Risque de feu", "Fire risk", "خطر الحريق"],
    ["Très faible", "Very low", "منخفض جدًا"],
    ["Faible", "Low", "منخفض"],
    ["Modéré", "Moderate", "متوسط"],
    ["Élevé", "High", "مرتفع"],
    ["Très élevé", "Very high", "مرتفع جدًا"],
    ["Zone en alerte (top 20 %)", "Alert zone (top 20%)", "منطقة إنذار (أعلى 20٪)"],
    ["Détection FIRMS", "FIRMS detection", "رصد FIRMS"],
    ["Chargement du modèle…", "Loading the model…", "جارٍ تحميل النموذج…"],
    ["DANGER MÉTÉO", "WEATHER DANGER", "الخطر المناخي"],
    ["Non disponible", "Unavailable", "غير متوفر"],
    ["HR min", "min RH", "الرطوبة الدنيا"],
    ["vent", "wind", "الرياح"],
    ["km/h", "km/h", "كم/س"],
    ["Alerte active sur les zones encadrées.", "Alert active in the outlined zones.", "الإنذار مفعّل في المناطق المؤطَّرة."],
    ["Journée peu dangereuse : la carte montre les zones les plus sensibles.", "Low-danger day: the map shows the most sensitive areas.", "يوم قليل الخطورة: تُظهر الخريطة المناطق الأكثر حساسية."],
    ["Danger modéré : pas d'alerte, la carte montre les zones les plus sensibles.", "Moderate danger: no alert, the map shows the most sensitive areas.", "خطر متوسط: لا إنذار، تُظهر الخريطة المناطق الأكثر حساسية."],
    ["Open-Meteo n'a pas répondu : danger météo non calculé.", "Open-Meteo did not respond: weather danger not computed.", "لم يستجب Open-Meteo: لم يُحسب الخطر المناخي."],
    ["Modèle indisponible", "Model unavailable", "النموذج غير متوفر"],
    ["Lancez le serveur (python server/app.py) puis ouvrez http://localhost:8000.", "Start the server (python server/app.py) then open http://localhost:8000.", "شغّل الخادم (python server/app.py) ثم افتح http://localhost:8000."],
    ["L'API /api/risk ne répond pas ({e}).", "The /api/risk API is not responding ({e}).", "واجهة /api/risk لا تستجيب ({e})."],
    ["zone en alerte", "alert zone", "منطقة إنذار"],
    ["Susceptibilité", "Susceptibility", "القابلية للاشتعال"],
    ["Dernier feu connu", "Last known fire", "آخر حريق معروف"],
    ["aucun depuis 2005", "none since 2005", "لا شيء منذ 2005"],
    ["il y a {n} an(s)", "{n} year(s) ago", "منذ {n} سنة"],
    ["Altitude", "Elevation", "الارتفاع"],
    ["pente", "slope", "الانحدار"],
    ["Population", "Population", "السكان"],
    ["hab.", "people", "نسمة"],
    ["partie", "part", "الجزء"],
    ["dans la forêt", "inside the forest", "داخل الغابة"],
    ["à moins de 5 km de la forêt", "within 5 km of the forest", "على بعد أقل من 5 كلم من الغابة"],

    // Historique (calendrier)
    ["Historique des incendies", "Fire history", "السجل التاريخي للحرائق"],
    ["Choisissez une date pour consulter les incendies sur la carte.", "Pick a date to see the fires on the map.", "اختر تاريخًا لعرض الحرائق على الخريطة."],
    ["Mois précédent", "Previous month", "الشهر السابق"],
    ["Mois suivant", "Next month", "الشهر التالي"],
    ["Lun", "Mon", "إثن"], ["Mar", "Tue", "ثلا"], ["Mer", "Wed", "أرب"], ["Jeu", "Thu", "خمي"],
    ["Ven", "Fri", "جمع"], ["Sam", "Sat", "سبت"], ["Dim", "Sun", "أحد"],
    ["Choisir une date", "Choose a date", "اختر تاريخًا"],
    ["Aujourd’hui", "Today", "اليوم"],
    ["Aucune date sélectionnée", "No date selected", "لم يتم اختيار أي تاريخ"],
    ["Sélectionnez une date pour consulter l’historique.", "Select a date to view the history.", "اختر تاريخًا للاطلاع على السجل."],
    ["Date sélectionnée : {date}.", "Selected date: {date}.", "التاريخ المختار: {date}."],
    ["Recherche des détections FIRMS…", "Looking up FIRMS detections…", "جارٍ البحث عن رصد FIRMS…"],
    ["{n} détection(s) satellite FIRMS, dont {f} dans la forêt : points affichés sur la carte.", "{n} FIRMS satellite detection(s), {f} inside the forest: points shown on the map.", "{n} رصد بالأقمار الصناعية FIRMS، منها {f} داخل الغابة: النقاط معروضة على الخريطة."],
    ["Aucune détection FIRMS ce jour-là (données disponibles jusqu’au {date}).", "No FIRMS detection that day (data available until {date}).", "لا يوجد أي رصد FIRMS في ذلك اليوم (البيانات متوفرة حتى {date})."],
    ["Archives indisponibles : lancez le serveur Wiqaya (python server/app.py).", "Archive unavailable: start the Wiqaya server (python server/app.py).", "الأرشيف غير متوفر: شغّل خادم وقاية (python server/app.py)."],
    ["♧ Être alerté par SMS", "♧ Get SMS alerts", "♧ تلقَّ التنبيهات عبر الرسائل القصيرة"],

    // Liste des feux (données de démonstration) et localisation
    ["Forêt de Maâmora", "Maâmora forest", "غابة المعمورة"],
    ["Forêt de Talassemtane", "Talassemtane forest", "غابة تلاسمطان"],
    ["Forêt de Tazekka", "Tazekka forest", "غابة تازكة"],
    ["Kénitra", "Kenitra", "القنيطرة"], ["Chefchaouen", "Chefchaouen", "شفشاون"], ["Taza", "Taza", "تازة"],
    ["Sidi Yahya", "Sidi Yahya", "سيدي يحيى"], ["Akchour", "Akchour", "أقشور"], ["Bab Boudir", "Bab Boudir", "باب بودير"],
    ["Point chaud détecté par satellite, intervention en cours.", "Hotspot detected by satellite, response under way.", "بؤرة ساخنة رصدها القمر الصناعي، والتدخل جارٍ."],
    ["Surveillance renforcée autour de la zone montagneuse.", "Increased monitoring around the mountain area.", "مراقبة معززة حول المنطقة الجبلية."],
    ["Feu contenu, équipes présentes pour la surveillance.", "Fire contained, teams on site for monitoring.", "تمت السيطرة على الحريق، والفرق حاضرة للمراقبة."],
    ["Maîtrisé", "Contained", "تحت السيطرة"],
    ["ha", "ha", "هكتار"],
    ["◷ Mise à jour il y a 12 min", "◷ Updated 12 min ago", "◷ آخر تحديث قبل 12 دقيقة"],
    ["La géolocalisation n’est pas disponible sur cet appareil.", "Geolocation is not available on this device.", "تحديد الموقع غير متاح على هذا الجهاز."],
    ["Localisation activée. Les alertes proches de vous seront prioritaires.", "Location enabled. Alerts near you will be prioritised.", "تم تفعيل تحديد الموقع. ستُعطى الأولوية للتنبيهات القريبة منك."],
    ["Autorisation de localisation refusée par le navigateur.", "Location permission denied by the browser.", "رفض المتصفح الإذن بتحديد الموقع."],
    ["Choisissez au moins un canal de notification.", "Choose at least one notification channel.", "اختر قناة إشعار واحدة على الأقل."],

    // Rubriques
    ["Le risque, forêt par forêt", "Risk, forest by forest", "الخطر، غابةً بغابة"],
    ["Historique", "History", "السجل التاريخي"],
    ["Cartes et statistiques", "Maps and statistics", "خرائط وإحصائيات"],
    ["Les bons gestes", "Good practices", "السلوكيات الصحيحة"],
    ["Témoin d’un feu ?", "Witnessed a fire?", "شاهدت حريقًا؟"],
    ["Recevez l’alerte", "Get the alert", "تلقَّ التنبيه"],
    ["VIGILANCE PAR ZONE", "VIGILANCE BY AREA", "اليقظة حسب المنطقة"],
    ["Les indicateurs utilisent une source de démonstration. Votre flux officiel pourra être branché ensuite.", "These indicators use demo data. An official feed can be connected later.", "تعتمد هذه المؤشرات على بيانات تجريبية. يمكن ربط مصدر رسمي لاحقًا."],
    ["Jbel Sougna", "Jbel Sougna", "جبل سوكنة"],
    ["Forêt de Jbel Sougna · Chefchaouen", "Jbel Sougna forest · Chefchaouen", "غابة جبل سوكنة · شفشاون"],
    ["Indice de vigilance", "Vigilance index", "مؤشر اليقظة"],
    ["Bouhachem", "Bouhachem", "بوهاشم"],
    ["Forêt de Bouhachem · Chefchaouen", "Bouhachem forest · Chefchaouen", "غابة بوهاشم · شفشاون"],
    ["Derdara", "Derdara", "دردارة"],
    ["Forêt de Derdara · Chefchaoune", "Derdara forest · Chefchaouen", "غابة دردارة · شفشاون"],
    ["ACTUALITÉS & PRÉVENTION", "NEWS & PREVENTION", "الأخبار والوقاية"],
    ["Comprendre pour mieux protéger", "Understand to protect better", "نفهم لنحمي بشكل أفضل"],
    ["Voir tout →", "See all →", "عرض الكل ←"],
    ["PRÉVENTION", "PREVENTION", "الوقاية"],
    ["GUIDE WIQAYA", "WIQAYA GUIDE", "دليل وقاية"],
    ["Les bons gestes avant, pendant et après un incendie", "What to do before, during and after a wildfire", "السلوكيات الصحيحة قبل الحريق وأثناءه وبعده"],
    ["Adoptez les réflexes essentiels pour protéger votre famille et limiter les risques.", "Learn the key reflexes to protect your family and reduce the risks.", "اكتسب العادات الأساسية لحماية أسرتك والحد من المخاطر."],
    ["Lire l’article →", "Read the article →", "اقرأ المقال ←"],
    ["SURVEILLANCE", "MONITORING", "المراقبة"],
    ["SOURCE DE DONNÉES", "DATA SOURCE", "مصدر البيانات"],
    ["Comment Wiqaya détecte les points chauds par satellite", "How Wiqaya detects hotspots by satellite", "كيف ترصد وقاية البؤر الساخنة عبر الأقمار الصناعية"],
    ["Une vue pédagogique sur les données qui alimentent cette version.", "An educational look at the data behind this version.", "نظرة تعليمية على البيانات التي تغذي هذه النسخة."],
    ["Découvrir →", "Discover →", "اكتشف ←"],
    ["TÉMOIN D’UN FEU ?", "WITNESSED A FIRE?", "شاهدت حريقًا؟"],
    ["Un signal rapide peut", "A quick report can", "إبلاغ سريع"],
    ["faire toute la différence.", "make all the difference.", "قد يُحدث كل الفرق."],
    ["En cas de fumée ou de feu, éloignez-vous et contactez les secours. Wiqaya vous aide à rester informé.", "If you see smoke or fire, move away and call the emergency services. Wiqaya helps you stay informed.", "في حال رؤية دخان أو نار، ابتعد واتصل بفرق الإنقاذ. وقاية تساعدك على البقاء على اطلاع."],
    ["Urgence", "Emergency", "طوارئ"],

    // Formulaire d'alerte
    ["ALERTES WIQAYA", "WIQAYA ALERTS", "تنبيهات وقاية"],
    ["Activez vos alertes", "Turn on your alerts", "فعّل تنبيهاتك"],
    ["Recevez un SMS et un e-mail dès qu’un risque est confirmé dans votre zone.", "Get an SMS and an email as soon as a risk is confirmed in your area.", "تلقَّ رسالة قصيرة وبريدًا إلكترونيًا فور تأكيد خطر في منطقتك."],
    ["Prénom *", "First name *", "الاسم الشخصي *"],
    ["Ex. Yassine", "e.g. Yassine", "مثال: ياسين"],
    ["Nom *", "Last name *", "الاسم العائلي *"],
    ["Ex. Amrani", "e.g. Amrani", "مثال: العمراني"],
    ["Numéro de téléphone *", "Phone number *", "رقم الهاتف *"],
    ["Adresse e-mail *", "Email address *", "البريد الإلكتروني *"],
    ["vous@exemple.ma", "you@example.ma", "you@example.ma"],
    ["Forêt à surveiller", "Forest to monitor", "الغابة المراد مراقبتها"],
    ["Toutes les zones", "All areas", "جميع المناطق"],
    ["Forêt de Derdara", "Derdara forest", "غابة دردارة"],
    ["Forêt de Bouhachem", "Bouhachem forest", "غابة بوهاشم"],
    ["Forêt de Jbel Sougna", "Jbel Sougna forest", "غابة جبل سوكنة"],
    ["Canaux de notification", "Notification channels", "قنوات الإشعار"],
    ["Email", "Email", "البريد الإلكتروني"],
    ["Autoriser ma localisation pour prioriser les alertes proches de moi.", "Allow my location to prioritise alerts near me.", "السماح بتحديد موقعي لإعطاء الأولوية للتنبيهات القريبة مني."],
    ["Vos informations sont utilisées uniquement pour vous prévenir des incendies.", "Your information is only used to warn you about fires.", "تُستخدم معلوماتك فقط لتنبيهك بالحرائق."],
    ["Votre inscription est enregistrée. Vous recevrez les prochaines alertes Wiqaya.", "You're signed up. You will receive the next Wiqaya alerts.", "تم تسجيلك. ستتلقى تنبيهات وقاية القادمة."],

    // Pied de page et fenêtre de localisation
    ["WIQAYA", "WIQAYA", "وقاية"],
    ["Wiqaya", "Wiqaya", "وقاية"],
    ["Surveiller les feux.", "Monitor fires.", "مراقبة الحرائق."],
    ["Protéger les forêts du Maroc.", "Protect Morocco’s forests.", "حماية غابات المغرب."],
    ["Surveillance", "Monitoring", "المراقبة"],
    ["À propos", "About", "من نحن"],
    ["Contact", "Contact", "اتصل بنا"],
    ["Prototype · Données d’exemple", "Prototype · Sample data", "نموذج أولي · بيانات تجريبية"],
    ["Confidentialité · Mentions légales", "Privacy · Legal notice", "الخصوصية · الإشعارات القانونية"],
    ["Autoriser la localisation ?", "Allow location?", "السماح بتحديد الموقع؟"],
    ["Pour afficher les alertes proches de vous.", "To show alerts near you.", "لعرض التنبيهات القريبة منك."],
    ["Autoriser", "Allow", "سماح"],
    ["Plus tard", "Later", "لاحقًا"],
    ["Fermer", "Close", "إغلاق"],
  ];

  const normaliser = (s) => s.replace(/\s+/g, " ").trim();
  const DICO = new Map(TEXTES.map(([fr, en, ar]) => [normaliser(fr), { fr, en, ar }]));
  const ATTRIBUTS = ["placeholder", "aria-label", "title"];
  const originaux = new WeakMap();

  function lireLangue() {
    const demandee = new URLSearchParams(location.search).get("lang");
    if (LANGUES.includes(demandee)) return demandee;
    try { const l = localStorage.getItem("wiqayaLangue"); if (LANGUES.includes(l)) return l; } catch { /* stockage indisponible */ }
    // Première visite : langue du navigateur (français, anglais ou arabe), sinon anglais
    const navigateur = (navigator.language || "en").slice(0, 2);
    return LANGUES.includes(navigateur) ? navigateur : "en";
  }
  let langue = lireLangue();

  function remplir(texte, valeurs) {
    return valeurs ? texte.replace(/\{(\w+)\}/g, (m, k) => (k in valeurs ? valeurs[k] : m)) : texte;
  }

  function t(fr, valeurs) {
    const entree = DICO.get(normaliser(fr));
    return remplir(entree ? entree[langue] : fr, valeurs);
  }

  function ignore(el) {
    return !el || el.closest("script, style, [data-no-i18n]");
  }

  function traduireTexte(noeud) {
    if (!originaux.has(noeud)) originaux.set(noeud, noeud.nodeValue);
    const origine = originaux.get(noeud);
    const entree = DICO.get(normaliser(origine));
    if (!entree) return;
    const avant = origine.match(/^\s*/)[0], apres = origine.match(/\s*$/)[0];
    const voulu = langue === "fr" ? origine : avant + entree[langue] + apres;
    if (noeud.nodeValue !== voulu) noeud.nodeValue = voulu;
  }

  function traduireElement(el) {
    if (el.tagName === "OPTION" && !el.hasAttribute("value")) el.value = normaliser(el.textContent); // valeur envoyée : toujours le français
    for (const attr of ATTRIBUTS) {
      if (!el.hasAttribute(attr)) continue;
      const cle = "i18n" + attr.replace(/(^|-)(\w)/g, (m, s, c) => c.toUpperCase());
      if (!(cle in el.dataset)) el.dataset[cle] = el.getAttribute(attr);
      const entree = DICO.get(normaliser(el.dataset[cle]));
      if (entree) el.setAttribute(attr, entree[langue]);
    }
  }

  function traduire(racine) {
    if (racine.nodeType === Node.TEXT_NODE) {
      if (!ignore(racine.parentElement) && /\S/.test(racine.nodeValue)) traduireTexte(racine);
      return;
    }
    if (racine.nodeType !== Node.ELEMENT_NODE || ignore(racine)) return;
    traduireElement(racine);
    racine.querySelectorAll("*").forEach((el) => { if (!ignore(el)) traduireElement(el); });
    const parcours = document.createTreeWalker(racine, NodeFilter.SHOW_TEXT, {
      acceptNode: (n) => (!ignore(n.parentElement) && /\S/.test(n.nodeValue) ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT),
    });
    for (let n = parcours.nextNode(); n; n = parcours.nextNode()) traduireTexte(n);
  }

  function appliquer(nouvelle) {
    langue = nouvelle;
    try { localStorage.setItem("wiqayaLangue", langue); } catch { /* stockage indisponible */ }
    document.documentElement.lang = langue;
    document.documentElement.dir = langue === "ar" ? "rtl" : "ltr";
    const titre = DICO.get(normaliser(document.querySelector("title")?.dataset.i18nTitre || document.title));
    if (titre) { document.querySelector("title").dataset.i18nTitre = titre.fr; document.title = titre[langue]; }
    traduire(document.body);
    const bouton = document.querySelector("#languageBtn");
    if (bouton) bouton.textContent = BOUTON[langue];
    document.querySelectorAll("#languageMenu [data-lang]").forEach((b) => b.setAttribute("aria-pressed", b.dataset.lang === langue));
    window.dispatchEvent(new CustomEvent("wiqaya:langue", { detail: langue }));
  }

  // Textes ajoutés plus tard par les scripts (liste des feux, popups…) : traduits à la volée.
  new MutationObserver((mutations) => {
    if (langue === "fr") return;
    for (const m of mutations) m.addedNodes.forEach(traduire);
  }).observe(document.body, { childList: true, subtree: true });

  // Menu de langue (bouton 🌐 de l'en-tête)
  const bouton = document.querySelector("#languageBtn");
  const menu = document.querySelector("#languageMenu");
  if (bouton && menu) {
    bouton.closest(".language-selector")?.setAttribute("data-no-i18n", "");
    bouton.setAttribute("aria-haspopup", "true");
    bouton.addEventListener("click", (e) => { e.stopPropagation(); menu.classList.toggle("show"); });
    menu.querySelectorAll("[data-lang]").forEach((b) => b.addEventListener("click", () => { appliquer(b.dataset.lang); menu.classList.remove("show"); }));
    document.addEventListener("click", (e) => { if (!e.target.closest(".language-selector")) menu.classList.remove("show"); });
  }

  window.wiqayaI18n = { t, langue: () => langue, locale: () => LOCALES[langue], appliquer };
  appliquer(langue);
})();
