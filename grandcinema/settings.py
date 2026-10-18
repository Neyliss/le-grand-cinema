"""
Réglages du projet « Le Grand Cinéma ».

Tous les réglages sensibles ou propres à un environnement (clés, base de données,
e-mails, Stripe, S3) viennent de variables d'environnement. En local, elles sont
lues dans le fichier .env (voir .env.example). Sur AWS, elles sont définies dans
l'environnement Elastic Beanstalk (gc-prod).
"""
import os
from pathlib import Path

from django.utils.translation import gettext_lazy as _

BASE_DIR = Path(__file__).resolve().parent.parent

# Lecture du fichier .env en local (facultatif)
try:
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env")
except ImportError:  # python-dotenv absent : on se contente des variables d'environnement
    pass


def env_bool(nom, defaut=False):
    return os.environ.get(nom, str(defaut)).lower() in ("1", "true", "yes", "oui")


def env_liste(nom, defaut=""):
    return [v.strip() for v in os.environ.get(nom, defaut).split(",") if v.strip()]


# --- Sécurité ---------------------------------------------------------------
DEBUG = env_bool("DEBUG", False)
SECRET_KEY = os.environ.get("SECRET_KEY", "")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "cle-de-developpement-a-ne-jamais-utiliser-en-production"
    else:
        raise RuntimeError("La variable SECRET_KEY doit être définie en production.")

ALLOWED_HOSTS = env_liste("ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_liste("CSRF_TRUSTED_ORIGINS")

# --- Applications ------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Les six modules de l'application (dossier 3, figure 7)
    "catalogue",
    "reservation",
    "paiement",
    "billetterie",
    "guichet",
    "pilotage",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",  # français / anglais
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

if not DEBUG:
    # En production, WhiteNoise sert les fichiers statiques (mis en cache ensuite par CloudFront)
    MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")

ROOT_URLCONF = "grandcinema.urls"
WSGI_APPLICATION = "grandcinema.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.i18n",
                "grandcinema.context_processors.langues",  # sélecteur FR / EN
            ],
        },
    },
]

# --- Base de données ---------------------------------------------------------
# Local : SQLite par défaut. Production : PostgreSQL (Amazon RDS, composant C4)
# via DATABASE_URL, par exemple postgres://utilisateur:motdepasse@hote:5432/grandcinema
if os.environ.get("DATABASE_URL"):
    import dj_database_url

    DATABASES = {"default": dj_database_url.parse(os.environ["DATABASE_URL"], conn_max_age=60)}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "admin:login"

# --- Langues (EPIC E1 : site en français et en anglais) -----------------------
LANGUAGE_CODE = "fr"
LANGUAGES = [("fr", _("Français")), ("en", _("Anglais"))]
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = os.environ.get("TIME_ZONE") or "Europe/Paris"
USE_I18N = True
USE_TZ = True

# --- Fichiers statiques et fichiers envoyés ----------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
if DEBUG:
    # En développement, pas besoin de « collectstatic »
    STORAGES["staticfiles"] = {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}

# Production : affiches et billets PDF dans Amazon S3 (composant C5)
AWS_STORAGE_BUCKET_NAME = os.environ.get("AWS_STORAGE_BUCKET_NAME", "")
if AWS_STORAGE_BUCKET_NAME:
    AWS_S3_REGION_NAME = os.environ.get("AWS_S3_REGION_NAME") or "eu-west-3"
    AWS_DEFAULT_ACL = None
    AWS_QUERYSTRING_AUTH = True  # liens temporaires : les billets ne sont pas publics
    STORAGES["default"] = {"BACKEND": "storages.backends.s3.S3Storage"}

# --- E-mails (composant C6 : Amazon SES) --------------------------------------
# Local : les e-mails s'affichent dans le terminal. Production : SMTP d'Amazon SES.
EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND") or "django.core.mail.backends.console.EmailBackend"
EMAIL_HOST = os.environ.get("EMAIL_HOST") or "email-smtp.eu-west-3.amazonaws.com"
EMAIL_PORT = int(os.environ.get("EMAIL_PORT") or "587")
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL") or "Le Grand Cinéma <billets@legrandcinema.fr>"

# --- Paiement (composant C8 : Stripe) -----------------------------------------
# Sans clé Stripe, le site fonctionne en « mode démonstration » : le paiement est simulé.
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
PAIEMENT_DEMO = env_bool("PAIEMENT_DEMO", DEBUG and not STRIPE_SECRET_KEY)

# Adresse publique du site, utilisée dans les liens des e-mails
SITE_URL = os.environ.get("SITE_URL") or "http://127.0.0.1:8000"

# --- Règles métier ---------------------------------------------------------------
DUREE_BLOCAGE_MINUTES = 10  # E2-US2 : sièges bloqués 10 minutes pendant le paiement
PLACES_MAX_PAR_RESERVATION = 8
RAFRAICHISSEMENT_PLAN_SECONDES = 5  # E2-US1 : plan mis à jour toutes les 5 secondes

# --- Sécurité en production -----------------------------------------------------
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    # CloudFront (C2) termine le HTTPS et transmet ce en-tête au serveur (C3)
    SECURE_PROXY_SSL_HEADER = ("HTTP_CLOUDFRONT_FORWARDED_PROTO", "https")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
