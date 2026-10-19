# Image Docker de l'application Le Grand Cinéma (voir docs/guide-docker.md).
# Construire : docker build -t le-grand-cinema .
FROM python:3.12-slim

# Python n'écrit pas de fichiers .pyc et affiche ses messages sans attendre
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# 1. Les bibliothèques d'abord : cette étape reste en cache tant que requirements.txt ne change pas
COPY requirements.txt .
RUN pip install -r requirements.txt

# 2. Puis le code du projet (les fichiers listés dans .dockerignore sont exclus)
COPY . .

# 3. Fichiers statiques rassemblés une fois pour toutes (servis ensuite par WhiteNoise)
RUN DEBUG=False SECRET_KEY=construction-de-l-image python manage.py collectstatic --noinput

# 4. L'application ne tourne pas en administrateur (root) : bonne pratique de sécurité
RUN useradd --create-home --uid 1000 cinema \
    && mkdir -p /app/media \
    && chown -R cinema /app/media
USER cinema

EXPOSE 8000
ENTRYPOINT ["sh", "/app/docker/entrypoint.sh"]
# Commande par défaut : serveur de production Gunicorn (comme sur Elastic Beanstalk)
CMD ["gunicorn", "grandcinema.wsgi", "--bind", "0.0.0.0:8000", "--workers", "2", "--threads", "4", "--timeout", "60"]
