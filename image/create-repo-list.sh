#!/bin/bash
# Thomas Breitbach 2026, modified from raspberry pi imager documentation
# create-os-list.sh - Create an OS list entry, from rpi-imager documentation
# usage: ./create-os-list.sh <image_file> <name> <description> <icon_url> <download_url> <devices> <output_file>
# example: ./create-os-list.sh my-os.img "My OS" "Custom OS for Pi" "https://example.com/icon.png" "https://example.com/my-os.img.xz" "pi4,pi5" "entry.json"

set -e

IMAGE_FILE="$1"
COMPRESSED_FILE="$2"
OS_NAME="$3"
OS_DESC="$4"
ICON_URL="$5"
DOWNLOAD_URL="$6"
DEVICES="$7"  # Comma-separated, e.g., "pi4,pi5"
OUTPUT_FILE="$8"

if [ "$#" -lt 7 ]; then
    echo "Usage: $0 <image_file> <name> <description> <icon_url> <download_url> <devices> <output_file>"
    exit 1
fi

# Calculate SHA256
echo "Calculating SHA256..."
SHA256=$(sha256sum "$IMAGE_FILE" | awk '{print $1}')

# Get file size
SIZE=$(stat -f%z "$IMAGE_FILE" 2>/dev/null || stat -c%s "$IMAGE_FILE")
COMPRESSED_SIZE=$(stat -f%z "$COMPRESSED_FILE" 2>/dev/null || stat -c%s "$COMPRESSED_FILE")

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