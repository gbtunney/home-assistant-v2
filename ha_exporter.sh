#!/bin/bash
# Home Assistant Registry Exporter
# - Dumps full arrays with a header row (union of keys across all items)
# - CSVs are written to /config/www/ha_exports for easy Nabu Casa access
# - Also exports raw JSON arrays for each registry

OUT="/config/www/ha_exports"
IN="/config/.storage"
HA_HOST="${HA_HOST:-yzcm6icwt327ovrlkovlq6vvtbrwxk6j.ui.nabu.casa}"
BASE_URL="http://${HA_HOST}/local/ha_exports"

mkdir -p "$OUT"

if [ ! -d "$IN" ]; then
    echo "❌ Not found: $IN"
    exit 1
fi

export_registry() {
    local in_file="$1" # e.g. core.entity_registry
    local arr_key="$2" # e.g. entities | devices | areas | labels | floors
    local out_csv="$3" # e.g. ha_entities_raw.csv

    if [ ! -f "$IN/$in_file" ]; then
        echo "⚠️  Skipping $in_file (not found)"
        return 0
    fi

    echo "🔹 Exporting $in_file → $out_csv (.$arr_key with header)"

    jq -r --arg k "$arr_key" '
    # Normalize any JSON value to a CSV-safe string
    def norm:
      if . == null then ""
      elif type == "string" then .
      elif type == "number" or type == "boolean" then tostring
      elif type == "array" or type == "object" then tojson
      else tostring
      end;

    # Grab the array at .data[$k]
    (.data[$k]) as $a
    | if ($a | type) != "array" then
        # If the path is not an array, emit nothing
        empty
      else
        # Build union of keys for header row
        ($a | map(keys) | add | unique) as $cols
        # Header
        | ($cols | @csv),
          # Rows
          ( $a[] | [ $cols[] as $c | (.[$c] | norm) ] | @csv )
      end
  ' "$IN/$in_file" > "$OUT/$out_csv"
}

# New: export raw JSON arrays too
export_registry_json() {
    local in_file="$1"  # e.g. core.entity_registry
    local arr_key="$2"  # e.g. entities | devices | areas | labels | floors
    local out_json="$3" # e.g. ha_entities_raw.json

    if [ ! -f "$IN/$in_file" ]; then
        echo "⚠️  Skipping $in_file (not found)"
        return 0
    fi

    echo "🔹 Exporting $in_file → $out_json (.$arr_key raw JSON)"
    jq --arg k "$arr_key" '
      .data[$k] // [] 
      | if (type=="array") then . else [] end
    ' "$IN/$in_file" > "$OUT/$out_json"
}

# Entities, Devices, Areas, Labels, Floors (CSV)
export_registry "core.entity_registry" "entities" "ha_entities_raw.csv"
export_registry "core.device_registry" "devices" "ha_devices_raw.csv"
export_registry "core.area_registry" "areas" "ha_areas_raw.csv"
export_registry "core.label_registry" "labels" "ha_labels_raw.csv"
export_registry "core.floor_registry" "floors" "ha_floors_raw.csv"

# Entities, Devices, Areas, Labels, Floors (JSON)
export_registry_json "core.entity_registry" "entities" "ha_entities_raw.json"
export_registry_json "core.device_registry" "devices" "ha_devices_raw.json"
export_registry_json "core.area_registry" "areas" "ha_areas_raw.json"
export_registry_json "core.label_registry" "labels" "ha_labels_raw.json"
export_registry_json "core.floor_registry" "floors" "ha_floors_raw.json"

echo "✅ Exports complete (CSV):"
ls -1 "$OUT"/ha_*_raw.csv 2> /dev/null || true

echo "✅ Exports complete (JSON):"
ls -1 "$OUT"/ha_*_raw.json 2> /dev/null || true

echo "📂 Access URLs (Nabu Casa):"
echo "  ${BASE_URL}/ha_entities_raw.csv"
echo "  ${BASE_URL}/ha_devices_raw.csv"
echo "  ${BASE_URL}/ha_areas_raw.csv"
echo "  ${BASE_URL}/ha_labels_raw.csv"
echo "  ${BASE_URL}/ha_floors_raw.csv"
echo "  ${BASE_URL}/ha_entities_raw.json"
echo "  ${BASE_URL}/ha_devices_raw.json"
echo "  ${BASE_URL}/ha_areas_raw.json"
echo "  ${BASE_URL}/ha_labels_raw.json"
echo "  ${BASE_URL}/ha_floors_raw.json"
