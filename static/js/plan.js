/*
 * Plan de salle interactif (EPIC E2), utilisé par le site et par le guichet.
 * Le plan est relu en JSON toutes les 5 secondes : un siège vendu au guichet
 * disparaît du plan en ligne en moins de 5 secondes (critère de E2-US1).
 */
class PlanDeSalle {
  constructor(conteneur, options = {}) {
    this.conteneur = conteneur;
    this.url = conteneur.dataset.url;
    this.max = Number(conteneur.dataset.max || 8);
    this.intervalle = Number(conteneur.dataset.intervalle || 5) * 1000;
    this.libelleSiege = conteneur.dataset.libelleSiege || "Siège";
    this.selection = new Map();   // identifiant du siège -> { id, rangee, numero }
    this.boutons = new Map();     // identifiant du siège -> bouton
    this.statuts = new Map();     // identifiant du siège -> statut connu
    this.surChangement = options.surChangement || (() => {});
    this.surPerte = options.surPerte || (() => {});
  }

  demarrer(planInitial) {
    if (planInitial) this.afficher(planInitial); else this.charger();
    setInterval(() => { if (!document.hidden) this.charger(); }, this.intervalle);
    document.addEventListener("visibilitychange", () => { if (!document.hidden) this.charger(); });
  }

  async charger() {
    try {
      const reponse = await fetch(this.url, { headers: { Accept: "application/json" }, cache: "no-store" });
      if (reponse.ok) this.afficher(await reponse.json());
    } catch (erreur) {
      // Réseau coupé : on réessaiera au prochain rafraîchissement.
    }
  }

  construire(plan) {
    const allees = new Set(plan.allees);
    const grille = document.createElement("div");
    grille.className = "plan__grille";
    for (const rangee of plan.rangees) {
      const ligne = document.createElement("div");
      ligne.className = "rangee";
      ligne.append(this.nomRangee(rangee.nom));
      for (const siege of rangee.sieges) {
        const bouton = document.createElement("button");
        bouton.type = "button";
        bouton.className = "siege";
        if (siege.type === "pmr") bouton.classList.add("siege--pmr");
        if (allees.has(siege.numero)) bouton.classList.add("siege--allee");
        bouton.setAttribute("aria-label", `${this.libelleSiege} ${rangee.nom}${siege.numero}${siege.type === "pmr" ? " (PMR)" : ""}`);
        bouton.setAttribute("aria-pressed", "false");
        bouton.addEventListener("click", () => this.basculer({ id: siege.id, rangee: rangee.nom, numero: siege.numero }));
        this.boutons.set(siege.id, bouton);
        ligne.append(bouton);
      }
      ligne.append(this.nomRangee(rangee.nom));
      grille.append(ligne);
    }
    this.conteneur.replaceChildren(grille);
    // Taille des sièges adaptée à la largeur de l'écran (téléphone ou ordinateur)
    this.nbColonnes = Math.max(...plan.rangees.map((r) => r.sieges.length));
    this.nbAllees = plan.allees.length;
    this.ajusterTaille();
    window.addEventListener("resize", () => this.ajusterTaille());
  }

  ajusterTaille() {
    const largeur = this.conteneur.clientWidth - 2 * 18 - 20;
    const unites = this.nbColonnes + (this.nbColonnes + 1) * 0.25 + this.nbAllees * 0.6;
    const taille = Math.max(12, Math.min(28, Math.floor(largeur / unites)));
    this.conteneur.style.setProperty("--siege", `${taille}px`);
    this.conteneur.style.setProperty("--ecart", `${Math.max(3, Math.round(taille * 0.25))}px`);
  }

  nomRangee(nom) {
    const span = document.createElement("span");
    span.className = "rangee__nom";
    span.textContent = nom;
    span.setAttribute("aria-hidden", "true");
    return span;
  }

  afficher(plan) {
    const premiereFois = this.boutons.size === 0;
    if (premiereFois) this.construire(plan);
    for (const rangee of plan.rangees) {
      for (const siege of rangee.sieges) {
        const bouton = this.boutons.get(siege.id);
        if (!bouton) continue;
        const ancien = this.statuts.get(siege.id);
        this.statuts.set(siege.id, siege.statut);
        const choisi = this.selection.has(siege.id);
        if (choisi && siege.statut !== "libre") {
          // Pris entre-temps par quelqu'un d'autre (site ou guichet) : on le retire de la sélection.
          this.selection.delete(siege.id);
          bouton.setAttribute("aria-pressed", "false");
          this.surPerte(`${rangee.nom}${siege.numero}`);
          this.surChangement(this.liste());
        }
        bouton.classList.toggle("siege--vendue", siege.statut === "vendue");
        bouton.classList.toggle("siege--bloquee", siege.statut === "bloquee");
        bouton.disabled = siege.statut !== "libre" || !plan.reservable;
        if (!premiereFois && ancien && ancien !== siege.statut) {
          bouton.classList.remove("siege--change");
          void bouton.offsetWidth; // relance l'animation
          bouton.classList.add("siege--change");
        }
      }
    }
  }

  basculer(siege) {
    const bouton = this.boutons.get(siege.id);
    if (this.selection.has(siege.id)) {
      this.selection.delete(siege.id);
      bouton.setAttribute("aria-pressed", "false");
    } else {
      if (this.selection.size >= this.max || this.statuts.get(siege.id) !== "libre") return;
      this.selection.set(siege.id, siege);
      bouton.setAttribute("aria-pressed", "true");
    }
    this.surChangement(this.liste());
  }

  liste() {
    return [...this.selection.values()].sort((a, b) => a.rangee.localeCompare(b.rangee) || a.numero - b.numero);
  }

  vider() {
    for (const id of this.selection.keys()) this.boutons.get(id)?.setAttribute("aria-pressed", "false");
    this.selection.clear();
    this.surChangement([]);
  }
}

// Affiche un message temporaire en haut de la page.
function afficherMessage(texte, type = "error") {
  let zone = document.querySelector(".messages");
  if (!zone) {
    zone = document.createElement("div");
    zone.className = "messages";
    zone.setAttribute("role", "status");
    document.querySelector("main").prepend(zone);
  }
  const message = document.createElement("p");
  message.className = `message message--${type}`;
  message.textContent = texte;
  zone.append(message);
  setTimeout(() => message.remove(), 7000);
}
