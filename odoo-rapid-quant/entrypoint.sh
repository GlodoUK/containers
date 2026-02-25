#!/usr/bin/env bash
set -euo pipefail

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BINARY_PATH="${SCRIPT_DIR}/odoo-rapid-quant"

# Validate required environment variables
: "${PGHOST:?PGHOST must be set}"
: "${PGUSER:?PGUSER must be set}"
: "${PGPASSWORD:?PGPASSWORD must be set}"
: "${PGDATABASE:?PGDATABASE must be set (source Odoo DB name)}"
: "${WAREHOUSE_IDS:?WAREHOUSE_IDS must be set (space-separated list)}"
# Optional: use custom port
PGPORT="${PGPORT:-5432}"
# Database URLs
SRC_DB_URL="postgres://${PGUSER}:${PGPASSWORD}@${PGHOST}:${PGPORT}/${PGDATABASE}?statement-cache-capacity=0"
SINK_DB_URL="postgres://${PGUSER}:${PGPASSWORD}@${PGHOST}:${PGPORT}/${PGDATABASE}?statement-cache-capacity=0"
# Verify odoo-rapid-quant exists or auto-download
if [[ ! -x "$BINARY_PATH" ]]; then
  echo "Error: odoo-rapid-quant not found" >&2
fi
# Create table if needed
echo "Creating stock availability table..."
psql -h psql-rw -U "$PGUSER" -d "$PGDATABASE" -v ON_ERROR_STOP=1 <<'SQL'
CREATE TABLE IF NOT EXISTS stock_rapid_quant (
    product_id        INTEGER NOT NULL,
    warehouse_id      INTEGER NOT NULL,
    quantity          NUMERIC NOT NULL,
    reserved          NUMERIC NOT NULL,
    incoming          NUMERIC NOT NULL,
    outgoing          NUMERIC NOT NULL,
    buildable         NUMERIC NOT NULL,
    free_immediately  NUMERIC NOT NULL,
    virtual_available NUMERIC NOT NULL,
    write_date        TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT stock_rapid_quant_pkey PRIMARY KEY (product_id, warehouse_id),
    CONSTRAINT stock_rapid_quant_product_fk
        FOREIGN KEY (product_id) REFERENCES product_product(id),
    CONSTRAINT stock_rapid_quant_warehouse_fk
        FOREIGN KEY (warehouse_id) REFERENCES stock_warehouse(id)
);
SQL
SINK_STMT="INSERT INTO stock_rapid_quant (product_id, warehouse_id, quantity, reserved, incoming, outgoing, buildable, free_immediately, virtual_available, write_date) VALUES ({product_id}, {warehouse_id}, {quantity}, {reserved}, {incoming}, {outgoing}, {buildable}, {free_immediately}, {virtual_available}, NOW()) ON CONFLICT (product_id, warehouse_id) DO UPDATE SET quantity = EXCLUDED.quantity, reserved = EXCLUDED.reserved, incoming = EXCLUDED.incoming, outgoing = EXCLUDED.outgoing, buildable = EXCLUDED.buildable, free_immediately = EXCLUDED.free_immediately, virtual_available = EXCLUDED.virtual_available, write_date = NOW()"
# Process each warehouse
for warehouse_id in $WAREHOUSE_IDS; do
  echo "[$(date -Iseconds)] Processing warehouse $warehouse_id..."
  "$BINARY_PATH" \
    --log-level info \
    --allow-negative \
    --warehouse "$warehouse_id" \
    --src-db-url "$SRC_DB_URL" \
    --sink-db-url "$SINK_DB_URL" \
    --sink-db-stmt "$SINK_STMT"
done
echo "[$(date -Iseconds)] All warehouses processed successfully"
