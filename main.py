#!/usr/bin/env python3
import argparse
import configparser
import json
import os
import subprocess
from urllib.request import urlopen, Request
import websocket

try:
    import setproctitle
    setproctitle.setproctitle("gotify-dunst")
except ImportError:
    pass

# -----------------------
# Command-line arguments
# -----------------------
parser = argparse.ArgumentParser(description="Gotify Dunst client")
parser.add_argument(
    "--local",
    action="store_true",
    help="Use a .dbus_session file in the current directory instead of ~/.config/gotify-dunst/"
)
args = parser.parse_args()

# -----------------------
# Paths and config
# -----------------------
home = os.path.expanduser("~")
configdir = os.path.join(home, ".config", "gotify-dunst")
configpath = os.path.join(configdir, "gotify-dunst.conf")
cachedir = os.path.join(home, ".cache", "gotify-dunst")
os.makedirs(cachedir, exist_ok=True)

if args.local:
    SESSION_FILE = os.path.join(os.getcwd(), ".dbus_session")
else:
    SESSION_FILE = os.path.join(configdir, ".dbus_session")

# Create default config if missing
if not os.path.isfile(configpath):
    from shutil import copyfile
    from os import makedirs
    makedirs(configdir, exist_ok=True)
    copyfile("gotify-dunst.conf", configpath)

config = configparser.ConfigParser()
config.read(configpath)

domain = config.get("server", "domain", fallback=None)
if domain in ["push.example.com", None]:
    print("Configuration error. Edit gotify-dunst.conf properly")
    exit(1)

token = config.get("server", "token")
ssl = config.get("server", "ssl", fallback="false").lower() == "true"

# -----------------------
# DBus session
# -----------------------
def ensure_dbus_session():
    """Reuse or start a dbus session."""
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE) as f:
            lines = dict(line.strip().split("=", 1) for line in f if "=" in line)
        addr, pid = lines.get("DBUS_SESSION_BUS_ADDRESS"), lines.get("DBUS_SESSION_BUS_PID")
        if addr and pid and os.path.exists(f"/proc/{pid}"):
            os.environ["DBUS_SESSION_BUS_ADDRESS"] = addr
            return

    proc = subprocess.run(
        ["dbus-launch", "--sh-syntax", "--exit-with-session"],
        stdout=subprocess.PIPE, text=True
    )
    addr, pid = None, None
    for line in proc.stdout.splitlines():
        if line.startswith("DBUS_SESSION_BUS_ADDRESS"):
            addr = line.split("=", 1)[1].strip("';")
        elif line.startswith("DBUS_SESSION_BUS_PID"):
            pid = line.split("=", 1)[1].strip("';")
    if not addr or not pid:
        raise RuntimeError("Failed to start DBus session")

    os.environ["DBUS_SESSION_BUS_ADDRESS"] = addr
    with open(SESSION_FILE, "w") as f:
        f.write(f"DBUS_SESSION_BUS_ADDRESS={addr}\nDBUS_SESSION_BUS_PID={pid}\n")

# -----------------------
# Gotify helpers
# -----------------------
def get_picture(appid):
    imgpath = os.path.join(cachedir, f"{appid}.jpg")
    if os.path.isfile(imgpath):
        return imgpath
    proto = "https" if ssl else "http"
    req = Request(f"{proto}://{domain}/application?token={token}", headers={"User-Agent": "Mozilla/5.0"})
    apps = json.loads(urlopen(req).read())
    for app in apps:
        if app["id"] == appid:
            with open(imgpath, "wb") as f:
                imgreq = Request(f"{proto}://{domain}/{app['image']}?token={token}", headers={"User-Agent": "Mozilla/5.0"})
                f.write(urlopen(imgreq).read())
    return imgpath

LOG_PATH = "/home/lolo/mydev/perso/gotify-dunst/shell/dunstify.log"

def log(msg: str):
    with open(LOG_PATH, "a") as f:
        f.write(msg + "\n")

def send_notification(message):
    m = json.loads(message)
    urgency = "low" if m["priority"] <= 3 else "normal" if m["priority"] <= 7 else "critical"
    cmd = [
        "dunstify",
        m["title"],
        m["message"],
        "-u", urgency,
        "-i", get_picture(m["appid"]),
        "-a", "Gotify",
        "-h", "string:desktop-entry:gotify-dunst",
    ]

    category = m.get("extras", {}).get("category")
    actions = m.get("extras", {}).get("actions", {})

    if category:
        cmd.extend(["-h", f"string:category:{category}"])

    for key, label in actions.items():
        cmd.extend(["-A", f"{key},{label}"])

    # Run dunstify and capture stdout/stderr
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=os.environ.copy()
    )
    stdout, stderr = proc.communicate()
    action_key = stdout.strip()

    log(f"[gotify-dunst] Notification sent: {m['title']} - {m['message']}")
    log(f"[gotify-dunst] dunstify stdout: {stdout.strip()}")
    log(f"[gotify-dunst] dunstify stderr: {stderr.strip()}")

    if action_key:
        log(f"[gotify-dunst] User clicked action: {action_key}")
        handle_action(action_key)

def handle_action(action_key):
    if action_key == "install":
        cmd = ["/home/lolo/Music/alarms/alarm_flower.sh"]
    elif action_key == "ignore":
        cmd = ["/home/lolo/Music/alarms/alarm.sh"]
    else:
        log(f"[gotify-dunst] No handler for action: {action_key}")
        return

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=os.environ.copy()
        )
        out, err = proc.communicate()
        log(f"[gotify-dunst] Script {cmd[0]} stdout: {out.strip()}")
        log(f"[gotify-dunst] Script {cmd[0]} stderr: {err.strip()}")
    except Exception as e:
        log(f"[gotify-dunst] Failed to run {cmd[0]}: {e}")

# -----------------------
# Main
# -----------------------
if __name__ == "__main__":
    ensure_dbus_session()
    print(f"DBUS_SESSION_BUS_ADDRESS={os.environ['DBUS_SESSION_BUS_ADDRESS']}")

    # WebSocket client runs in background thread
    proto = "wss" if ssl else "ws"
    ws = websocket.WebSocketApp(
        f"{proto}://{domain}/stream?token={token}",
        on_message=lambda ws, msg: send_notification(msg),
    )
    ws.run_forever()



