/* Étape 2 : compte à rebours du blocage de 10 minutes et calcul du total selon les tarifs choisis. */
(function () {
  const minuteur = document.getElementById("minuteur");
  const bouton = document.getElementById("bouton-payer");
  if (minuteur) {
    const fin = new Date(minuteur.dataset.fin).getTime();
    const affichage = minuteur.querySelector("strong");
    const tic = () => {
      const reste = Math.max(0, Math.round((fin - Date.now()) / 1000));
      affichage.textContent = `${String(Math.floor(reste / 60)).padStart(2, "0")}:${String(reste % 60).padStart(2, "0")}`;
      minuteur.classList.toggle("minuteur--urgent", reste > 0 && reste <= 120);
      if (reste === 0) {
        minuteur.classList.add("minuteur--fini");
        minuteur.querySelector("span").textContent = minuteur.dataset.texteFini;
        if (bouton) bouton.disabled = true;
        clearInterval(intervalle);
      }
    };
    const intervalle = setInterval(tic, 1000);
    tic();
  }

  const prix = JSON.parse(document.getElementById("prix-tarifs").textContent);
  const format = new Intl.NumberFormat(document.documentElement.lang, { style: "currency", currency: "EUR" });
  const selects = document.querySelectorAll("select[data-siege]");
  const total = document.getElementById("total");
  const lignes = document.getElementById("lignes-recap");
  const majTotal = () => {
    let somme = 0;
    lignes.replaceChildren();
    selects.forEach((select) => {
      const montant = Number(prix[select.value] || 0);
      somme += montant;
      document.getElementById(`prix-${select.dataset.siege}`).textContent = format.format(montant);
      const ligne = document.createElement("div");
      ligne.className = "recap__ligne";
      const libelle = document.createElement("span");
      libelle.textContent = `${select.dataset.siege} · ${select.options[select.selectedIndex].text}`;
      const valeur = document.createElement("span");
      valeur.textContent = format.format(montant);
      ligne.append(libelle, valeur);
      lignes.append(ligne);
    });
    total.textContent = format.format(somme);
  };
  selects.forEach((select) => select.addEventListener("change", majTotal));
  majTotal();
})();
