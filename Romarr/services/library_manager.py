import os
import shutil

class LibraryManager:
    def __init__(self, library_base_path):
        self.base_path = library_base_path
        os.makedirs(self.base_path, exist_ok=True)

    def import_rom(self, source_filepath, platform_name, game_title):
        """Move and rename a ROM into the standardized library structure."""
        if not os.path.exists(source_filepath):
            return False, "Source file not found"

        # Standard layout: Library/{Platform}/{Game Name}/{Game Name}.ext
        platform_dir = os.path.join(self.base_path, self._sanitize(platform_name))
        game_dir = os.path.join(platform_dir, self._sanitize(game_title))
        
        os.makedirs(game_dir, exist_ok=True)

        _, ext = os.path.splitext(source_filepath)
        new_filename = f"{self._sanitize(game_title)}{ext}"
        destination_filepath = os.path.join(game_dir, new_filename)

        try:
            shutil.move(source_filepath, destination_filepath)
            # Alternatively use shutil.copy2 if we want to keep the original upload
            return True, destination_filepath
        except Exception as e:
            return False, f"Failed to move file: {e}"

    def delete_rom(self, platform_name, game_title):
        """Remove a ROM and its directory from the library."""
        platform_dir = os.path.join(self.base_path, self._sanitize(platform_name))
        game_dir = os.path.join(platform_dir, self._sanitize(game_title))

        if os.path.exists(game_dir):
            try:
                shutil.rmtree(game_dir)
                return True, "Deleted successfully"
            except Exception as e:
                return False, f"Failed to delete directory: {e}"
        return False, "Directory not found"

    def scan_library(self):
        """Scan the existing library folder for ROMs."""
        found_roms = []
        for root, dirs, files in os.walk(self.base_path):
            for file in files:
                # Basic check, in reality we'd check extensions against a known list
                if not file.startswith('.'): 
                    rel_dir = os.path.relpath(root, self.base_path)
                    parts = rel_dir.split(os.sep)
                    if len(parts) >= 2:
                        platform = parts[0]
                        game = parts[1]
                        found_roms.append({
                            'platform': platform,
                            'game_title': game,
                            'path': os.path.join(root, file)
                        })
        return found_roms

    def _sanitize(self, name):
        """Sanitize a string for use as a folder/file name."""
        keepcharacters = (' ', '.', '_', '-')
        s = "".join(c for c in name if c.isalnum() or c in keepcharacters).rstrip()
        return s
