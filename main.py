import os
import subprocess
import json
import configparser
import websocket
from urllib.request import urlopen, Request
import argparse

try:
    import setproctitle
    setproctitle.setproctitle("gotify-dunst")
except:
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
configpath = os.path.join(home, ".config", "gotify-dunst", "gotify-dunst.conf")
localdir = os.path.join(home, ".config", "gotify-dunst")

# Session file location
if args.local:
    SESSION_FILE = os.path.join(os.getcwd(), ".dbus_session")
else:
    SESSION_FILE = os.path.join(localdir, ".dbus_session")

if not os.path.isfile(configpath):
    from shutil import copyfile
    from os import makedirs
    makedirs(localdir, exist_ok=True)
    copyfile("gotify-dunst.conf", configpath)

config = configparser.ConfigParser()
config.read(configpath)

domain = config.get("server", "domain", fallback=None)

if domain in ["push.example.com", None]:
    print("Configuration error. Make sure you have properly modified the configuration")
    exit()

token = config.get("server", "token")
ssl = config.get("server", "ssl", fallback="false").lower() == "true"

path = os.path.join(home, ".cache", "gotify-dunst")
os.makedirs(path, exist_ok=True)


def ensure_dbus_session():
    """Reuse an existing session if possible, otherwise start a new one."""
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE) as f:
            lines = dict(line.strip().split("=", 1) for line in f if "=" in line)
        addr, pid = lines.get("DBUS_SESSION_BUS_ADDRESS"), lines.get("DBUS_SESSION_BUS_PID")
        if addr and pid and os.path.exists(f"/proc/{pid}"):
            os.environ["DBUS_SESSION_BUS_ADDRESS"] = addr
            return addr, pid

    # Otherwise start a new one
    proc = subprocess.Popen(
        ["dbus-launch", "--sh-syntax", "--exit-with-session"],
        stdout=subprocess.PIPE,
        text=True,
    )
    stdout, _ = proc.communicate()
    addr, pid = None, None
    for line in stdout.splitlines():
        if line.startswith("DBUS_SESSION_BUS_ADDRESS"):
            addr = line.split("=", 1)[1].strip("';")
        elif line.startswith("DBUS_SESSION_BUS_PID"):
            pid = line.split("=", 1)[1].strip("';")

    if not addr or not pid:
        raise RuntimeError("Failed to start DBus session")

    os.environ["DBUS_SESSION_BUS_ADDRESS"] = addr
    with open(SESSION_FILE, "w") as f:
        f.write(f"DBUS_SESSION_BUS_ADDRESS={addr}\nDBUS_SESSION_BUS_PID={pid}\n")

    return addr, pid


def get_picture(appid):
    imgPath = os.path.join(path, f"{appid}.jpg")
    if os.path.isfile(imgPath):
        return imgPath
    protocol = "https" if ssl else "http"
    req = Request(f"{protocol}://{domain}/application?token={token}")
    req.add_header("User-Agent", "Mozilla/5.0")
    r = json.loads(urlopen(req).read())
    for i in r:
        if i["id"] == appid:
            with open(imgPath, "wb") as f:
                req = Request(f"{protocol}://{domain}/{i['image']}?token={token}")
                req.add_header("User-Agent", "Mozilla/5.0")
                f.write(urlopen(req).read())
    return imgPath


def send_notification(message):
    m = json.loads(message)
    urgency = "low" if m["priority"] <= 3 else "normal" if m["priority"] <= 7 else "critical"
    cmd = [
        "notify-send",
        m["title"],
        m["message"],
        "-u", urgency,
        "-i", get_picture(m["appid"]),
        "-a", "Gotify",
        "-h", "string:desktop-entry:gotify-dunst",
    ]
    category = m.get("extras", {}).get("category")
    if category:
        cmd.extend(["-h", f"string:category:{category}"])
    subprocess.Popen(cmd)


def on_message(ws, message):
    send_notification(message)


if __name__ == "__main__":
    addr, pid = ensure_dbus_session()
    print(f"DBus session ready at {addr} (pid={pid})")

    protocol = "wss" if ssl else "ws"
    ws = websocket.WebSocketApp(
        f"{protocol}://{domain}/stream?token={token}",
        on_message=on_message,
    )
    ws.run_forever()
