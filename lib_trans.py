import curses


def txt_to_m3u(txt_file, m3u_file):
    try:
        with open(txt_file, 'r') as infile, open(m3u_file, 'w') as outfile:
            outfile.write("#EXTM3U\n\n")
            for line in infile:
                if "name:" in line and "link:" in line:
                    parts = line.strip().split("link:")
                    name = parts[0].replace("name:", "").strip()
                    link = parts[1].strip()
                    outfile.write(f"#EXTINF:-1,{name}\n")
                    outfile.write(f"{link}\n\n")
        return f"Successfully converted {txt_file} to {m3u_file}"
    except Exception as e:
        return f"Error: {e}"


def m3u_to_txt(m3u_file, txt_file):
    try:
        with open(m3u_file, 'r') as infile, open(txt_file, 'w') as outfile:
            name = None
            for line in infile:
                line = line.strip()
                if line.startswith("#EXTINF:"):
                    name = line.split(",", 1)[1].strip()
                elif line.startswith("http"):
                    link = line.strip()
                    outfile.write(f"name: {name} link: {link}\n")
        return f"Successfully converted {m3u_file} to {txt_file}"
    except Exception as e:
        return f"Error: {e}"


def tui(stdscr):
    curses.curs_set(1)
    stdscr.clear()
    stdscr.refresh()

    def get_input(prompt):
        stdscr.addstr(prompt)
        stdscr.refresh()
        curses.echo()
        user_input = stdscr.getstr().decode("utf-8").strip()
        curses.noecho()
        return user_input

    def menu():
        stdscr.addstr(0, 0, "Radio Converter TUI", curses.A_BOLD)
        stdscr.addstr(2, 0, "Choose an option:")
        stdscr.addstr(3, 2, "1. Convert TXT to M3U")
        stdscr.addstr(4, 2, "2. Convert M3U to TXT")
        stdscr.addstr(6, 0, "Enter your choice: ")

        while True:
            stdscr.refresh()
            choice = stdscr.getch()
            if choice == ord('1'):
                return "txt_to_m3u"
            elif choice == ord('2'):
                return "m3u_to_txt"
            else:
                stdscr.addstr(8, 0, "Invalid choice. Try again.")
                stdscr.clrtoeol()

    choice = menu()
    stdscr.clear()

    if choice == "txt_to_m3u":
        stdscr.addstr(0, 0, "Convert TXT to M3U", curses.A_BOLD)
        txt_file = get_input("Enter the path to the TXT file: ")
        m3u_file = get_input("Enter the output path for the M3U file: ")
        stdscr.clear()
        result = txt_to_m3u(txt_file, m3u_file)
    elif choice == "m3u_to_txt":
        stdscr.addstr(0, 0, "Convert M3U to TXT", curses.A_BOLD)
        m3u_file = get_input("Enter the path to the M3U file: ")
        txt_file = get_input("Enter the output path for the TXT file: ")
        stdscr.clear()
        result = m3u_to_txt(m3u_file, txt_file)

    stdscr.addstr(0, 0, "Result", curses.A_BOLD)
    stdscr.addstr(2, 0, result)
    stdscr.addstr(4, 0, "Press any key to exit...")
    stdscr.getch()


if __name__ == "__main__":
    curses.wrapper(tui)
