"""Réglages de production (Elastic Beanstalk derrière CloudFront)."""
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, override_settings

from grandcinema.middleware import RedirectionVersSitePublic

SITE = "https://d1234.cloudfront.net"


@override_settings(SITE_URL=SITE, ALLOWED_HOSTS=[".elasticbeanstalk.com", ".cloudfront.net"],
                   SECURE_PROXY_SSL_HEADER=("HTTP_CLOUDFRONT_FORWARDED_PROTO", "https"))
class RedirectionVersSitePublicTests(SimpleTestCase):
    def passer(self, **entetes):
        middleware = RedirectionVersSitePublic(lambda request: HttpResponse("page"))
        return middleware(RequestFactory().get("/programmation/?jour=2026-11-05", **entetes))

    def test_une_visite_directe_du_serveur_est_renvoyee_vers_l_adresse_publique_en_https(self):
        reponse = self.passer(HTTP_HOST="gc-prod.eu-west-3.elasticbeanstalk.com")

        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(reponse["Location"], f"{SITE}/programmation/?jour=2026-11-05")

    def test_une_visite_par_cloudfront_en_https_est_servie_normalement(self):
        reponse = self.passer(HTTP_HOST="d1234.cloudfront.net", HTTP_CLOUDFRONT_FORWARDED_PROTO="https")

        self.assertEqual(reponse.content, b"page")

    @override_settings(SITE_URL="http://127.0.0.1:8000")
    def test_sans_adresse_publique_en_https_rien_n_est_redirige(self):
        reponse = self.passer(HTTP_HOST="gc-prod.eu-west-3.elasticbeanstalk.com")

        self.assertEqual(reponse.content, b"page")
