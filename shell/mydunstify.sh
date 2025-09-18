#!/bin/bash

SESSION_FILE=".dbus_session"

if [[ ! -f "$SESSION_FILE" ]]; then
  echo "No DBus session file found at $SESSION_FILE"
  exit 1
fi

# Load the private DBus session environment
source "$SESSION_FILE"

# Forward all arguments to dunstify using the private DBus
DBUS_SESSION_BUS_ADDRESS="$DBUS_SESSION_BUS_ADDRESS" dunstify "$@"

