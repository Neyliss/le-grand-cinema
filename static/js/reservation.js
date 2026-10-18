/* Étape 1 du parcours en ligne : sélection des places puis envoi du formulaire. */
(function () {
  const conteneur = document.getElementById("plan");
  if (!conteneur) return;
  const liste = document.getElementById("liste-selection");
  const vide = document.getElementById("selection-vide");
  const compte = document.getElementById("compte-selection");
  const champs = document.getElementById("champs-sieges");
  const bouton = document.getElementById("bouton-continuer");
  const textes = {
    une: conteneur.dataset.texteUne,
    plusieurs: conteneur.dataset.textePlusieurs,
    aucune: conteneur.dataset.texteAucune,
    rang: conteneur.dataset.texteRang,
  };

  const plan = new PlanDeSalle(conteneur, {
    surChangement(sieges) {
      liste.replaceChildren(...sieges.map((s) => {
        const li = document.createElement("li");
        const code = document.createElement("strong");
        code.textContent = `${s.rangee}${s.numero}`;
        const detail = document.createElement("span");
        detail.className = "muet petit";
        detail.textContent = textes.rang.replace("%r", s.rangee).replace("%n", s.numero);
        li.append(code, detail);
        return li;
      }));
      champs.replaceChildren(...sieges.map((s) => {
        const champ = document.createElement("input");
        champ.type = "hidden";
        champ.name = "sieges";
        champ.value = s.id;
        return champ;
      }));
      vide.hidden = sieges.length > 0;
      compte.textContent = sieges.length === 0 ? textes.aucune : sieges.length === 1 ? textes.une : textes.plusieurs.replace("%s", sieges.length);
      bouton.disabled = sieges.length === 0;
    },
    surPerte(code) {
      afficherMessage(conteneur.dataset.libellePris.replace("%s", code));
    },
  });
  plan.demarrer(JSON.parse(document.getElementById("plan-initial").textContent));
})();
