const fires = [
  { name: "Sidi Yahya", forest: "Forêt de Maâmora", province: "Kénitra", status: "active", risk: "critical", hectares: 18, description: "Point chaud détecté par satellite, intervention en cours." },
  { name: "Akchour", forest: "Forêt de Talassemtane", province: "Chefchaouen", status: "active", risk: "high", hectares: 6, description: "Surveillance renforcée autour de la zone montagneuse." },
  { name: "Bab Boudir", forest: "Forêt de Tazekka", province: "Taza", status: "contained", risk: "moderate", hectares: 42, description: "Feu contenu, équipes présentes pour la surveillance." },
];

// Traduction (i18n.js) : renvoie le texte français tel quel si i18n.js n'est pas chargé.
const t = (texte, valeurs) => (window.wiqayaI18n ? window.wiqayaI18n.t(texte, valeurs) : texte);
const locale = () => (window.wiqayaI18n ? window.wiqayaI18n.locale() : "fr-MA");

const riskLabels = { critical: "Très élevé", high: "Élevé", moderate: "Maîtrisé" };
const feedList = document.querySelector("#feedList");
const popup = document.querySelector("#mapPopup");
const toast = document.querySelector("#locationToast");
const successMessage = document.querySelector("#successMessage");

function renderFeed() {
  if (!feedList) return;
  feedList.innerHTML = fires.map((fire, index) => `
    <button class="feed-item" data-fire="${index}">
      <span class="feed-thumb ${fire.risk}">♨</span>
      <div><strong>${t(fire.name)}</strong><span>${t(fire.province)} · ${fire.hectares} ${t("ha")}</span><small>${t("◷ Mise à jour il y a 12 min")}</small></div>
      <i class="feed-state ${fire.status}"></i>
    </button>
  `).join("");
  feedList.querySelectorAll("[data-fire]").forEach((item) => item.addEventListener("click", () => showFire(Number(item.dataset.fire))));
}

function showFire(index) {
  const fire = fires[index];
  if (!popup) return;
  document.querySelector("#popupRisk").textContent = t(riskLabels[fire.risk]);
  document.querySelector("#popupRisk").className = `risk-tag ${fire.risk}`;
  document.querySelector("#popupTitle").textContent = fire.name;
  document.querySelector("#popupLocation").textContent = `${fire.forest} · ${fire.province}`;
  document.querySelector("#popupDescription").textContent = fire.description;
  popup.hidden = false;
}

function requestLocation() {
  if (!navigator.geolocation) {
    window.alert(t("La géolocalisation n’est pas disponible sur cet appareil."));
    return;
  }
  navigator.geolocation.getCurrentPosition(() => {
    toast.hidden = true;
    window.alert(t("Localisation activée. Les alertes proches de vous seront prioritaires."));
  }, () => window.alert(t("Autorisation de localisation refusée par le navigateur.")), { enableHighAccuracy: true, timeout: 10000 });
}

document.querySelectorAll(".fire-pin").forEach((pin) => pin.addEventListener("click", () => showFire(Number(pin.dataset.fire))));
// La popup de démonstration (#mapPopup) est commentée dans index2.html : `?.` évite que le script s'arrête ici
// (sinon le formulaire d'alerte plus bas n'était jamais branché).
document.querySelector("#popupClose")?.addEventListener("click", () => { popup.hidden = true; });
document.querySelector("#mapLocation")?.addEventListener("click", requestLocation);
document.querySelector("#allowLocation")?.addEventListener("click", requestLocation);
document.querySelector("#dismissLocation")?.addEventListener("click", () => { toast.hidden = true; });
document.querySelector("#closeLocation")?.addEventListener("click", () => { toast.hidden = true; });
document.querySelector("#menuButton")?.addEventListener("click", () => { document.querySelector("#mainNav").classList.toggle("open"); });
document.querySelectorAll("#mainNav a").forEach((link) => link.addEventListener("click", () => document.querySelector("#mainNav").classList.remove("open")));
document.querySelectorAll(".banner-close").forEach((button) => button.addEventListener("click", () => button.closest(".info-banner").remove()));

document.querySelector("#alertForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const formElement = event.currentTarget; // event.currentTarget vaut null après le premier await
  const form = new FormData(formElement);
  const channels = [form.get("sms") ? "SMS" : "", form.get("emailChannel") ? "e-mail" : ""].filter(Boolean);
  if (!channels.length) {
    window.alert(t("Choisissez au moins un canal de notification."));
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
  formElement.reset();
  window.setTimeout(() => successMessage.classList.remove("show"), 5000);
});

document.querySelector("#updatedAt").textContent = new Date().toLocaleTimeString(locale(), { hour: "2-digit", minute: "2-digit" });
renderFeed();
window.addEventListener("wiqaya:langue", renderFeed);

