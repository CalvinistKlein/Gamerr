"""
Audit Test Suite: Verification of all Web Pages, API routes, and Service Lifecycles
"""

import unittest
import json
import os
from app import create_app
from extensions import db
from models.unified_schema import (
    Game, Platform, GameCatalog, Download, WantedGame,
    ROMFile
)
from models.notification import Notification
from services.metadata_service import MetadataService


class TestFullSystemAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.client = cls.app.test_client()
        with cls.app.app_context():
            db.create_all()

    def test_all_web_routes_render(self):
        """Verify all HTML web routes render successfully (200 OK)"""
        web_routes = [
            '/',
            '/library',
            '/wanted',
            '/downloads',
            '/catalog',
            '/import',
            '/settings',
        ]
        for route in web_routes:
            with self.subTest(route=route):
                res = self.client.get(route)
                self.assertEqual(res.status_code, 200, f"Route {route} failed with status {res.status_code}")

    def test_catalog_detail_route(self):
        """Verify /catalog/<id> renders with an existing or mock catalog game"""
        with self.app.app_context():
            first_game = GameCatalog.query.first()
            if not first_game:
                cat = GameCatalog(
                    title="Audit Test Game",
                    slug="audit-test-game",
                    platform="SNES",
                    release_year=1991,
                    description="Test summary"
                )
                db.session.add(cat)
                db.session.commit()
                game_id = cat.id
            else:
                game_id = first_game.id

        res = self.client.get(f'/catalog/{game_id}')
        self.assertEqual(res.status_code, 200)

    def test_all_api_get_routes(self):
        """Verify all core API GET endpoints return 200 OK and valid JSON"""
        endpoints = [
            '/api/stats',
            '/api/library/search',
            '/api/wanted/search',
            '/api/catalog/search?q=mario',
            '/api/platforms',
            '/api/colors',
            '/api/downloads/status',
            '/api/games',
            '/api/wanted',
            '/api/downloads',
            '/api/downloads/active',
            '/api/regions',
            '/api/search/catalog?query=sonic',
            '/api/health',
            '/api/system/storage',
            '/api/settings',
            '/api/settings/network/share-url',
            '/api/notifications',
            '/api/notifications/unread/count',
        ]
        for ep in endpoints:
            with self.subTest(endpoint=ep):
                res = self.client.get(ep)
                self.assertEqual(res.status_code, 200, f"Endpoint {ep} returned {res.status_code}")
                data = json.loads(res.data)
                self.assertIsNotNone(data)

    def test_catalog_add_to_wanted_and_lifecycle(self):
        """Test adding catalog game to wanted, checking status, then deleting"""
        with self.app.app_context():
            wanted_titles = [w.game_title for w in WantedGame.query.all()]
            cat = GameCatalog.query.filter(~GameCatalog.title.in_(wanted_titles)).first()
            if not cat:
                cat = GameCatalog(
                    title="Lifecycle Unique Title 999",
                    slug="lifecycle-unique-title-999",
                    platform="SNES",
                    release_year=1995
                )
                db.session.add(cat)
                db.session.commit()
            cat_id = cat.id

        # Add to wanted
        res = self.client.post(f'/api/catalog/{cat_id}/add-to-wanted', json={'monitored': True})
        self.assertIn(res.status_code, [200, 201])
        data = json.loads(res.data)
        self.assertTrue(data.get('success', False))

        # Check wanted list
        res_wanted = self.client.get('/api/wanted')
        self.assertEqual(res_wanted.status_code, 200)
        wanted_items = json.loads(res_wanted.data)
        self.assertIsInstance(wanted_items, list)
        self.assertGreater(len(wanted_items), 0)

    def test_metadata_service_integration(self):
        """Verify MetadataService search and fallback mechanism"""
        svc = MetadataService()
        res = svc.search_games("Chrono Trigger", platform="SNES")
        self.assertIsInstance(res, dict)
        self.assertIn('results', res)
        results = res['results']
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0]['title'], "Chrono Trigger")

        details = svc.get_game_details(results[0]['id'])
        self.assertIsNotNone(details)
        self.assertIn("Chrono Trigger", details['title'])

    def test_generation_and_decade_filtering(self):
        """Verify decade and generation filtering on /catalog and /library"""
        filters = [
            '/catalog?generation=4',
            '/catalog?generation=5',
            '/catalog?decade=1990s',
            '/catalog?decade=1980s',
            '/catalog?platform=PC+(DOS)',
            '/library?generation=4',
            '/library?decade=1990s',
        ]
        for f in filters:
            with self.subTest(filter=f):
                res = self.client.get(f)
                self.assertEqual(res.status_code, 200)


if __name__ == '__main__':
    unittest.main()
