#!/bin/bash
# Thomas Breitbach 2026, modified from raspberry pi imager documentation
# create-os-list.sh - Create an OS list entry, from rpi-imager documentation
# usage: ./create-repo-list.sh <image_file> <compressed_file> <name> <description> <icon_url> <download_url> <devices> <output_file>
# example: ./create-repo-list.sh my-os.img my-os.img.xz "My OS" "Custom OS for Pi" "https://example.com/icon.png" "https://example.com/my-os.img.xz" "pi4,pi5" "entry.json"

set -Eeuo pipefail

if [ "$#" -ne 8 ]; then
    echo "Usage: $0 <image_file> <compressed_file> <name> <description> <icon_url> <download_url> <devices> <output_file>" >&2
    exit 1
fi

IMAGE_FILE="$1"
COMPRESSED_FILE="$2"
OS_NAME="$3"
OS_DESC="$4"
ICON_URL="$5"
DOWNLOAD_URL="$6"
DEVICES="$7"  # Comma-separated, e.g., "pi4,pi5"
OUTPUT_FILE="$8"

command -v jq >/dev/null 2>&1 || { echo "jq is required but not installed" >&2; exit 1; }
[ -f "$IMAGE_FILE" ] || { echo "Image file '$IMAGE_FILE' not found" >&2; exit 1; }
[ -f "$COMPRESSED_FILE" ] || { echo "Compressed file '$COMPRESSED_FILE' not found" >&2; exit 1; }

# Calculate SHA256
echo "Calculating SHA256..."
# we need to unxz the xz file to calculate the sha256sum because sha256 sum of orig and decompressed files differ!
SHA256=$(unxz --stdout "$COMPRESSED_FILE" | sha256sum | awk '{print $1}')

# Get file size (GNU stat first, BSD stat as fallback)
SIZE=$(stat -c%s "$IMAGE_FILE" 2>/dev/null || stat -f%z "$IMAGE_FILE")
COMPRESSED_SIZE=$(stat -c%s "$COMPRESSED_FILE" 2>/dev/null || stat -f%z "$COMPRESSED_FILE")

# Get current date
DATE=$(date +%Y-%m-%d)

# Convert comma-separated devices to JSON array
DEVICES_JSON=$(echo "$DEVICES" | jq -R 'split(",") | map(gsub("^\\s+|\\s+$";""))')

# Create JSON entry
ENTRY=$(jq -n \
  --arg name "$OS_NAME" \
  --arg desc "$OS_DESC" \
  --arg icon "$ICON_URL" \
  --arg url "$DOWNLOAD_URL" \
  --argjson size "$SIZE" \
  --arg sha "$SHA256" \
  --argjson download_size "$COMPRESSED_SIZE" \
  --arg date "$DATE" \
  --argjson devices "$DEVICES_JSON" \
  '{
    name: $name,
    description: $desc,
    icon: $icon,
    url: $url,
    extract_size: $size,
    extract_sha256: $sha,
    image_download_size: $download_size,
    release_date: $date,
    devices: $devices
  }')

# Add to existing list or create new one
if [ -f "$OUTPUT_FILE" ]; then
    jq --argjson entry "$ENTRY" '.os_list += [$entry]' "$OUTPUT_FILE" > "${OUTPUT_FILE}.tmp"
    mv "${OUTPUT_FILE}.tmp" "$OUTPUT_FILE"
else
    echo "{\"os_list\": [$ENTRY]}" | jq '.' > "$OUTPUT_FILE"
fi

echo "✓ Added $OS_NAME to $OUTPUT_FILE"
echo "✓ SHA256: $SHA256"
echo "✓ Image size: $SIZE bytes"
echo "✓ Download size: $COMPRESSED_SIZE bytes"