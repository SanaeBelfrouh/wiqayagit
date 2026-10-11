const fires = [
  { name: "Sidi Yahya", forest: "Forêt de Maâmora", province: "Kénitra", status: "active", risk: "critical", hectares: 18, description: "Point chaud détecté par satellite, intervention en cours." },
  { name: "Akchour", forest: "Forêt de Talassemtane", province: "Chefchaouen", status: "active", risk: "high", hectares: 6, description: "Surveillance renforcée autour de la zone montagneuse." },
  { name: "Bab Boudir", forest: "Forêt de Tazekka", province: "Taza", status: "contained", risk: "moderate", hectares: 42, description: "Feu contenu, équipes présentes pour la surveillance." },
];

const riskLabels = { critical: "Très élevé", high: "Élevé", moderate: "Maîtrisé" };
const feedList = document.querySelector("#feedList");
const popup = document.querySelector("#mapPopup");
const toast = document.querySelector("#locationToast");
const successMessage = document.querySelector("#successMessage");

function renderFeed() {
  feedList.innerHTML = fires.map((fire, index) => `
    <button class="feed-item" data-fire="${index}">
      <span class="feed-thumb ${fire.risk}">♨</span>
      <div><strong>${fire.name}</strong><span>${fire.province} · ${fire.hectares} ha</span><small>◷ Mise à jour il y a 12 min</small></div>
      <i class="feed-state ${fire.status}"></i>
    </button>
  `).join("");
  feedList.querySelectorAll("[data-fire]").forEach((item) => item.addEventListener("click", () => showFire(Number(item.dataset.fire))));
}

function showFire(index) {
  const fire = fires[index];
  document.querySelector("#popupRisk").textContent = riskLabels[fire.risk];
  document.querySelector("#popupRisk").className = `risk-tag ${fire.risk}`;
  document.querySelector("#popupTitle").textContent = fire.name;
  document.querySelector("#popupLocation").textContent = `${fire.forest} · ${fire.province}`;
  document.querySelector("#popupDescription").textContent = fire.description;
  popup.hidden = false;
}

function requestLocation() {
  if (!navigator.geolocation) {
    window.alert("La géolocalisation n’est pas disponible sur cet appareil.");
    return;
  }
  navigator.geolocation.getCurrentPosition(() => {
    toast.hidden = true;
    window.alert("Localisation activée. Les alertes proches de vous seront prioritaires.");
  }, () => window.alert("Autorisation de localisation refusée par le navigateur."), { enableHighAccuracy: true, timeout: 10000 });
}

document.querySelectorAll(".fire-pin").forEach((pin) => pin.addEventListener("click", () => showFire(Number(pin.dataset.fire))));
document.querySelector("#popupClose").addEventListener("click", () => { popup.hidden = true; });
document.querySelector("#mapLocation").addEventListener("click", requestLocation);
document.querySelector("#allowLocation").addEventListener("click", requestLocation);
document.querySelector("#dismissLocation").addEventListener("click", () => { toast.hidden = true; });
document.querySelector("#closeLocation").addEventListener("click", () => { toast.hidden = true; });
document.querySelector("#menuButton").addEventListener("click", () => { document.querySelector("#mainNav").classList.toggle("open"); });
document.querySelectorAll("#mainNav a").forEach((link) => link.addEventListener("click", () => document.querySelector("#mainNav").classList.remove("open")));
document.querySelectorAll(".banner-close").forEach((button) => button.addEventListener("click", () => button.closest(".info-banner").remove()));

document.querySelector("#alertForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const channels = [form.get("sms") ? "SMS" : "", form.get("emailChannel") ? "e-mail" : ""].filter(Boolean);
  if (!channels.length) {
    window.alert("Choisissez au moins un canal de notification.");
    return;
  }
  const subscription = { firstName: form.get("firstName"), lastName: form.get("lastName"), phone: form.get("phone"), email: form.get("email"), forest: form.get("forest"), notificationChannels: channels.map((channel) => channel === "SMS" ? "sms" : "email"), allowLocation: Boolean(form.get("location")) };
  try {
    const response = await fetch("/api/trpc/alerts.subscribe", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ json: subscription }) });
    if (!response.ok) throw new Error("API indisponible");
  } catch {
    localStorage.setItem("wiqayaAlertSubscription", JSON.stringify(subscription));
  }
  successMessage.classList.add("show");
  event.currentTarget.reset();
  window.setTimeout(() => successMessage.classList.remove("show"), 5000);
});

document.querySelector("#updatedAt").textContent = new Date().toLocaleTimeString("fr-MA", { hour: "2-digit", minute: "2-digit" });
renderFeed();


// const translations = {
//     fr: {
//         fires: "Incendies en cours",
//         vigilance: "Vigilance journalière",
//         history: "Historique",
//         prevention: "Prévention",
//         title: "Wiqaya informe sur les incendies au Maroc",
//         description: "Une plateforme de surveillance et d’alerte pour les forêts du Maroc.",
//         read: "Lire l’article →"
//     },

//     en: {
//         fires: "Active fires",
//         vigilance: "Daily vigilance",
//         history: "History",
//         prevention: "Prevention",
//         title: "Wiqaya provides wildfire information in Morocco",
//         description: "A monitoring and alert platform for Morocco's forests.",
//         read: "Read the article →"
//     },

//     ar: {
//         fires: "الحرائق المشتعلة",
//         vigilance: "مستوى اليقظة اليومي",
//         history: "السجل التاريخي",
//         prevention: "الوقاية",
//         title: "وقاية: معلومات حول حرائق الغابات في المغرب",
//         description: "منصة لمراقبة حرائق الغابات وإرسال التنبيهات في المغرب.",
//         read: "اقرأ المقال ←"
//     }
// };

// // Ouvrir et fermer le menu
// const languageBtn = document.getElementById("languageBtn");
// const languageMenu = document.getElementById("languageMenu");

// languageBtn.addEventListener("click", () => {
//     languageMenu.classList.toggle("show");
// });

// // Changer la langue
// document.querySelectorAll(".language-menu button").forEach(button => {
//     button.addEventListener("click", () => {
//         const lang = button.dataset.lang;

//         // Traduire les textes
//         document.querySelectorAll("[data-i18n]").forEach(element => {
//             const key = element.dataset.i18n;

//             if (translations[lang][key] !== undefined) {
//                 element.textContent = translations[lang][key];
//             }
//         });

//         // Changer la direction de la page
//         document.documentElement.lang = lang;
//         document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";

//         // Mettre à jour le bouton
//         const labels = {
//             fr: "🌐 FR",
//             en: "🌐 EN",
//             ar: "🌐 AR"
//         };

//         languageBtn.innerHTML = labels[lang] + " <span>⌄</span>";

//         // Fermer le menu
//         languageMenu.classList.remove("show");
//     });
// });

// // Fermer le menu en cliquant ailleurs
// document.addEventListener("click", (event) => {
//     if (!event.target.closest(".language-selector")) {
//         languageMenu.classList.remove("show");
//     }
// });
// ===== Calendrier historique =====
(function () {
  const calendarGrid = document.querySelector("#calendarGrid");
  if (!calendarGrid) return;

  const monthLabel = document.querySelector("#calendarMonth");
  const yearLabel = document.querySelector("#calendarYear");
  const selectedLabel = document.querySelector("#calendarSelection");
  const historyDate = document.querySelector("#historyDate");
  const historyStatus = document.querySelector("#historyStatus");
  const historyResults = document.querySelector("#historyResults");

  const today = new Date();
  today.setHours(12, 0, 0, 0);
  let selectedDate = new Date(today);
  let displayedMonth = new Date(today.getFullYear(), today.getMonth(), 1, 12);

  const pad = (n) => String(n).padStart(2, "0");
  const toISODate = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  const formatLongDate = (d) => new Intl.DateTimeFormat("fr-MA", {
    weekday: "long", day: "numeric", month: "long", year: "numeric",
  }).format(d);
  const daysInMonth = (y, m) => new Date(y, m + 1, 0).getDate();

  function renderCalendar() {
    if (monthLabel) monthLabel.textContent = new Intl.DateTimeFormat("fr-MA", { month: "long" }).format(displayedMonth);
    if (yearLabel) yearLabel.textContent = String(displayedMonth.getFullYear());

    const firstDay = new Date(displayedMonth.getFullYear(), displayedMonth.getMonth(), 1, 12);
    const mondayOffset = (firstDay.getDay() + 6) % 7;
    const monthLength = daysInMonth(displayedMonth.getFullYear(), displayedMonth.getMonth());
    const selectedISO = toISODate(selectedDate);
    const todayISO = toISODate(today);
    const cells = [];

    for (let i = 0; i < 42; i++) {
      const day = i - mondayOffset + 1;
      if (day < 1 || day > monthLength) {
        cells.push('<span class="cal__day is-outside" aria-hidden="true"></span>');
        continue;
      }
      const date = new Date(displayedMonth.getFullYear(), displayedMonth.getMonth(), day, 12);
      const iso = toISODate(date);
      const classes = ["cal__day"];
      if (iso === todayISO) classes.push("is-today");
      if (iso === selectedISO) classes.push("is-selected");
      cells.push(`<button class="${classes.join(" ")}" type="button" data-date="${iso}" aria-label="${formatLongDate(date)}" aria-pressed="${iso === selectedISO}" tabindex="${iso === selectedISO ? "0" : "-1"}">${day}</button>`);
    }
    calendarGrid.innerHTML = cells.join("");
  }

  function selectDate(date, moveCalendar = true) {
    selectedDate = new Date(date.getFullYear(), date.getMonth(), date.getDate(), 12);
    if (moveCalendar) displayedMonth = new Date(selectedDate.getFullYear(), selectedDate.getMonth(), 1, 12);
    if (historyDate) historyDate.value = toISODate(selectedDate);
    if (selectedLabel) selectedLabel.textContent = new Intl.DateTimeFormat("fr-MA", { day: "numeric", month: "short" }).format(selectedDate);
    if (historyStatus) historyStatus.textContent = `Date sélectionnée : ${formatLongDate(selectedDate)}.`;
    if (historyResults) historyResults.textContent = "Les archives d’incendies ne sont pas encore reliées à cette maquette.";
    renderCalendar();
  }

  calendarGrid.addEventListener("click", (event) => {
    const btn = event.target.closest("button[data-date]");
    if (!btn) return;
    const [y, m, d] = btn.dataset.date.split("-").map(Number);
    selectDate(new Date(y, m - 1, d, 12));
  });

  document.querySelectorAll("[data-calendar-nav]").forEach((button) => {
    button.addEventListener("click", () => {
      displayedMonth = new Date(displayedMonth.getFullYear(), displayedMonth.getMonth() + Number(button.dataset.calendarNav), 1, 12);
      renderCalendar();
    });
  });

  document.querySelector("#calendarToday")?.addEventListener("click", () => selectDate(today));

  calendarGrid.addEventListener("keydown", (event) => {
    const btn = event.target.closest("button[data-date]");
    if (!btn) return;
    const [y, m, d] = btn.dataset.date.split("-").map(Number);
    const current = new Date(y, m - 1, d, 12);
    const next = new Date(current);

    if (event.key === "ArrowLeft") next.setDate(next.getDate() - 1);
    else if (event.key === "ArrowRight") next.setDate(next.getDate() + 1);
    else if (event.key === "ArrowUp") next.setDate(next.getDate() - 7);
    else if (event.key === "ArrowDown") next.setDate(next.getDate() + 7);
    else if (event.key === "Home") next.setDate(next.getDate() - ((next.getDay() + 6) % 7));
    else if (event.key === "End") next.setDate(next.getDate() + (6 - ((next.getDay() + 6) % 7)));
    else if (event.key === "PageUp" || event.key === "PageDown") {
      const delta = event.key === "PageUp" ? -1 : 1;
      next.setDate(1);
      next.setMonth(current.getMonth() + delta);
      next.setDate(Math.min(d, daysInMonth(next.getFullYear(), next.getMonth())));
    } else return;

    event.preventDefault();
    selectDate(next);
    calendarGrid.querySelector(`[data-date="${toISODate(next)}"]`)?.focus();
  });

  if (historyDate) historyDate.value = toISODate(today);
  if (selectedLabel) selectedLabel.textContent = "Aujourd’hui";
  renderCalendar();
})();