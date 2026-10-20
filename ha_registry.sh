#!/bin/bash
set -euo pipefail

SRC="/config/.storage"
DEST="/config/ha_registry"

mkdir -p "$DEST"

files=(
  core.area_registry
  core.category_registry
  core.device_registry
  core.entity_registry
  core.floor_registry
  core.label_registry
  localtuya_remotes_codes
)

for file in "${files[@]}"; do
  if [[ -f "$SRC/$file" ]]; then
    cp "$SRC/$file" "$DEST/$file.json"
    echo "✓ $file"
  else
    echo "– $file (not found)"
  fi
done

echo "Formatting JSON..."
for file in "$DEST"/*.json; do
  python3 -m json.tool "$file" > "$file.tmp" && mv "$file.tmp" "$file"
done
echo "✓ Registry backup complete"