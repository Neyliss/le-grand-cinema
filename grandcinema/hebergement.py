"""Réglages qui dépendent de l'hébergeur (AWS par défaut, Render en secours).

Ces petites fonctions reçoivent les variables d'environnement et sont testées à part
(grandcinema/tests/test_hebergement.py)."""


def hotes_autorises(hotes, environnement):
    """Adresses par lesquelles le site accepte d'être appelé. Sur Render, l'adresse du site
    (…onrender.com) est donnée par Render lui-même dans RENDER_EXTERNAL_HOSTNAME."""
    hote_render = environnement.get("RENDER_EXTERNAL_HOSTNAME")
    return hotes + [hote_render] if hote_render else hotes


def adresse_publique(environnement):
    """Adresse publique du site : SITE_URL (AWS : le domaine CloudFront), sinon celle donnée par Render."""
    return environnement.get("SITE_URL") or environnement.get("RENDER_EXTERNAL_URL") or "http://127.0.0.1:8000"


def entete_https(environnement):
    """En-tête par lequel le proxy placé devant le serveur dit que la visite est en HTTPS :
    - AWS (par défaut) : CloudFront (C2) envoie CloudFront-Forwarded-Proto au serveur (C3) ;
    - Render (PROXY_HTTPS=standard) : son proxy envoie X-Forwarded-Proto."""
    if environnement.get("PROXY_HTTPS", "cloudfront") == "standard":
        return ("HTTP_X_FORWARDED_PROTO", "https")
    return ("HTTP_CLOUDFRONT_FORWARDED_PROTO", "https")
