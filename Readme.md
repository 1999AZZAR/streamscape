# StreamScape

**StreamScape** is a Terminal User Interface (TUI) application for managing and streaming web radio stations. With an intuitive interface and customizable playlists, StreamScape brings the world of online radio to your terminal.

## Features

- **Playlist Management**: Create, edit, and switch between multiple playlists.
- **Last Station Resume**: Automatically save the last played station and resume it after restarting the app.
- **Stream Monitoring**: Tracks playback status to ensure smooth streaming.
- **Search and Filter**: Easily find your favorite stations with search functionality.
- **Minimal Dependencies**: Works with `ffplay` and `curl` for streamlined performance.

## Installation

1. Ensure you have the required dependencies installed:
    - `ffmpeg`
    - `curl`
    - Python 3.x (with `requests` module installed)

2. Clone the repository:
    ```bash
    git clone https://github.com/1999AZZAR/streamscape.git
    cd streamscape
    ```

3. Run the application:
    ```bash
    python radio.py
    ```

## Usage

### Commands

- **Play a station**: `play [index]` (e.g., `play 1`)
- **Stop playback**: `stop`
- **Resume last station**: Automatically prompted on startup.
- **Search stations**: `/ [search term]`
- **Switch playlists**: `s`
- **Add a station**: `a`
- **Delete a station**: `d`
- **Exit application**: `exit`

### Key Features

#### Resume Last Played Station
StreamScape saves your last played station in the configuration file and prompts you to resume playback on the next startup.

#### Station Management
Easily manage your stations using the intuitive menu. Add new stations, delete old ones, or switch playlists effortlessly.

## Configuration

StreamScape stores user preferences in `radio_config.json`. The file includes:

- `current_playlist`: Tracks the currently active playlist.
- `last_played_station`: Saves the last played station details.

## Contributing

We welcome contributions! Feel free to fork the repository, create a branch, and submit a pull request. Please ensure your code adheres to the project's guidelines.

## License

StreamScape is licensed under the MIT License. See the `LICENSE` file for more details.

## Support

For issues or feature requests, please open an issue on the GitHub repository or reach out to the maintainers.

---

Enjoy your personalized radio streaming experience with **StreamScape**!

