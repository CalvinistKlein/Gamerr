import os
import xml.etree.ElementTree as ET
import sqlite3
from datetime import datetime

class DatabaseBuilder:
    def __init__(self, db_path='romarr.db'):
        self.db_path = db_path

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def parse_mame_xml(self, xml_path):
        """Parse a MAME machine XML file and insert into the database."""
        if not os.path.exists(xml_path):
            print(f"File not found: {xml_path}")
            return False

        print(f"Parsing MAME XML from: {xml_path}")
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # Assuming 'Arcade' as the platform for MAME
                cursor.execute("INSERT OR IGNORE INTO platforms (name) VALUES (?)", ("Arcade",))
                cursor.execute("SELECT id FROM platforms WHERE name = ?", ("Arcade",))
                platform_id = cursor.fetchone()[0]

                count = 0
                for machine in root.findall('machine'):
                    if machine.get('isbios') == 'yes' or machine.get('isdevice') == 'yes':
                        continue # Skip BIOS and devices

                    name = machine.get('name')
                    description_elem = machine.find('description')
                    year_elem = machine.find('year')
                    manufacturer_elem = machine.find('manufacturer')

                    title = description_elem.text if description_elem is not None else name
                    year = int(year_elem.text) if year_elem is not None and year_elem.text.isdigit() else None
                    manufacturer = manufacturer_elem.text if manufacturer_elem is not None else None

                    # Insert basic game info
                    cursor.execute('''
                        INSERT OR IGNORE INTO games (title, release_year, summary, platform_id) 
                        VALUES (?, ?, ?, ?)
                    ''', (title, year, f"Manufacturer: {manufacturer}", platform_id))
                    
                    count += 1
                    if count % 1000 == 0:
                        print(f"Parsed {count} MAME entries...")

                conn.commit()
                print(f"Successfully processed {count} arcade machines.")
                return True
        except Exception as e:
            print(f"Error parsing MAME XML: {e}")
            return False

    def parse_nointro_dat(self, dat_path, platform_name):
        """Parse a No-Intro clrmamepro DAT file and insert into the database."""
        if not os.path.exists(dat_path):
            print(f"File not found: {dat_path}")
            return False

        print(f"Parsing No-Intro DAT for {platform_name} from: {dat_path}")
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT OR IGNORE INTO platforms (name) VALUES (?)", (platform_name,))
                cursor.execute("SELECT id FROM platforms WHERE name = ?", (platform_name,))
                platform_id = cursor.fetchone()[0]

                count = 0
                with open(dat_path, 'r', encoding='utf-8', errors='ignore') as f:
                    in_game_block = False
                    game_name = None
                    description = None

                    for line in f:
                        line = line.strip()
                        if line == "game (":
                            in_game_block = True
                            game_name = None
                            description = None
                        elif line == ")" and in_game_block:
                            if game_name:
                                title = description if description else game_name
                                cursor.execute('''
                                    INSERT OR IGNORE INTO games (title, platform_id) 
                                    VALUES (?, ?)
                                ''', (title, platform_id))
                                count += 1
                                if count % 1000 == 0:
                                    print(f"Parsed {count} No-Intro entries...")
                            in_game_block = False
                        elif in_game_block:
                            if line.startswith('name "'):
                                game_name = line[6:-1]
                            elif line.startswith('description "'):
                                description = line[13:-1]

                conn.commit()
                print(f"Successfully processed {count} games for {platform_name}.")
                return True
        except Exception as e:
            print(f"Error parsing No-Intro DAT: {e}")
            return False

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Rebuild Romarr DB from local sources")
    parser.add_argument("--mame", type=str, help="Path to MAME XML file")
    parser.add_argument("--nointro", nargs=2, metavar=('DAT_PATH', 'PLATFORM'), help="Path to No-Intro DAT and Platform Name")
    args = parser.parse_args()

    builder = DatabaseBuilder()
    if args.mame:
        builder.parse_mame_xml(args.mame)
    if args.nointro:
        builder.parse_nointro_dat(args.nointro[0], args.nointro[1])
