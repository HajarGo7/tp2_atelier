
from pathlib import Path

from atelier import (
    charger_machines,
    lire_releves,
    ecrire_rejets,
    construire_rapport,
    ecrire_rapport,
)
from exceptions import AtelierError


BASE_DIR = Path(__file__).resolve().parent
DONNEES = BASE_DIR / "donnees"
SORTIES = BASE_DIR / "sorties"


def main() -> int:
    """Renvoie 0 si tout s'est bien passé, 1 si un fichier est inutilisable."""

    try:
        machines = charger_machines(DONNEES / "machines.json")
        releves, erreurs = lire_releves(
            DONNEES / "releves.csv",
            machines,
        )
    except (AtelierError, FileNotFoundError) as erreur:
        print(f"Erreur : {erreur}")
        return 1

    SORTIES.mkdir(parents=True, exist_ok=True)

    ecrire_rejets(erreurs, SORTIES / "rejets.csv")

    rapport = construire_rapport(releves, erreurs, machines)
    ecrire_rapport(rapport, SORTIES / "rapport.json")

    print(
        f"{rapport['releves_valides']} relevés valides, "
        f"{rapport['lignes_rejetees']} lignes rejetées"
    )
    print(
        f"{len(rapport['alertes'])} alertes ; machines à surveiller : "
        f"{', '.join(rapport['classement'])}"
    )
    print(
        f"Sans relevé : "
        f"{', '.join(rapport['machines_silencieuses'])}"
    )
    print("Fichiers écrits dans sorties/ : rejets.csv, rapport.json")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

