/* Vente au guichet (E6-US1) : même plan, même stock que le site. */
(function () {
  const conteneur = document.getElementById("plan");
  const lignes = document.getElementById("lignes-panier");
  const vide = document.getElementById("panier-vide");
  const total = document.getElementById("total-panier");
  const boutons = document.querySelectorAll("[data-action]");
  const tarifs = JSON.parse(document.getElementById("tarifs").textContent);
  const format = new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" });
  const choix = new Map(); // id du siège -> id du tarif

  const majTotal = () => {
    let somme = 0;
    lignes.querySelectorAll("select").forEach((s) => {
      const tarif = tarifs.find((t) => String(t.id) === s.value);
      somme += Number(tarif.prix);
      s.closest(".ligne-panier").querySelector(".prix").textContent = format.format(Number(tarif.prix));
    });
    total.textContent = format.format(somme);
  };

  const plan = new PlanDeSalle(conteneur, {
    surChangement(sieges) {
      lignes.replaceChildren(...sieges.map((s) => {
        const ligne = document.createElement("div");
        ligne.className = "ligne-panier";
        const code = document.createElement("strong");
        code.textContent = `${s.rangee}${s.numero}`;
        const cache = document.createElement("input");
        cache.type = "hidden"; cache.name = "sieges"; cache.value = s.id;
        const select = document.createElement("select");
        select.name = `tarif_${s.id}`;
        select.setAttribute("aria-label", `Tarif du siège ${s.rangee}${s.numero}`);
        for (const t of tarifs) select.add(new Option(t.libelle, t.id));
        select.value = choix.get(s.id) || String(tarifs[0].id);
        select.addEventListener("change", () => { choix.set(s.id, select.value); majTotal(); });
        const prix = document.createElement("span");
        prix.className = "prix";
        ligne.append(code, select, prix, cache);
        return ligne;
      }));
      vide.hidden = sieges.length > 0;
      boutons.forEach((b) => { b.disabled = sieges.length === 0; });
      majTotal();
    },
    surPerte(code) {
      afficherMessage(`Le siège ${code} vient d'être pris en ligne : il a été retiré de la vente.`);
    },
  });
  const original = plan.afficher.bind(plan);
  plan.afficher = (donnees) => {
    original(donnees);
    document.getElementById("nb-libres").textContent = donnees.libres;
  };
  plan.demarrer(JSON.parse(document.getElementById("plan-initial").textContent));
})();
