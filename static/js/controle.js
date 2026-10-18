/* Contrôle à l'entrée (E6-US2) : un billet déjà scanné est refusé avec un message clair. */
(function () {
  const form = document.getElementById("form-controle");
  const champ = document.getElementById("code");
  const zone = document.getElementById("resultat");
  const compteur = document.getElementById("compteur");
  const jauge = document.getElementById("jauge");
  let dernier = { code: "", heure: 0 };

  async function verifier(code) {
    code = code.trim();
    if (!code) return;
    // Évite de scanner deux fois de suite le même billet par erreur (caméra)
    if (code === dernier.code && Date.now() - dernier.heure < 3000) return;
    dernier = { code, heure: Date.now() };
    const donnees = new FormData(form);
    donnees.set("code", code);
    const reponse = await fetch(form.action, { method: "POST", body: donnees });
    const r = await reponse.json();
    const carte = document.createElement("div");
    carte.className = `resultat resultat--${r.resultat}`;
    const titre = document.createElement("strong");
    titre.textContent = (r.resultat === "valide" ? "✓ " : "✕ ") + r.titre;
    const detail = document.createElement("p");
    detail.textContent = r.detail;
    carte.append(titre, detail);
    zone.replaceChildren(carte);
    compteur.textContent = `${r.compteur.entrees} / ${r.compteur.vendus}`;
    jauge.style.width = `${r.compteur.vendus ? Math.round((100 * r.compteur.entrees) / r.compteur.vendus) : 0}%`;
    champ.value = "";
    champ.focus();
  }

  form.addEventListener("submit", (e) => { e.preventDefault(); verifier(champ.value); });

  document.getElementById("activer-camera").addEventListener("click", () => {
    if (!window.Html5Qrcode) {
      zone.textContent = "Caméra indisponible : saisissez le code ou utilisez une douchette.";
      return;
    }
    const lecteur = new Html5Qrcode("camera");
    lecteur.start({ facingMode: "environment" }, { fps: 10, qrbox: 220 }, (texte) => verifier(texte))
      .catch(() => { zone.textContent = "Accès à la caméra refusé : saisissez le code du billet."; });
  });
})();
