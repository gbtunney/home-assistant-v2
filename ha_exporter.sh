#!/bin/bash
# Home Assistant Raw Registry Export Script with Floors + Web Exposure

OUT="/config/www/ha_exports"
HA_URL="${HA_URL:-homeassistant.local:8123}/local/ha_exports"
mkdir -p "$OUT"
cd /config/.storage || { echo "❌ .storage not found"; exit 1; }

echo "🔹 Exporting entities..."
jq -r '
  .data.entities[]
  | [
      .entity_id,
      .device_id,
      .platform,
      .name,
      .original_name,
      .disabled_by,
      .hidden_by,
      (.labels // [] | join(";")),
      .area_id
    ]
  | @csv
' core.entity_registry > "$OUT/ha_entities_raw.csv"

echo "🔹 Exporting devices..."
jq -r '
  .data.devices[]
  | [
      .id,
      (.name_by_user // .name // ""),
      .manufacturer,
      .model,
      .area_id,
      .via_device_id,
      (.entry_type // ""),
      (.disabled_by // "")
    ]
  | @csv
' core.device_registry > "$OUT/ha_devices_raw.csv"

echo "🔹 Exporting areas..."
jq -r '
  .data.areas[]
  | [
      .id,
      .name,
      (
        if (.aliases | type) == "array" then
          (.aliases | join(";"))
        else
          (.aliases // "")
        end
      ),
      (.floor_id // "")
    ]
  | @csv
' core.area_registry > "$OUT/ha_areas_raw.csv"

echo "🔹 Exporting labels..."
if [ -f core.label_registry ]; then
  jq -r '
    .data.labels[]
    | [
        .id,
        .name,
        .color,
        (.description // "")
      ]
    | @csv
  ' core.label_registry > "$OUT/ha_labels_raw.csv"
else
  echo "⚠️ No label registry found; skipping label export."
fi

echo "🔹 Exporting floors..."
if [ -f core.floor_registry ]; then
  jq -r '
    .data.floors[]
    | [
        .id,
        .name,
        (.aliases // [] | join(";")),
        (.level // "")
      ]
    | @csv
  ' core.floor_registry > "$OUT/ha_floors_raw.csv"
  echo "✅ Floors exported to ha_floors_raw.csv"
else
  echo "⚠️ No floor registry found; skipping floors export."
fi

echo "✅ Raw registry exports complete:"
ls -1 "$OUT"/ha_*_raw.csv

echo "📂 Access your exports at:"
echo "🔹  http://$HA_URL/ha_entities_raw.csv"
echo "🔹  http://$HA_URL/ha_devices_raw.csv"
echo "🔹  http://$HA_URL/ha_areas_raw.csv"
echo "🔹  http://$HA_URL/ha_labels_raw.csv"
echo "🔹  http://$HA_URL/ha_floors_raw.csv"