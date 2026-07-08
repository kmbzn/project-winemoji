#!/bin/bash
set -e

# Change directory to script location
cd "$(dirname "$0")"

# Register desktop application shortcut if it doesn't exist
DESKTOP_FILE="$HOME/.local/share/applications/winemoji.desktop"
if [ ! -f "$DESKTOP_FILE" ]; then
    echo "Registering desktop shortcut..."
    mkdir -p "$HOME/.local/share/applications"
    cat << EOL > "$DESKTOP_FILE"
[Desktop Entry]
Name=Winemoji Builder
Exec=$(pwd)/run.sh
Icon=$(pwd)/assets/logo.png
Terminal=false
Type=Application
Path=$(pwd)
Categories=Utility;
EOL
    chmod +x "$DESKTOP_FILE"
    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
fi

# Check for GTK dependencies
if ! dpkg -s python3-gi >/dev/null 2>&1; then
    echo "python3-gi is missing. Attempting to install system dependencies..."
    sudo apt update
    sudo apt install -y python3-gi gir1.2-gtk-3.0
fi

# Recreate virtual environment with system site packages to access PyGObject
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment with system site packages..."
    python3 -m venv --system-site-packages .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Install requirements
echo "Checking requirements..."
pip install -r requirements.txt --quiet

# Run the application
echo "Starting Winemoji Builder..."
python3 main.py
