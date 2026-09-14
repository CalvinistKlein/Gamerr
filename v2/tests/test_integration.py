"""
Comprehensive Integration Tests for Romarr v2
Tests routes, API endpoints, model relationships, and import pipeline
"""

import unittest
import json
import tempfile
import os

from app import create_app
from extensions import db
from models.unified_schema import Game, GameCatalog, WantedGame, Download, Platform


class TestRomarrIntegration(unittest.TestCase):
    """Integration test suite covering web routes, API, and services"""
    
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.client = cls.app.test_client()

    def test_web_routes_render(self):
        """Verify all core HTML views render HTTP 200"""
        routes = ['/', '/catalog', '/library', '/wanted', '/downloads', '/settings', '/import']
        for r in routes:
            res = self.client.get(r)
            self.assertEqual(res.status_code, 200, f"Route {r} failed with status {res.status_code}")

    def test_catalog_detail_view(self):
        """Verify individual catalog game page renders"""
        res = self.client.get('/catalog/1')
        self.assertEqual(res.status_code, 200)

    def test_library_platform_filter(self):
        """Verify platform filter does not fail with WHERE 0=1"""
        res = self.client.get('/library?platform=NES')
        self.assertEqual(res.status_code, 200)

    def test_api_health_and_stats(self):
        """Verify health check and stats API"""
        res = self.client.get('/api/health')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()['status'], 'healthy')

        res = self.client.get('/api/stats')
        self.assertEqual(res.status_code, 200)
        self.assertIn('library_count', res.get_json())

    def test_game_creation_and_setters(self):
        """Verify Game model sets platform, region, and auto-generates slug"""
        payload = {
            'title': 'Chrono Trigger',
            'platform': 'SNES',
            'region': 'USA',
            'release_year': 1995
        }
        res = self.client.post('/api/games', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertEqual(data['title'], 'Chrono Trigger')
        self.assertEqual(data['platform'], 'SNES')
        self.assertTrue(data['slug'].startswith('chrono-trigger'))

    def test_wanted_game_workflow(self):
        """Verify adding game to wanted list"""
        payload = {
            'game_title': 'Super Metroid',
            'platform': 'SNES',
            'region_preference': 'USA'
        }
        res = self.client.post('/api/wanted', data=json.dumps(payload), content_type='application/json')
        self.assertIn(res.status_code, (200, 201))

    def test_downloads_status_endpoint(self):
        """Verify /api/downloads/status works without attribute error"""
        with self.app.app_context():
            dl = Download(
                torrent_name='Chrono Trigger (USA).zip',
                torrent_hash='test_hash_001',
                size_bytes=4000000,
                progress=0.75,
                status='downloading'
            )
            db.session.add(dl)
            db.session.commit()

        res = self.client.get('/api/downloads/status')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(len(data) >= 1)
        self.assertIn('downloaded_bytes', data[0])

    def test_catalog_search_and_hybrid_search(self):
        """Verify local and hybrid search without catalog_id error"""
        res = self.client.get('/api/search/catalog?q=Mario')
        self.assertEqual(res.status_code, 200)

        res = self.client.post('/api/search', data=json.dumps({'query': 'Mario'}), content_type='application/json')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('results', data)

    def test_rom_scanner_and_importer_api(self):
        """Verify /api/import/scan and /api/import/process pipeline"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_id = os.urandom(4).hex()
            sample_file = os.path.join(tmpdir, f'MegaMan_{test_id}.nes')
            with open(sample_file, 'wb') as f:
                f.write(b'NES\x1a' + os.urandom(128))

            # 1. Scan
            res = self.client.post('/api/import/scan', data=json.dumps({'path': tmpdir}), content_type='application/json')
            self.assertEqual(res.status_code, 200)
            scan_data = res.get_json()
            self.assertTrue(scan_data['success'])
            self.assertEqual(len(scan_data['roms']), 1)
            self.assertEqual(scan_data['roms'][0]['detected_platform'], 'NES')

            # 2. Process
            res = self.client.post('/api/import/process', data=json.dumps({'roms': scan_data['roms']}), content_type='application/json')
            self.assertEqual(res.status_code, 200)
            proc_data = res.get_json()
            self.assertTrue(proc_data['success'])
            self.assertEqual(proc_data['imported'], 1)

    def test_generation_and_decade_filtering_with_pc_titles(self):
        """Verify cross-generation mapping includes console and PC titles from that era"""
        # 1. Gen 4 filter should return 200 and include both SNES and PC (DOS) titles
        res = self.client.get('/catalog?generation=4')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn('Super Mario World', html)
        self.assertIn('DOOM', html)

        # 2. Decade 1990s filter
        res = self.client.get('/catalog?decade=1990s')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn('1990', html)

    def test_catalog_view_modes(self):
        """Verify Sonarr/Radarr style poster grid and table views"""
        # Poster view
        res_posters = self.client.get('/catalog?view=posters')
        self.assertEqual(res_posters.status_code, 200)
        self.assertIn('arr-poster-grid', res_posters.get_data(as_text=True))

        # Table view
        res_table = self.client.get('/catalog?view=table')
        self.assertEqual(res_table.status_code, 200)
        self.assertIn('arr-table', res_table.get_data(as_text=True))


if __name__ == '__main__':
    unittest.main()
