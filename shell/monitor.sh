#!/bin/bash

pkill  -f "./main.py"
pkill  "dunst"
pkill  "gotify-dunst"

# Function to be executed when Ctrl-C is pressed
cleanup_and_exit() {
    echo -e "\nCtrl-C detected! Performing cleanup..."
    echo "killing ./main.py"
    kill -9 $PID
    echo "restarting gotify-dunst.service with: systemctl --user restart gotify-dunst.service"
    systemctl --user restart gotify-dunst.service
    # Add your custom cleanup actions here
    exit 1 # Exit with a non-zero status to indicate interruption
}

# Where to store the session info
SESSION_FILE=".dbus_session"

# Function to check if existing session is valid
check_existing_session() {
    if [[ -f "$SESSION_FILE" ]]; then
        echo "Found existing session file, checking validity..."
        source "$SESSION_FILE"
        
        # Check if the PID exists and the address is accessible
        if [[ -n "$DBUS_SESSION_BUS_PID" ]] && [[ -d "/proc/$DBUS_SESSION_BUS_PID" ]]; then
            echo "Existing D-Bus session is valid (PID: $DBUS_SESSION_BUS_PID)"
            export DBUS_SESSION_BUS_ADDRESS
            export DBUS_SESSION_BUS_PID
            return 0
        else
            echo "Existing session is invalid (PID $DBUS_SESSION_BUS_PID not found)"
            return 1
        fi
    else
        echo "No existing session file found"
        return 1
    fi
}

# Try to reuse existing session, create new one if it fails
if ! check_existing_session; then
    echo "Creating new D-Bus session..."
    eval "$(dbus-launch --sh-syntax --exit-with-session)"
    
    # Save the session environment to file
    {
      echo "DBUS_SESSION_BUS_ADDRESS=$DBUS_SESSION_BUS_ADDRESS"
      echo "DBUS_SESSION_BUS_PID=$DBUS_SESSION_BUS_PID"
    } > "$SESSION_FILE"
    echo "New session created and saved"
else
    echo "Reusing existing D-Bus session"
fi


# Start dunst in this DBus session
dunst >> ./dunst.log 2>&1 &

# Small delay to ensure dunst is ready
sleep 1

# Start gotify-dunst (using the same DBus session)
DBUS_SESSION_BUS_ADDRESS="$DBUS_SESSION_BUS_ADDRESS" python3 ../main.py --local &
PID=$!
#echo "The PID of the background process is: $PID"
trap cleanup_and_exit SIGINT

echo "Monitoring DBus messages on bus: $DBUS_SESSION_BUS_ADDRESS"
echo "Press Ctrl+C to stop."

# Attach dbus-monitor to the private session
DBUS_SESSION_BUS_ADDRESS="$DBUS_SESSION_BUS_ADDRESS" dbus-monitor "interface='org.freedesktop.Notifications'"
