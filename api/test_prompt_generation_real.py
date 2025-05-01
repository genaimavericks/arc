import pytest
import logging
from .kgdatainsights.data_insights_api import get_schema_aware_assistant
from .models import Schema  # Adjust import if needed
from .db_config import SessionLocal  # Adjust import if needed

# Replace this with a real schema_id from your database
REAL_SCHEMA_ID = "1"  # <-- Update this value as needed

@pytest.mark.usefixtures("caplog", "capfd")
def test_real_prompt_generation(caplog, capfd):
    # Set logging to DEBUG for all loggers
    logging.basicConfig(level=logging.DEBUG, force=True)
    caplog.set_level(logging.DEBUG)

    db = SessionLocal()
    schema_id = REAL_SCHEMA_ID
    try:
        schema_db = db.query(Schema).filter(Schema.id == schema_id).first()
        assert schema_db is not None, f"Schema with id {schema_id} not found in DB"
        assert schema_db.schema, "Schema field is empty"
        assert schema_db.db_id, "db_id field is empty"

        assistant = get_schema_aware_assistant(schema_db.db_id, schema_id, schema_db.schema)
        # This should generate prompt templates and sample queries
        assistant._ensure_prompt()
        print(f"Prompt templates and queries generated for schema_id={schema_id}")

        # Show captured print output
        out, err = capfd.readouterr()
        if out:
            print("Captured STDOUT:\n", out)
        if err:
            print("Captured STDERR:\n", err)

        # Show captured logs
        if caplog.records:
            print("\nCaptured LOGS:")
            for record in caplog.records:
                print(f"{record.levelname}: {record.getMessage()}")

    finally:
        db.close()
