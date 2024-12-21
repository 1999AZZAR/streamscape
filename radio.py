import os
import subprocess
import json
import requests
from colorama import Fore, Style, init
from math import ceil
import shutil
import glob
from typing import List, Tuple, Dict, Optional
import threading
import queue
import time
import sys
from datetime import datetime

init(autoreset=True)

# Enhanced Constants
DEFAULT_STATION_FILE = "list.txt"
STATIONS_PER_PAGE = 15  # Increased for better visibility
CONFIG_FILE = "radio_config.json"
HISTORY_FILE = "play_history.json"
FAVORITES_FILE = "favorites.txt"
MAX_HISTORY_ENTRIES = 50

# Basic dependencies - just ffmpeg and curl
REQUIRED_PACKAGES = {
    'debian': {
        'ffmpeg': 'ffmpeg',
        'curl': 'curl'
    },
    'fedora': {
        'ffmpeg': 'ffmpeg',
        'curl': 'curl'
    },
    'brew': {
        'ffmpeg': 'ffmpeg',
        'curl': 'curl'
    }
}

def detect_package_manager():
    """Detect the system's package manager."""
    if shutil.which('apt-get'):
        return 'debian'
    elif shutil.which('dnf'):
        return 'fedora'
    elif shutil.which('brew'):
        return 'brew'
    return None

def check_dependencies():
    """Check if required dependencies are installed."""
    required_cmds = {
        'ffmpeg': False,
        'curl': False
    }

    for cmd in required_cmds:
        if shutil.which(cmd):
            required_cmds[cmd] = True

    missing = [cmd for cmd, installed in required_cmds.items() if not installed]

    if missing:
        print(f"{Fore.RED}Missing required dependencies: {', '.join(missing)}")
        print(f"{Fore.YELLOW}Please install the missing dependencies:")

        pkg_manager = detect_package_manager()
        if pkg_manager:
            packages = set(REQUIRED_PACKAGES[pkg_manager][cmd] for cmd in missing)
            if pkg_manager == 'debian':
                print(f"{Fore.WHITE}Ubuntu/Debian: sudo apt-get install {' '.join(packages)}")
            elif pkg_manager == 'fedora':
                print(f"{Fore.WHITE}Fedora: sudo dnf install {' '.join(packages)}")
            else:  # brew
                print(f"{Fore.WHITE}macOS: brew install {' '.join(packages)}")
        else:
            print(f"{Fore.RED}Could not detect package manager. Please install the missing dependencies manually.")

        print(f"\n{Fore.YELLOW}Also make sure you have python requests installed:")
        print(f"{Fore.WHITE}pip install requests")
        return False
    return True

def get_content_type(url):
    """Detect the content type of the stream."""
    try:
        response = requests.head(url, timeout=5, allow_redirects=True)
        content_type = response.headers.get('Content-Type', '').lower()
        return content_type.split(';')[0]  # Remove charset info if present
    except Exception as e:
        print(f"{Fore.YELLOW}Warning: Could not detect content type: {str(e)}")
        return None

def resolve_playlist(url):
    """Resolve playlist URLs to get the actual stream URL."""
    try:
        response = requests.get(url, timeout=5)
        content = response.text.lower()

        # Handle M3U/M3U8 playlists
        if 'http' in content:
            for line in content.splitlines():
                if line.startswith('http'):
                    return line.strip()

        # Handle PLS playlists
        if '[playlist]' in content:
            for line in content.splitlines():
                if line.startswith('file1='):
                    return line.replace('file1=', '').strip()

        return url  # Return original URL if no stream URL found
    except Exception as e:
        print(f"{Fore.YELLOW}Warning: Could not resolve playlist: {str(e)}")
        return url

def play_station(url, player_process):
    """Play a radio station using ffplay."""
    stop_station(player_process)

    try:
        # Check if it's a playlist first
        content_type = get_content_type(url)
        if content_type and 'playlist' in content_type:
            url = resolve_playlist(url)

        # Use ffplay with optimized settings for streaming
        player_process["process"] = subprocess.Popen([
            "ffplay",
            "-nodisp",              # No video display
            "-hide_banner",         # Hide ffplay banner
            "-loglevel", "panic",   # Minimal logging
            "-vn",                  # Skip video
            "-infbuf",             # Infinite buffer (good for streams)
            "-autoexit",           # Exit when stream ends
            url
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        print(f"{Fore.GREEN}Playing stream... Press any key to access menu.")

    except Exception as e:
        print(f"{Fore.RED}Error playing stream: {str(e)}")
        input("Press Enter to continue.")

def stop_station(player_process):
    """Stop the currently playing station."""
    if player_process.get("process"):
        player_process["process"].terminate()
        player_process["process"] = None

def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def filter_stations(stations: List[Tuple[str, str]], search_term: str) -> List[Tuple[str, str]]:
    """Filter stations based on search term."""
    if not search_term:
        return stations
    return [(name, link) for name, link in stations if search_term.lower() in name.lower()]

def display_help():
    """Display help information."""
    clear_screen()
    print(f"{Fore.CYAN}Radio Player Help")
    print(f"{Fore.CYAN}{'=' * 40}")
    print(f"{Fore.YELLOW}Navigation:")
    print(f"{Fore.WHITE}  </> - Navigate between pages")
    print(f"{Fore.WHITE}  n/p - Next/Previous station")
    print(f"{Fore.WHITE}  j   - Jump to specific station")
    print(f"{Fore.WHITE}  /   - Search stations")
    print(f"{Fore.WHITE}  c   - Clear search")

    print(f"\n{Fore.YELLOW}Playlist Management:")
    print(f"{Fore.WHITE}  s   - Switch between playlists")
    print(f"{Fore.WHITE}  a   - Add new station")
    print(f"{Fore.WHITE}  d   - Delete station")

    print(f"\n{Fore.YELLOW}Other Commands:")
    print(f"{Fore.WHITE}  h   - Show this help")
    print(f"{Fore.WHITE}  e   - Exit program")

    input(f"\n{Fore.GREEN}Press Enter to return to menu...")

class RadioPlayer:
    def __init__(self):
        self.current_playlist = DEFAULT_STATION_FILE
        self.playlists: Dict[str, List[Tuple[str, str]]] = {}
        self.favorites: List[Tuple[str, str]] = []
        self.current_station = 0
        self.is_playing = False
        self.last_played_station = None
        self.player_process = None
        self.current_page = 1
        self.search_term = ""
        self.status_queue = queue.Queue()
        self.current_station_name = None
        self.play_history = []
        self.volume = 100
        self.is_muted = False
        self.view_mode = "all"  # Can be "all", "favorites", "history"

        # Initialize everything
        self.load_config()
        self.load_all_playlists()
        self.load_favorites()
        self.load_history()

    def load_config(self):
        """Load configuration from file."""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    self.current_playlist = config.get('current_playlist', self.current_playlist)
                    self.last_played_station = config.get('last_played_station', None)
        except Exception as e:
            print(f"Warning: Could not load config: {str(e)}")

    def save_config(self):
        """Save configuration to file."""
        try:
            config = {
                'current_playlist': self.current_playlist,
                'last_played_station': self.last_played_station
            }
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f)
        except Exception as e:
            print(f"Warning: Could not save config: {str(e)}")

    def load_all_playlists(self):
        """Load all .txt files as potential playlists."""
        self.playlists.clear()
        for playlist_file in glob.glob("*.txt"):
            stations = self.load_stations(playlist_file)
            if stations:
                self.playlists[playlist_file] = stations

    def load_stations(self, filename: str) -> List[Tuple[str, str]]:
        """Load stations from a specific file."""
        if not os.path.exists(filename):
            return []
        try:
            with open(filename, 'r') as file:
                lines = file.read().strip().split("\n")
                stations = []
                for line in lines:
                    parts = line.split("link:")
                    if len(parts) == 2:
                        name = parts[0].replace("name:", "").strip()
                        link = parts[1].strip()
                        stations.append((name, link))
                return stations
        except Exception as e:
            print(f"{Fore.YELLOW}Warning: Could not load stations from {filename}: {str(e)}")
            return []

    def save_stations(self, stations: List[Tuple[str, str]], filename: str):
        """Save stations to a specific file."""
        try:
            with open(filename, 'w') as file:
                for name, link in stations:
                    file.write(f"name: {name} link: {link}\n")
        except Exception as e:
            print(f"{Fore.RED}Error saving stations to {filename}: {str(e)}")

    def get_current_stations(self) -> List[Tuple[str, str]]:
        """Get stations from current playlist."""
        return self.playlists.get(self.current_playlist, [])

    def get_stream_url(self, url: str) -> str:
        """Resolve the actual stream URL from potentially a playlist URL."""
        try:
            content_type = self.get_content_type(url)
            if content_type and ('playlist' in content_type or '.m3u' in url.lower() or '.pls' in url.lower()):
                return self.resolve_playlist(url)
            return url
        except Exception as e:
            print(f"{Fore.YELLOW}Warning: Could not resolve stream URL: {str(e)}")
            return url

    def get_content_type(self, url: str) -> Optional[str]:
        """Get content type of the URL."""
        try:
            response = requests.head(url, timeout=5, allow_redirects=True)
            content_type = response.headers.get('Content-Type', '').lower()
            return content_type.split(';')[0]
        except Exception:
            return None

    def resolve_playlist(self, url: str) -> str:
        """Resolve playlist URL to get the actual stream URL."""
        try:
            response = requests.get(url, timeout=5)
            content = response.text.lower()

            # Handle M3U/M3U8 playlists
            if 'http' in content:
                for line in content.splitlines():
                    if line.startswith('http'):
                        return line.strip()

            # Handle PLS playlists
            if '[playlist]' in content:
                for line in content.splitlines():
                    if line.startswith('file1='):
                        return line.replace('file1=', '').strip()

            return url
        except Exception:
            return url

    def check_playback_status(self) -> bool:
        """Check if the station is actually playing."""
        if self.player_process is None:
            return False

        # Check if process is still running
        return self.player_process.poll() is None

    def monitor_playback(self):
        """Monitor playback status in a separate thread with improved status tracking."""
        while True:
            current_status = self.check_playback_status()

            if self.is_playing and not current_status:
                # Playback stopped unexpectedly
                self.is_playing = False
                self.current_station_name = None
                self.status_queue.put("stopped")

            time.sleep(1)

    def resume_last_station(self):
        """Resume playback of the last played station."""
        if self.last_played_station:
            self.current_playlist = self.last_played_station['playlist']
            station_idx = self.last_played_station['station_idx']
            self.play_station(station_idx)
        else:
            print(f"{Fore.YELLOW}No previous station found.")
            input("Press Enter to continue...")

    def switch_playlist(self):
        """Switch between available playlists."""
        clear_screen()
        print(f"{Fore.CYAN}Available Playlists:")
        playlists = list(self.playlists.keys())

        for i, playlist in enumerate(playlists, 1):
            current = " (current)" if playlist == self.current_playlist else ""
            print(f"{Fore.YELLOW}{i}. {Fore.WHITE}{playlist}{Fore.GREEN}{current}")

        print(f"\n{Fore.YELLOW}[n] Create new playlist")
        print(f"{Fore.YELLOW}[c] Cancel")

        choice = input("\nEnter your choice: ").strip().lower()

        if choice == 'n':
            filename = input("Enter new playlist filename (*.txt): ").strip()
            if not filename.endswith('.txt'):
                filename += '.txt'
            if not os.path.exists(filename):
                self.playlists[filename] = []
                self.current_playlist = filename
                self.save_config()
        elif choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(playlists):
                self.current_playlist = playlists[idx]
                self.save_config()

    def load_favorites(self):
        """Load favorite stations from file."""
        try:
            if os.path.exists(FAVORITES_FILE):
                self.favorites = self.load_stations(FAVORITES_FILE)
        except Exception as e:
            print(f"{Fore.YELLOW}Warning: Could not load favorites: {str(e)}")

    def save_favorites(self):
        """Save favorite stations to file."""
        try:
            self.save_stations(self.favorites, FAVORITES_FILE)
        except Exception as e:
            print(f"{Fore.YELLOW}Warning: Could not save favorites: {str(e)}")

    def toggle_favorite(self, station: Tuple[str, str]):
        """Add or remove station from favorites."""
        if station in self.favorites:
            self.favorites.remove(station)
            print(f"{Fore.YELLOW}Removed from favorites: {station[0]}")
        else:
            self.favorites.append(station)
            print(f"{Fore.GREEN}Added to favorites: {station[0]}")
        self.save_favorites()

    def load_history(self):
        """Load play history from file."""
        try:
            if os.path.exists(HISTORY_FILE):
                with open(HISTORY_FILE, 'r') as f:
                    self.play_history = json.load(f)
                    # Keep only the last MAX_HISTORY_ENTRIES
                    self.play_history = self.play_history[-MAX_HISTORY_ENTRIES:]
        except Exception as e:
            print(f"{Fore.YELLOW}Warning: Could not load history: {str(e)}")

    def save_history(self):
        """Save play history to file."""
        try:
            with open(HISTORY_FILE, 'w') as f:
                json.dump(self.play_history, f)
        except Exception as e:
            print(f"{Fore.YELLOW}Warning: Could not save history: {str(e)}")

    def add_to_history(self, station_name: str, station_url: str):
        """Add station to play history with timestamp."""
        entry = {
            'name': station_name,
            'url': station_url,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        self.play_history.append(entry)
        if len(self.play_history) > MAX_HISTORY_ENTRIES:
            self.play_history.pop(0)
        self.save_history()

    def adjust_volume(self, direction: str):
        """Adjust playback volume."""
        if direction == 'up' and self.volume < 100:
            self.volume = min(100, self.volume + 10)
        elif direction == 'down' and self.volume > 0:
            self.volume = max(0, self.volume - 10)

        if self.player_process:
            # Use ffmpeg filter to adjust volume
            self.restart_playback_with_volume()

    def toggle_mute(self):
        """Toggle mute state."""
        self.is_muted = not self.is_muted
        if self.player_process:
            self.restart_playback_with_volume()

    def restart_playback_with_volume(self):
        """Restart playback with current volume settings."""
        if self.current_station_name:
            stations = self.get_current_stations()
            station_info = next((s for s in stations if s[0] == self.current_station_name), None)
            if station_info:
                self.play_station(self.current_station, None, force_restart=True)

    def stop_station(self):
        """Stop the currently playing station."""
        if self.player_process:
            try:
                self.player_process.terminate()
                self.player_process = None
                self.is_playing = False
                self.current_station_name = None
            except Exception:
                pass

    def play_station(self, station_idx: int, filtered_stations: List[Tuple[str, str]] = None, force_restart: bool = False):
        """Enhanced play station with volume control and history."""
        if not force_restart and self.is_playing and self.current_station == station_idx:
            return True

        self.stop_station()

        try:
            stations = filtered_stations if filtered_stations is not None else self.get_current_stations()

            if not (0 <= station_idx < len(stations)):
                print(f"{Fore.RED}Invalid station index")
                return False

            name, url = stations[station_idx]

            print(f"{Fore.YELLOW}Loading station: {name}...")

            # Find the index in the original station list if using filtered results
            all_stations = self.get_current_stations()
            original_idx = next((i for i, (n, _) in enumerate(all_stations) if n == name), station_idx)

            stream_url = self.get_stream_url(url)

            # Calculate effective volume
            effective_volume = 0 if self.is_muted else self.volume

            # Build ffplay command with volume control
            cmd = [
                "ffplay",
                "-nodisp",
                "-hide_banner",
                "-loglevel", "panic",
                "-vn",
                "-af", f"volume={effective_volume/100}",
                "-infbuf",
                "-autoexit",
                stream_url
            ]

            self.player_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            self.is_playing = True
            self.current_station = original_idx
            self.current_station_name = name
            self.last_played_station = {
                'playlist': self.current_playlist,
                'station_idx': original_idx
            }

            # Add to history
            self.add_to_history(name, url)

            self.save_config()

            # Show status with volume
            volume_status = "🔇" if self.is_muted else f"🔊 {self.volume}%"
            favorite_status = "⭐" if (name, url) in self.favorites else ""
            print(f"{Fore.GREEN}Now playing: {name} {volume_status} {favorite_status}")
            print(f"{Fore.CYAN}Press any key to access menu")
            return True

        except Exception as e:
            print(f"{Fore.RED}Error playing station: {str(e)}")
            self.is_playing = False
            self.current_station_name = None
            return False

    def display_menu(self) -> List[Tuple[str, str]]:
        """Enhanced menu display with favorites and history."""
        clear_screen()

        # Get appropriate station list based on view mode
        if self.view_mode == "favorites":
            stations = self.favorites
        elif self.view_mode == "history":
            # Convert history entries to station format
            stations = [(entry['name'], entry['url']) for entry in reversed(self.play_history)]
        else:
            stations = self.get_current_stations()

        filtered_stations = filter_stations(stations, self.search_term)
        total_pages = ceil(len(filtered_stations) / STATIONS_PER_PAGE)
        start_idx = (self.current_page - 1) * STATIONS_PER_PAGE
        end_idx = start_idx + STATIONS_PER_PAGE

        # Header with mode indicator
        mode_text = {
            "all": "All Stations",
            "favorites": "Favorites",
            "history": "Recently Played"
        }[self.view_mode]

        print(f"{Fore.CYAN}{mode_text} {Fore.YELLOW}[Page {self.current_page}/{max(1, total_pages)}]")
        print(f"{Fore.CYAN}{'=' * 50}")

        # Playlist info
        if self.view_mode == "all":
            print(f"{Fore.GREEN}Current Playlist: {self.current_playlist}")

        # Playing status with volume
        if self.is_playing and self.current_station_name:
            volume_status = "🔇" if self.is_muted else f"🔊 {self.volume}%"
            favorite_status = "⭐" if any(s[0] == self.current_station_name for s in self.favorites) else ""
            print(f"{Fore.GREEN}Now Playing: {Fore.WHITE}{self.current_station_name} {volume_status} {favorite_status}")
            print(f"{Fore.CYAN}{'=' * 50}")

        # Search status
        if self.search_term:
            print(f"{Fore.YELLOW}Search: '{self.search_term}' ({len(filtered_stations)} results)")

        # Station list
        print(f"\n{Fore.CYAN}Available Stations:")
        for i, (name, _) in enumerate(filtered_stations[start_idx:end_idx], start=start_idx + 1):
            station_idx = i - 1
            is_playing = (station_idx == self.current_station and self.is_playing and
                         self.current_station_name == name)
            is_favorite = any(f[0] == name for f in self.favorites)

            # Build station display
            status = f"{Fore.GREEN}◄-- PLAYING" if is_playing else ""
            favorite = "⭐ " if is_favorite else ""
            print(f"{Fore.YELLOW}{i:3d}. {favorite}{Fore.WHITE}{name[:40]} {status}")

        # Enhanced controls display
        print(f"\n{Fore.CYAN}Playback:")
        print(f"{Fore.GREEN}  [+/-] - Volume Up/Down  {Fore.GREEN}[m] - Mute/Unmute")
        print(f"{Fore.GREEN}  [k]   - Play/Pause      {Fore.GREEN}[f] - Toggle Favorite")

        print(f"\n{Fore.CYAN}Navigation:")
        print(f"{Fore.GREEN}  [/] - Search   {Fore.GREEN}[</>] - Prev/Next page")
        print(f"{Fore.GREEN}  [n] - Next     {Fore.GREEN}[p]   - Previous station")
        print(f"{Fore.GREEN}  [j] - Jump to  {Fore.GREEN}[c]   - Clear search")

        print(f"\n{Fore.CYAN}Views:")
        print(f"{Fore.GREEN}  [v] - Switch view (All/Favorites/History)")
        print(f"{Fore.GREEN}  [s] - Switch playlist")

        print(f"\n{Fore.CYAN}Other:")
        print(f"{Fore.GREEN}  [a] - Add station   {Fore.GREEN}[d] - Delete station")
        print(f"{Fore.GREEN}  [h] - Help          {Fore.RED}[e] - Exit")

        return filtered_stations

    def switch_view_mode(self):
        """Switch between different view modes."""
        modes = ["all", "favorites", "history"]
        current_index = modes.index(self.view_mode)
        self.view_mode = modes[(current_index + 1) % len(modes)]
        self.current_page = 1
        self.search_term = ""

    def run(self):
        """Main application loop with improved search handling."""
        if not check_dependencies():
            input("Press Enter to exit.")
            return

        # Start playback monitoring thread
        threading.Thread(target=self.monitor_playback, daemon=True).start()

        # Resume last played station if requested
        if self.last_played_station:
            choice = input(f"{Fore.CYAN}Resume last played station? (y/n): ").strip().lower()
            if choice == 'y':
                self.resume_last_station()

        while True:
            try:
                # Check for status updates
                while not self.status_queue.empty():
                    status = self.status_queue.get_nowait()
                    if status == "stopped":
                        self.is_playing = False

                filtered_stations = self.display_menu()
                total_pages = ceil(len(filtered_stations) / STATIONS_PER_PAGE)

                choice = input(f"\n{Fore.CYAN}Enter your choice: ").strip().lower()

                if choice == 'e':
                    print("Exiting the radio station selector. Goodbye!")
                    self.stop_station()
                    return

                if choice in ['n', 'p']:
                    if filtered_stations:
                        # Find current station in filtered list
                        current_name = next((name for name, _ in filtered_stations if name == self.current_station_name), None)
                        current_filtered_idx = next((i for i, (name, _) in enumerate(filtered_stations) if name == current_name), 0)

                        if choice == 'n':
                            next_idx = (current_filtered_idx + 1) % len(filtered_stations)
                        else:
                            next_idx = (current_filtered_idx - 1) % len(filtered_stations)

                        self.play_station(next_idx, filtered_stations)

                elif choice == 'k':
                    if self.is_playing:
                        self.stop_station()
                    else:
                        self.resume_last_station()
                elif choice in ['+', '-']:
                    self.adjust_volume('up' if choice == '+' else 'down')
                elif choice == 'm':
                    self.toggle_mute()
                elif choice == '>':
                    if self.current_page < total_pages:
                        self.current_page += 1
                elif choice == '<':
                    if self.current_page > 1:
                        self.current_page -= 1
                elif choice == 'f' and self.current_station_name:
                    current_station = next((s for s in self.get_current_stations()
                                         if s[0] == self.current_station_name), None)
                    if current_station:
                        self.toggle_favorite(current_station)
                elif choice == '/':
                    self.search_term = input("Enter search term: ").strip()
                    self.current_page = 1
                elif choice == 'c':
                    self.search_term = ""
                    self.current_page = 1
                elif choice == 'v':
                    self.switch_view_mode()
                elif choice == 's':
                    self.switch_playlist()
                elif choice == 'j':
                    try:
                        station_number = int(input(f"{Fore.CYAN}Enter station number: ")) - 1
                        if 0 <= station_number < len(filtered_stations):
                            self.play_station(station_number, filtered_stations)
                        else:
                            print(f"{Fore.RED}Invalid station number.")
                            input("Press Enter to continue...")
                    except ValueError:
                        print(f"{Fore.RED}Invalid input.")
                        input("Press Enter to continue...")
                elif choice.isdigit():
                    station_number = int(choice) - 1
                    if 0 <= station_number < len(filtered_stations):
                        self.play_station(station_number, filtered_stations)
                    else:
                        print(f"{Fore.RED}Invalid station number.")
                        input("Press Enter to continue...")
                elif choice == 'a':
                    name = input("Enter station name: ").strip()
                    link = input("Enter station URL: ").strip()
                    if name and link:
                        current_stations = self.get_current_stations()
                        current_stations.append((name, link))
                        self.playlists[self.current_playlist] = current_stations
                        self.save_stations(current_stations, self.current_playlist)
                elif choice == 'd':
                    try:
                        station_number = int(input("Enter station number to delete: ")) - 1
                        current_stations = self.get_current_stations()
                        if 0 <= station_number < len(current_stations):
                            del current_stations[station_number]
                            self.playlists[self.current_playlist] = current_stations
                            self.save_stations(current_stations, self.current_playlist)
                    except ValueError:
                        print(f"{Fore.RED}Invalid input.")
                        input("Press Enter to continue...")
                elif choice == 'h':
                    display_help()
                else:
                    print(f"{Fore.RED}Invalid option.")
                    input("Press Enter to continue...")

            except Exception as e:
                print(f"{Fore.RED}An error occurred: {str(e)}")
                input("Press Enter to continue...")

def main():
    if not check_dependencies():
        input("Press Enter to exit.")
        return
    player = RadioPlayer()
    player.run()

if __name__ == "__main__":
    main()
