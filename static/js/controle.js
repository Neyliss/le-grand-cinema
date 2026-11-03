/* Contrôle à l'entrée (E6-US2) : un billet déjà scanné est refusé avec un message clair. */
(function () {
  const form = document.getElementById("form-controle");
  const champ = document.getElementById("code");
  const zone = document.getElementById("resultat");
  const compteur = document.getElementById("compteur");
  const jauge = document.getElementById("jauge");
  let dernier = { code: "", heure: 0 };

  function afficher(r, code) {
    const carte = document.createElement("div");
    carte.className = `resultat resultat--${r.resultat}`;
    const titre = document.createElement("strong");
    titre.textContent = (r.resultat === "valide" ? "✓ " : r.resultat === "annule" ? "↺ " : "✕ ") + r.titre;
    const detail = document.createElement("p");
    detail.textContent = r.detail;
    carte.append(titre, detail);
    if (r.resultat === "valide") {
      // Erreur de scan : l'agent peut annuler cette entrée (10 minutes au plus).
      const annuler = document.createElement("button");
      annuler.type = "button";
      annuler.className = "bouton bouton--clair";
      annuler.textContent = "Annuler cette entrée";
      annuler.addEventListener("click", () => envoyer(form.dataset.urlAnnuler, code));
      carte.append(annuler);
    }
    zone.replaceChildren(carte);
    compteur.textContent = `${r.compteur.entrees} / ${r.compteur.vendus}`;
    jauge.style.width = `${r.compteur.vendus ? Math.round((100 * r.compteur.entrees) / r.compteur.vendus) : 0}%`;
  }

  async function envoyer(url, code) {
    const donnees = new FormData(form);
    donnees.set("code", code);
    const reponse = await fetch(url, { method: "POST", body: donnees });
    afficher(await reponse.json(), code);
    champ.value = "";
    champ.focus();
  }

  async function verifier(code) {
    code = code.trim();
    if (!code) return;
    // Évite de scanner deux fois de suite le même billet par erreur (caméra)
    if (code === dernier.code && Date.now() - dernier.heure < 3000) return;
    dernier = { code, heure: Date.now() };
    await envoyer(form.action, code);
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
