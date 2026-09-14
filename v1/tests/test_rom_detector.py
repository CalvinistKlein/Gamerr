"""
Unit tests for ROM detector service
"""

import unittest
import tempfile
import os
from pathlib import Path
from services.rom_detector import ROMDetector


class TestROMDetector(unittest.TestCase):
    """Test cases for ROMDetector class"""
    
    def test_detect_platform_from_filename(self):
        """Test platform detection from filename"""
        test_cases = [
            ("Super Mario Bros.nes", "NES"),
            ("The Legend of Zelda.smc", "SNES"),
            ("Mario Kart 64.n64", "N64"),
            ("Super Mario Sunshine.gcm", "GameCube"),
            ("Super Mario Galaxy.wbfs", "Wii"),
            ("Super Mario Odyssey.nsp", "Switch"),
            ("Pokemon Red.gb", "Game Boy"),
            ("Pokemon Crystal.gbc", "Game Boy Color"),
            ("Pokemon Emerald.gba", "Game Boy Advance"),
            ("New Super Mario Bros.nds", "DS"),
            ("Pokemon X.3ds", "3DS"),
            ("Sonic the Hedgehog.gen", "Genesis"),
            ("Final Fantasy VII.bin", "PlayStation"),
            ("God of War.iso", "PlayStation 2"),
            ("Uncharted 3.pkg", "PlayStation 3"),
            ("Spider-Man.pkg", "PlayStation 4"),
            ("Halo.xbe", "Xbox"),
            ("Gears of War.xex", "Xbox 360"),
            ("Street Fighter II.zip", "Arcade"),
        ]
        
        for filename, expected_platform in test_cases:
            with self.subTest(filename=filename):
                detected = ROMDetector.detect_platform_from_filename(filename)
                self.assertEqual(detected, expected_platform)
    
    def test_detect_region_from_filename(self):
        """Test region detection from filename"""
        test_cases = [
            ("Super Mario Bros (USA).nes", "USA"),
            ("Sonic the Hedgehog (Europe).gen", "Europe"),
            ("Final Fantasy (Japan).bin", "Japan"),
            ("Street Fighter II (Asia).zip", "Asia"),
            ("Croc (Australia).iso", "Australia"),
            ("Super Mario Bros (US).nes", "USA"),
            ("Sonic (EU).gen", "Europe"),
            ("Final Fantasy (JP).bin", "Japan"),
            ("Street Fighter (AS).zip", "Asia"),
            ("Croc (AU).iso", "Australia"),
        ]
        
        for filename, expected_region in test_cases:
            with self.subTest(filename=filename):
                detected = ROMDetector.detect_region_from_filename(filename)
                self.assertEqual(detected, expected_region)
    
    def test_extract_title_from_filename(self):
        """Test title extraction from filename"""
        test_cases = [
            ("Super Mario Bros (USA).nes", "Super Mario Bros"),
            ("The Legend of Zelda - A Link to the Past (Europe).smc", "The Legend Of Zelda A Link To The Past"),
            ("Final Fantasy VII (Japan) [Disc1].bin", "Final Fantasy Vii"),
            ("Sonic The Hedgehog 2 (World).gen", "Sonic The Hedgehog 2"),
            ("Street Fighter II - Champion Edition (Arcade).zip", "Street Fighter Ii Champion Edition"),
        ]
        
        for filename, expected_title in test_cases:
            with self.subTest(filename=filename):
                extracted = ROMDetector.extract_title_from_filename(filename)
                self.assertEqual(extracted, expected_title)
    
    def test_detect_file_info(self):
        """Test comprehensive file info detection"""
        # Create a temporary file for testing
        with tempfile.NamedTemporaryFile(suffix='.nes', delete=False) as tmp:
            tmp.write(b'test data')
            tmp_path = tmp.name
        
        try:
            # Test detection
            file_info = ROMDetector.detect_file_info(tmp_path)
            
            # Check expected fields
            self.assertIn('filename', file_info)
            self.assertIn('file_path', file_info)
            self.assertIn('file_size', file_info)
            self.assertIn('detected_title', file_info)
            self.assertIn('detected_platform', file_info)
            self.assertIn('detected_region', file_info)
            self.assertIn('detected_year', file_info)
            
            # Check specific values
            self.assertEqual(file_info['detected_platform'], 'NES')
            self.assertTrue(file_info['filename'].endswith('.nes'))
        finally:
            # Clean up
            os.unlink(tmp_path)
    
    def test_unknown_platform(self):
        """Test detection of unknown platform"""
        # Test with unknown extension
        detected = ROMDetector.detect_platform_from_filename("unknown_file.txt")
        self.assertIsNone(detected)
        
        # Test with no extension
        detected = ROMDetector.detect_platform_from_filename("filename")
        self.assertIsNone(detected)
    
    def test_unknown_region(self):
        """Test detection of unknown region"""
        detected = ROMDetector.detect_region_from_filename("Game with no region.nes")
        self.assertIsNone(detected)


if __name__ == '__main__':
    unittest.main()