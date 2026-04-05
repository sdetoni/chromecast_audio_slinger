#!/bin/bash
set -e

APP_CONFIG_DIR="/app/config"
USER_CONFIG_DIR="/config"

# create config dir if missing
mkdir -p "$USER_CONFIG_DIR"

# copy default config on first run
if [ -z "$(ls -A $USER_CONFIG_DIR 2>/dev/null)" ]; then
    echo "Copying default config..."
    cp -r /app/config/* "$USER_CONFIG_DIR/" 2>/dev/null || true
fi

# remove app config and replace with symlink
if [ -e "$APP_CONFIG_DIR" ] && [ ! -L "$APP_CONFIG_DIR" ]; then
    rm -rf "$APP_CONFIG_DIR"
fi

if [ ! -L "$APP_CONFIG_DIR" ]; then
    ln -s "$USER_CONFIG_DIR" "$APP_CONFIG_DIR"
fi

# Run the correct main script
exec python3 /app/runner.py

