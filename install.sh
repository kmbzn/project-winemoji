#!/bin/bash
set -e

INSTALL_DIR="$HOME/.local/share/winemoji"
BIN_DIR="$HOME/.local/bin"
REPO_URL="https://github.com/kmbzn/project-winemoji.git"

echo "[*] Installing Winemoji..."

# 1. Clone or update repository
if [ -d "$INSTALL_DIR" ]; then
    echo "[*] Winemoji directory already exists. Updating..."
    cd "$INSTALL_DIR"
    git pull
else
    echo "[*] Cloning repository to $INSTALL_DIR..."
    git clone "$REPO_URL" "$INSTALL_DIR"
fi

# 2. Ensure bin directory exists
mkdir -p "$BIN_DIR"

# 3. Create symlink
echo "[*] Creating symlink in $BIN_DIR..."
ln -sf "$INSTALL_DIR/winemoji" "$BIN_DIR/winemoji"
chmod +x "$INSTALL_DIR/winemoji"

echo ""
echo "[+] Successfully installed Winemoji!"
echo ""
echo "------------------------------------------------------------------"
echo "To run 'winemoji' from anywhere, make sure $BIN_DIR is in your PATH."
echo "If it is not, add the following line to your ~/.bashrc or ~/.zshrc:"
echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
echo "------------------------------------------------------------------"
echo ""
echo "Run 'winemoji --help' to get started."
