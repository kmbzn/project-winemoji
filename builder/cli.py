#!/usr/bin/env python3
import os
import sys
import argparse
from processor import build_winemoji

def main():
    parser = argparse.ArgumentParser(
        description="Winemoji - Universal tool for resolving emoji rendering errors in Wine environments"
    )
    parser.add_argument(
        "-b", "--base",
        required=True,
        help="Path to the base font file (.ttf or .otf) you want to patch."
    )
    parser.add_argument(
        "-o", "--output",
        help="Path to the output font file. (Default: [base_font_name]-winemoji.ttf)"
    )
    parser.add_argument(
        "-e", "--emoji",
        help="Path to the Noto Emoji font file. (Default: assets/NotoEmoji.ttf in builder directory)"
    )
    parser.add_argument(
        "--version",
        action="version",
        version="Winemoji 1.0"
    )
    
    args = parser.parse_args()
    
    # 1. Base font verification
    if not os.path.exists(args.base):
        print(f"Error: Base font file not found: {args.base}", file=sys.stderr)
        sys.exit(1)
        
    # 2. Emoji font default value & verification
    if args.emoji:
        emoji_path = args.emoji
    else:
        # Default to assets/NotoEmoji.ttf relative to the script location
        script_dir = os.path.dirname(os.path.abspath(__file__))
        emoji_path = os.path.join(script_dir, "assets", "NotoEmoji.ttf")
        
    if not os.path.exists(emoji_path):
        print(f"Error: Emoji font file not found: {emoji_path}", file=sys.stderr)
        sys.exit(1)
        
    # 3. Output font default value
    if args.output:
        output_path = args.output
    else:
        base_dir = os.path.dirname(args.base)
        # If output directory is not writable (e.g. system directory), fallback to user local fonts
        if base_dir and not os.access(base_dir, os.W_OK):
            base_dir = os.path.expanduser("~/.local/share/fonts")
            os.makedirs(base_dir, exist_ok=True)
        elif not base_dir:
            base_dir = os.getcwd()
            
        base_name, _ = os.path.splitext(os.path.basename(args.base))
        output_path = os.path.join(base_dir, f"{base_name}-winemoji.ttf")
        
    print(f"[*] Base Font: {args.base}")
    print(f"[*] Emoji Font: {emoji_path}")
    print(f"[*] Output Font: {output_path}")
    print("[*] Starting build...")
    
    try:
        def progress_cb(msg):
            print(f"  > {msg}")
            
        build_winemoji(args.base, emoji_path, output_path, progress_callback=progress_cb)
        print("[+] Build completed successfully!")
    except Exception as e:
        print(f"[-] Error occurred: {e}", file=sys.stderr)
        sys.exit(2)

if __name__ == "__main__":
    main()
