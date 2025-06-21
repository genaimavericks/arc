"""
Constants for KGInsights module
"""

# Data loading stages with weights for progress calculation
DATA_LOADING_STAGES = {
    "schema_loading": {
        "name": "Schema Loading",
        "weight": 5,  # Percentage of total job progress
        "description": "Loading schema configuration"
    },
    "data_validation": {
        "name": "Data Validation", 
        "weight": 5,
        "description": "Validating data files"
    },
    "csv_generation": {
        "name": "CSV Generation", 
        "weight": 20,
        "description": "Creating CSV files from data and schema"
    },
    "neo4j_import": {
        "name": "Neo4j Import", 
        "weight": 40,
        "description": "Importing data into Neo4j database"
    },
    "neo4j_startup": {
        "name": "Neo4j Startup", 
        "weight": 5,
        "description": "Starting Neo4j with imported data"
    },
    "stats_collection": {
        "name": "Statistics Collection", 
        "weight": 5,
        "description": "Collecting database statistics"
    },
    "prompt_generation_prep": {
        "name": "Prompt Generation Preparation", 
        "weight": 2,
        "description": "Preparing for prompt generation"
    },
    "prompt_generation": {
        "name": "Prompt Generation", 
        "weight": 8,
        "description": "Generating Cypher prompts"
    },
    "qa_generation": {
        "name": "QA Generation", 
        "weight": 5,
        "description": "Generating QA prompts"
    },
    "query_generation": {
        "name": "Query Generation", 
        "weight": 5,
        "description": "Generating sample queries"
    }
}
