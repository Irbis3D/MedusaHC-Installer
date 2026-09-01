#!/usr/bin/env python3
"""Small TUI launcher for the independent MedusaHC project installers."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path


ESC = "\033["
RESET = f"{ESC}0m"
BOLD = f"{ESC}1m"
DIM = f"{ESC}2m"
RED = f"{ESC}91m"
GREEN = f"{ESC}92m"
YELLOW = f"{ESC}93m"
BLUE = f"{ESC}94m"
MAGENTA = f"{ESC}95m"
CYAN = f"{ESC}96m"
WHITE = f"{ESC}97m"

HOME = Path.home()
CONFIG = HOME / "printer_data" / "config"
KLIPPER_EXTRAS = HOME / "klipper" / "klippy" / "extras"
ROOT = Path(__file__).resolve().parent

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


@dataclass(frozen=True)
class Component:
    key: str
    name: str
    description: str
    repository: str
    status_paths: tuple[Path, ...]
    dependency: str | None = None

    @property
    def installer_url(self) -> str:
        return f"https://raw.githubusercontent.com/Irbis3D/{self.repository}/main/install-online.sh"


COMPONENTS = (
    Component(
        "core",
        "MedusaHC Core",
        "Python tool-change controller and example configuration",
        "MedusaHC",
        (KLIPPER_EXTRAS / "medusahc.py", CONFIG / "MedusaHC" / "MHC_config.cfg"),
    ),
    Component(
        "calibrate",
        "MedusaHC Calibration",
        "Independent automatic tool-offset calibration module",
        "MedusaHC-Calibrate",
        (KLIPPER_EXTRAS / "medusahc_calibrate.py",),
        "core",
    ),
    Component(
        "control",
        "MedusaHC Control Panel",
        "Standalone browser-based control and statistics panel",
        "MedusaHC-Control",
        (HOME / "medusahc-control",),
        "core",
    ),
    Component(
        "mainsail",
        "MedusaHC Mainsail",
        "Mainsail integration for the MedusaHC Control Panel",
        "MedusaHC-Mainsail",
        (Path("/var/lib/medusahc-installer/manifest.json"),),
        "control",
    ),
)


def color_enabled() -> bool:
    return sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def c(value: str, color: str) -> str:
    return f"{color}{value}{RESET}" if color_enabled() else value


def clear() -> None:
    if sys.stdout.isatty():
        print("\033[2J\033[H", end="")


def width() -> int:
    return max(72, min(96, shutil.get_terminal_size((82, 24)).columns))


def rule(left: str, fill: str, right: str) -> str:
    return left + fill * (width() - 2) + right


def centered(text: str) -> str:
    return "│" + text.center(width() - 2) + "│"


def header(section: str = "") -> None:
    clear()
    print(c(rule("╭", "─", "╮"), CYAN))
    print(c(centered("MEDUSAHC INSTALLER"), BOLD + CYAN))
    print(c(centered("Install and maintain MedusaHC components"), DIM + WHITE))
    if section:
        print(c(rule("├", "─", "┤"), CYAN))
        print(c(centered(section), BOLD + WHITE))
    print(c(rule("╰", "─", "╯"), CYAN))
    print()


def installed(component: Component) -> bool:
    if component.key == "mainsail":
        return any(
            (directory / "mainsail-medusahc.js").is_file()
            for directory in (HOME / "mainsail", HOME / "mainsail-medusahc")
        )
    return all(path.exists() for path in component.status_paths)


def component(key: str) -> Component:
    return next(item for item in COMPONENTS if item.key == key)


def state_label(item: Component) -> str:
    if installed(item):
        return c("● INSTALLED", GREEN)
    if item.dependency and not installed(component(item.dependency)):
        return c("● NEEDS DEPENDENCY", YELLOW)
    return c("○ NOT INSTALLED", DIM + WHITE)


def status_table() -> None:
    name_w = (width() - 3) // 2
    state_w = width() - name_w - 3
    print(c("┌" + "─" * name_w + "┬" + "─" * state_w + "┐", BLUE))
    print(c("│" + " Component".ljust(name_w) + "│" + " Status".ljust(state_w) + "│", BOLD + BLUE))
    print(c("├" + "─" * name_w + "┼" + "─" * state_w + "┤", BLUE))
    for item in COMPONENTS:
        raw_state = "INSTALLED" if installed(item) else ("NEEDS DEPENDENCY" if item.dependency and not installed(component(item.dependency)) else "NOT INSTALLED")
        state_color = GREEN if raw_state == "INSTALLED" else (YELLOW if raw_state == "NEEDS DEPENDENCY" else DIM + WHITE)
        print(
            c("│", BLUE)
            + " " + item.name[: name_w - 2].ljust(name_w - 1)
            + c("│", BLUE)
            + " " + c(raw_state.ljust(state_w - 1), state_color)
            + c("│", BLUE)
        )
    print(c("└" + "─" * name_w + "┴" + "─" * state_w + "┘", BLUE))


def menu_line(key: str, title: str, detail: str = "") -> None:
    suffix = f"  {c(detail, DIM + WHITE)}" if detail else ""
    print(f"  {c(f'[{key}]', CYAN + BOLD)} {title}{suffix}")


def pause() -> None:
    input(c("\nPress Enter to continue...", DIM + WHITE))


def confirm(prompt: str) -> bool:
    answer = input(c(f"\n{prompt} [y/N]: ", YELLOW)).strip().lower()
    return answer in {"y", "yes"}


def dependency_ready(item: Component) -> bool:
    if not item.dependency:
        return True
    required = component(item.dependency)
    if installed(required):
        return True
    print(c(f"\n{item.name} requires {required.name}. Install it first.", RED))
    pause()
    return False


def run_installer(item: Component, action: str, extra: tuple[str, ...] = ()) -> None:
    if action in {"install", "update"} and not dependency_ready(item):
        return
    header(f"{action.title()} — {item.name}")
    print(item.description)
    print(f"\nSource: {c(item.repository, CYAN)}")
    print(f"Action: {c(action, BOLD + WHITE)}")
    if not confirm("Continue with the official component installer?"):
        print(c("\nCancelled. Nothing was changed.", YELLOW))
        pause()
        return

    temporary = None
    try:
        with tempfile.NamedTemporaryFile(prefix="medusahc-installer-", suffix=".sh", delete=False) as handle:
            temporary = Path(handle.name)
            with urllib.request.urlopen(item.installer_url, timeout=30) as response:
                handle.write(response.read())
        result = subprocess.run(["bash", str(temporary), action, *extra], check=False)
        if result.returncode == 0:
            print(c("\nOperation completed successfully.", GREEN))
        else:
            print(c(f"\nInstaller exited with code {result.returncode}.", RED))
    except (OSError, urllib.error.URLError) as exc:
        print(c(f"\nUnable to run installer: {exc}", RED))
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)
    pause()


def choose_component(title: str, action: str, *, installed_only: bool = False) -> None:
    while True:
        header(title)
        shown = [item for item in COMPONENTS if not installed_only or installed(item)]
        if not shown:
            print(c("No installed components were detected.", YELLOW))
            pause()
            return
        for index, item in enumerate(shown, 1):
            menu_line(str(index), item.name, "installed" if installed(item) else "not installed")
        menu_line("B", "Back")
        choice = input(c("\nSelect: ", BOLD + WHITE)).strip().lower()
        if choice in {"b", "q"}:
            return
        if not choice.isdigit() or not 1 <= int(choice) <= len(shown):
            continue
        item = shown[int(choice) - 1]
        if item.key == "mainsail" and action == "install":
            mainsail_install_menu(item)
        else:
            run_installer(item, action)


def mainsail_install_menu(item: Component) -> None:
    while True:
        header("Install — MedusaHC Mainsail")
        menu_line("1", "Replace the current Mainsail", "backup and restore supported")
        menu_line("2", "Install alongside current Mainsail", "separate address and port")
        menu_line("B", "Back")
        choice = input(c("\nSelect: ", BOLD + WHITE)).strip().lower()
        if choice == "1":
            run_installer(item, "install", ("--mode", "replace"))
            return
        if choice == "2":
            run_installer(item, "install", ("--mode", "parallel"))
            return
        if choice in {"b", "q"}:
            return


def show_status() -> None:
    header("Installation status")
    status_table()
    print(c("\nStatus is detected locally. No installer was executed.", DIM + WHITE))
    pause()


def self_update() -> None:
    header("Update MedusaHC Installer")
    if not (ROOT / ".git").is_dir():
        print(c("This copy was not installed from Git and cannot update itself.", YELLOW))
        pause()
        return
    result = subprocess.run(["git", "-C", str(ROOT), "pull", "--ff-only"], check=False)
    if result.returncode == 0:
        print(c("\nInstaller is up to date.", GREEN))
    else:
        print(c("\nSelf-update failed. No component was changed.", RED))
    pause()


def main() -> int:
    if getattr(os, "geteuid", lambda: 1)() == 0:
        print("Do not run MedusaHC Installer as root. Run it as your printer user; sudo will be requested only when needed.", file=sys.stderr)
        return 2
    while True:
        header("Main menu")
        status_table()
        print()
        menu_line("1", "Install components")
        menu_line("2", "Update components")
        menu_line("3", "Remove components")
        menu_line("4", "Show installation status")
        menu_line("5", "Update this installer")
        menu_line("Q", "Exit")
        choice = input(c("\nSelect: ", BOLD + WHITE)).strip().lower()
        if choice == "1":
            choose_component("Install components", "install")
        elif choice == "2":
            choose_component("Update components", "update", installed_only=True)
        elif choice == "3":
            choose_component("Remove components", "uninstall", installed_only=True)
        elif choice == "4":
            show_status()
        elif choice == "5":
            self_update()
        elif choice in {"q", "x"}:
            clear()
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
