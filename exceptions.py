"""Les erreurs métier de l'application de supervision."""


class AtelierError(Exception):
    """Classe mère de toutes les erreurs de l'application."""


class FichierInvalide(AtelierError):
    """Le fichier entier est inutilisable (colonnes manquantes, identifiants en double...)."""



class ReleveInvalide(AtelierError):
    def __init__(self, message, ligne, champ):
        self.message = message
        self.ligne = ligne
        self.champ = champ
        super().__init__(f"ligne {ligne}, champ '{champ}' : {message}")
