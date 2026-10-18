"""Point d'entrée WSGI utilisé par Gunicorn sur le serveur applicatif (C3)."""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "grandcinema.settings")
application = get_wsgi_application()
