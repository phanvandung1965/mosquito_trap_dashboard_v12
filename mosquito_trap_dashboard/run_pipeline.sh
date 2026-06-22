#!/bin/bash
# Pipeline for mosquito_trap_dashboard

# Exit on error
set -e

# Define project directory
PROJECT_DIR="/home/dung/.openclaw/workspace-VP2_codex/projects/mosquito_trap_dashboard"
cd $PROJECT_DIR

# Log file
LOG_FILE="$PROJECT_DIR/logs/pipeline_$(date +%Y%m%d_%H%M%S).log"
mkdir -p "$PROJECT_DIR/logs"

echo "Starting pipeline at $(date)" | tee -a $LOG_FILE

# 1. Run ETL to create star schema
echo "Running ETL to create star schema..." | tee -a $LOG_FILE
python3 etl_to_star_schema.py | tee -a $LOG_FILE
echo "ETL finished." | tee -a $LOG_FILE

# 2. Load star schema into SQLite
echo "Loading star schema into SQLite..." | tee -a $LOG_FILE
python3 load_star_schema_to_sqlite.py | tee -a $LOG_FILE
echo "SQLite load finished." | tee -a $LOG_FILE

# 3. Calculate KPIs
echo "Calculating KPIs..." | tee -a $LOG_FILE
python3 kpi_calculation.py | tee -a $LOG_FILE
echo "KPI calculation finished." | tee -a $LOG_FILE

# 3. Generate the latest dashboard
echo "Generating dashboard..." | tee -a $LOG_FILE
python3 generate_dashboard_v5_1.py | tee -a $LOG_FILE
echo "Dashboard generated: dashboard_v5_1.html" | tee -a $LOG_FILE

echo "Pipeline finished successfully at $(date)" | tee -a $LOG_FILE
