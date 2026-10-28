"""Supervision d'un atelier : référentiel des machines, relevés capteurs, alertes et rapport."""
import csv
import json
import math
import re
from datetime import datetime
from pathlib import Path

from exceptions import FichierInvalide, ReleveInvalide

COLONNES = ("machine", "horodatage", "temperature", "vibration")

# Un relevé valide est un tuple : (machine, horodatage, temperature, vibration)
Releve = tuple[str, datetime, float, float]


# --- Étape 1 : le référentiel des machines (JSON, dictionnaires, ensembles) --------------------
def charger_machines(chemin):
    with open(chemin, "r", encoding="utf-8") as f:
        fiches = json.load(f)

    machines = {}

    for fiche in fiches:
        identifiant = fiche["id"]

        if identifiant in machines:
            raise FichierInvalide(
                f"identifiant en double : {identifiant}"
            )

        machines[identifiant] = fiche

    return machines


def ateliers(machines):
    return {fiche["atelier"] for fiche in machines.values()}

# --- Étape 3 : valider une ligne (exceptions, tuples) -------------------------------------------

def lire_nombre(texte, champ, numero):
    if not texte.strip():
        raise ReleveInvalide("valeur manquante", numero, champ)

    texte = texte.strip().replace(",", ".")

    try:
        valeur = float(texte)
    except ValueError:
        raise ReleveInvalide(
            f"valeur non numérique : {texte!r}", numero, champ
        ) from None

    if not math.isfinite(valeur):
        raise ReleveInvalide(
            f"valeur non finie : {texte!r}", numero, champ
        )

    return valeur

def parser_releve(brut, numero, machines):
    machine = brut["machine"].strip().upper()

    if machine not in machines:
        raise ReleveInvalide(
            f"machine inconnue : {machine!r}", numero, "machine"
        )

    texte_date = brut["horodatage"].strip()

    try:
        horodatage = datetime.fromisoformat(texte_date)
    except ValueError:
        raise ReleveInvalide(
            f"horodatage invalide : {texte_date!r}",
            numero,
            "horodatage",
        ) from None

    temperature = lire_nombre(brut["temperature"], "temperature", numero)
    vibration = lire_nombre(brut["vibration"], "vibration", numero)

    if vibration < 0:
        raise ReleveInvalide(
            f"vibration négative :{vibration}", numero, "vibration"
        )

    return machine, horodatage, temperature, vibration



# --- Étape 4 : lire le fichier (CSV, générateur, collecte des erreurs) ---------------------------

def lignes_csv(chemin):
    with open(chemin, "r", encoding="utf-8-sig", newline="") as f:
        lecteur = csv.DictReader(f, delimiter=";")

        if lecteur.fieldnames is None:
            raise FichierInvalide(
                f"colonnes manquantes : {', '.join(COLONNES)}"
            )

        manquantes = [colonne for colonne in COLONNES
                      if colonne not in lecteur.fieldnames]

        if manquantes:
            raise FichierInvalide(
                f"colonnes manquantes : {', '.join(manquantes)}"
            )

        for numero, brut in enumerate(lecteur, start=2):
            yield numero, brut




def lire_releves(chemin, machines):
    releves = []
    erreurs = []

    for numero, brut in lignes_csv(chemin):
        try:
            releve = parser_releve(brut, numero, machines)
            releves.append(releve)
        except ReleveInvalide as err:
            erreurs.append(err)

    return releves, erreurs



def ecrire_rejets(erreurs, chemin):
    with open(chemin, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(["ligne", "champ", "message"])

        for err in erreurs:
            writer.writerow([err.ligne, err.champ, err.message])


# --- Étape 5 : analyser (dictionnaires, compréhensions) ------------------------------------------

def par_machine(releves):
    groupes = {}

    for releve in releves:
        machine = releve[0]
        groupes.setdefault(machine, []).append(releve)

    return groupes




def moyennes(releves):
    groupes = par_machine(releves)

    return {
        machine: (
            round(sum(r[2] for r in liste) / len(liste), 1),
            round(sum(r[3] for r in liste) / len(liste), 2),
        )
        for machine, liste in groupes.items()
    }




def alertes(releves, machines):
    alertes_temp = [
        (
            machine,
            horodatage,
            f"température {temperature} > {machines[machine]['temp_max']}",
        )
        for machine, horodatage, temperature, vibration in releves
        if temperature > machines[machine]["temp_max"]
    ]

    alertes_vib = [
        (
            machine,
            horodatage,
            f"vibration {vibration} > {machines[machine]['vib_max']}",
        )
        for machine, horodatage, temperature, vibration in releves
        if vibration > machines[machine]["vib_max"]
    ]

    return sorted(
        alertes_temp + alertes_vib,
        key=lambda a: (a[1], a[0]),
    )




def machines_silencieuses(releves, machines):
    machines_connues = set(machines)
    machines_avec_releves = {r[0] for r in releves}

    return machines_connues - machines_avec_releves



# --- Étape 6 : trier ---------------------------------------------------------------------------

def classement(releves, machines):
    compteurs = {machine: 0 for machine in machines}

    for machine, horodatage, message in alertes(releves, machines):
        compteurs[machine] += 1

    return sorted(
        compteurs.items(),
        key=lambda element: (-element[1], element[0])
    )




def top_vibrations(releves, n=3):
    return sorted(
        releves,
        key=lambda releve: releve[3],
        reverse=True
    )[:n]



# --- Étape 7 : le rapport JSON ------------------------------------------------------------------


def construire_rapport(releves, erreurs, machines):
    moyennes_calculees = moyennes(releves)
    liste_alertes = alertes(releves, machines)
    classement_calcule = classement(releves, machines)

    return {
        "releves_valides": len(releves),
        "lignes_rejetees": len(erreurs),
        "moyennes": {
            machine: {
                "temperature": valeurs[0],
                "vibration": valeurs[1],
            }
            for machine, valeurs in sorted(moyennes_calculees.items())
        },
        "alertes": [
            {
                "machine": machine,
                "heure": horodatage.strftime("%H:%M"),
                "motif": motif,
            }
            for machine, horodatage, motif in liste_alertes
        ],
        "classement": [
            machine
            for machine, nombre in classement_calcule
            if nombre > 0
        ],
        "machines_silencieuses": sorted(
            machines_silencieuses(releves, machines)
        ),
    }




def ecrire_rapport(rapport, chemin):
    chemin = Path(chemin)
    chemin.parent.mkdir(parents=True, exist_ok=True)

    with chemin.open("w", encoding="utf-8") as fichier:
        json.dump(
            rapport,
            fichier,
            ensure_ascii=False,
            indent=2
        )



# --- Étape 8 (à la maison) : le journal des événements (expressions régulières) ------------------

MOTIF_EVENEMENT = re.compile(
    r"(?P<date>\d{4}-\d{2}-\d{2}) "
    r"(?P<heure>\d{2}:\d{2}:\d{2}) "
    r"\[(?P<machine>M-\d{2})\] "
    r"(?P<type>[A-Z]+) "
    r"code=(?P<code>[A-Z]\d{2})"
    r"(?: duree=(?P<duree>\d+))?"
)




def lire_evenements(chemin):
    with open(chemin, encoding="utf-8") as fichier:
        for ligne in fichier:
            resultat = MOTIF_EVENEMENT.fullmatch(ligne.strip())

            if resultat is not None:
                donnees = resultat.groupdict()
                duree = donnees["duree"]

                yield {
                    "machine": donnees["machine"],
                    "type": donnees["type"],
                    "code": donnees["code"],
                    "heure": donnees["heure"],
                    "duree": int(duree) if duree is not None else None,
                }




def temps_arret(evenements) -> dict[str, int]:
    """Durée totale des ARRET par machine, en minutes."""
    totaux = {}

    for evenement in evenements:
        if evenement["type"] == "ARRET" and evenement["duree"] is not None:
            machine = evenement["machine"]
            duree = evenement["duree"]

            totaux[machine] = totaux.get(machine, 0) + duree

    return totaux
