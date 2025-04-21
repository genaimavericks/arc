# /Users/asgiri218/gam-project/rsw/api/kgdatainsights/agent/csv_to_cypher_generator.py
import json
import pandas as pd
import math
from typing import List, Optional, Dict, Any
import os
import sys # Added for path manipulation in main block
from ...utils.llm_provider import LLMProvider
from langchain_core.language_models.chat_models import BaseChatModel


class CsvToCypherGenerator:
    """Generates Neo4j Cypher queries from CSV data based on a graph schema using an LLM."""

    def __init__(self, schema_json: Dict[str, Any], csv_path: str, provider_name: str, model_name: Optional[str] = None):
        """
        Initializes the generator.

        Args:
            schema_json: The graph schema as a Python dictionary.
            csv_path: Path to the CSV data file.
            provider_name: Name of the LLM provider ('openai' or 'google').
            model_name: Specific model name (optional, uses provider default if None).
        """
            
        self.schema = schema_json # Assign directly
        self.csv_path = csv_path
        self.provider_name = provider_name
        self.model_name = model_name
        
        self.dataframe = self._load_csv()
        self.llm = self._initialize_llm()

    def _load_csv(self) -> Optional[pd.DataFrame]:
        """Loads the data from the CSV file."""
        try:
            #TEMP Load only part instead of full!! else it will brk in
            df = pd.read_csv(self.csv_path, nrows=100)
            # Convert NaNs or other pandas nulls to None for consistency
            df = df.astype(object).where(pd.notnull(df), None)
            print(f"Successfully loaded CSV: {self.csv_path} with {len(df)} data rows.")
            return df
        except FileNotFoundError:
            print(f"Error: CSV file not found at {self.csv_path}")
            return None
        except Exception as e:
            print(f"An error occurred loading CSV {self.csv_path}: {e}")
            return None
            
    def _initialize_llm(self) -> Optional[BaseChatModel]:
        """Initializes the LangChain chat model."""
        try:
            llm_instance = LLMProvider.get_llm(self.provider_name, self.model_name)
            if not llm_instance:
                 print(f"Failed to initialize LLM for provider {self.provider_name}.")
                 return None
            print(f"LLM initialized successfully: {self.provider_name} - {self.model_name or 'default'}")
            return llm_instance
        except Exception as e:
            print(f"Error during LLM initialization: {e}")
            return None

    def _select_rows(self) -> List[Dict[str, Any]]:
        """Selects the 2nd, middle, and last data rows from the DataFrame."""
        selected_rows = []
        if self.dataframe is None or len(self.dataframe) < 2:
            print("Warning: DataFrame is missing or has less than 2 data rows. Cannot select rows.")
            return selected_rows

        num_rows = len(self.dataframe)
        indices_to_select = []

        # 2nd data row (index 1)
        if num_rows >= 2:
            indices_to_select.append(1)
        
        # Last data row (index num_rows - 1)
        last_index = num_rows - 1
        if last_index not in indices_to_select:
            indices_to_select.append(last_index)
        
        # Remove duplicates potentially introduced by small DFs and logic above
        indices_to_select = sorted(list(set(indices_to_select)))

        print(f"Selecting data rows at indices: {indices_to_select}")
        
        for index in indices_to_select:
            try:
                # Convert row to dictionary {column_name: value}
                row_dict = self.dataframe.iloc[index].to_dict()
                selected_rows.append(row_dict)
            except IndexError:
                 print(f"Warning: Could not access row at index {index}.")
                 
        return selected_rows

    def _create_prompt(self, row_data: Dict[str, Any]) -> str:
        """
        Creates a detailed prompt for the LLM to generate Cypher queries.
        """
        schema_str = json.dumps(self.schema, indent=2)
        # Use headers from the dataframe itself
        headers = list(self.dataframe.columns)
        row_values_str = ', '.join([f"{k}: '{v}'" if isinstance(v, str) else f"{k}: {v}" for k, v in row_data.items()])

        prompt = f"""
        Given the following Neo4j graph schema:
        ```json
        {schema_str}
        ```

        And the following data row from a CSV file (with headers corresponding to potential node/relationship properties):
        Headers: {headers}
        Data: {{ {row_values_str} }}

        Generate the Neo4j Cypher MERGE statements required to represent this data row in the graph according to the schema. 
        - Use MERGE to avoid creating duplicate nodes.
        - Create nodes first, then relationships.
        - Ensure properties are correctly assigned based on the schema and the data row.
        - Handle potential data type conversions if necessary (e.g., strings to numbers where appropriate based on schema hints, though the schema provided doesn't specify types).
        - IMPORTANT: Output ONLY the valid Cypher query block. 
        - If you cannot determine the correct Cypher queries based on the schema and data (e.g., ambiguous mapping, missing crucial information), output the single word: None
        
        Cypher Query:
        """
        return prompt

    def generate_cypher_for_rows(self) -> List[Optional[str]]:
        """ 
        Generates Cypher queries for the selected rows (2nd, middle, last).

        Returns:
            A list containing the generated Cypher query string for each selected row,
            or None for rows where generation failed or was not possible.
        """
        if self.schema is None or self.dataframe is None or self.llm is None:
            print("Error: Cannot generate Cypher queries due to missing schema, dataframe, or LLM.")
            return []

        selected_rows_data = self._select_rows()
        if not selected_rows_data:
            print("No rows selected to generate Cypher for.")
            return []
            
        cypher_queries = []
        
        for i, row_data in enumerate(selected_rows_data):
            print(f"\n--- Generating Cypher for Row {i+1} ---") # User-friendly 1-based count
            print(f"Row Data: {row_data}")
            prompt = self._create_prompt(row_data)
            # print(f"Prompt:\n{prompt}\n") # Uncomment for debugging prompts

            try:
                response = self.llm.invoke(prompt)
                # Assuming response structure might vary; aim for content attribute or similar
                # Adjust based on actual LangChain model response object structure
                generated_text = ""
                if hasattr(response, 'content'):
                    generated_text = response.content.strip()
                elif isinstance(response, str):
                     generated_text = response.strip()
                else:
                     # Handle other potential response types or structures if needed
                     print(f"Warning: Unexpected LLM response structure: {type(response)}")
                     generated_text = str(response).strip() # Best effort conversion
                
                print(f"LLM Raw Response: {generated_text}") # Log the raw response

                if generated_text and generated_text.lower() != 'none' and ('MERGE' in generated_text.upper() or 'CREATE' in generated_text.upper()): # Basic check for Cypher keywords
                    # Further clean up potentially extraneous text if LLM didn't follow instructions perfectly
                    if 'Cypher Query:' in generated_text:
                         generated_text = generated_text.split('Cypher Query:')[-1].strip()
                    if generated_text.startswith('```cypher'):
                        generated_text = generated_text[len('```cypher'):].strip()
                    if generated_text.startswith('```'):
                         generated_text = generated_text[3:].strip()
                    if generated_text.endswith('```'):
                        generated_text = generated_text[:-3].strip()
                        
                    print(f"Generated Cypher (Cleaned):\n{generated_text}")
                    cypher_queries.append(generated_text)
                else:
                    print("LLM indicated no query could be generated or returned empty/invalid response.")
                    cypher_queries.append(None)

            except Exception as e:
                print(f"An error occurred invoking the LLM or processing its response for row {i+1}: {e}")
                cypher_queries.append(None)
        
        return cypher_queries

# Example Usage (Optional - for testing this script directly)
if __name__ == '__main__':
    # Adjust paths relative to where you run this script, or use absolute paths
    # Calculation updated for new location: rsw/api/kgdatainsights/agent
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))) # -> rsw
    
    # Add project root to path to help with imports if run directly
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
        
    # Define paths relative to the calculated project root
    schema_file_path = os.path.join(project_root, 'test', 'api', 'kgdatainsights', 'schema.json') # Path still needed here
    csv_file = os.path.join(project_root, 'api', 'uploads', 'foamfactory_1000.csv')
    
    print(f"Project Root: {project_root}")
    print(f"Schema Path: {schema_file_path}")
    print(f"CSV Path: {csv_file}")

    # Load schema from file first
    loaded_schema = None
    try:
        with open(schema_file_path, 'r') as f:
            loaded_schema = json.load(f)
    except Exception as e:
         print(f"Error loading schema file {schema_file_path}: {e}")
         sys.exit(1)

    # Ensure API keys are set as environment variables (OPENAI_API_KEY or GOOGLE_API_KEY)
    provider = 'google' # or 'google' # Keep the user's last choice
    # model = 'gpt-4' # Optional: specific model
    model = None # Use default for the provider

    if loaded_schema is None:
         print(f"Error: Schema was not loaded successfully.")
    elif not os.path.exists(csv_file):
         print(f"Error: CSV file not found at calculated path: {csv_file}")
    else:
        # Check for API keys before initializing
        key_needed = "OPENAI_API_KEY" if provider == 'openai' else "GOOGLE_API_KEY"
        if not os.getenv(key_needed):
            print(f"Error: Environment variable {key_needed} is not set.")
        else:
            # Re-import LLMProvider here if it was None due to initial import errors when run as script
            if LLMProvider is None:
                 try:
                     from api.utils.llm_provider import LLMProvider
                 except ImportError:
                      print("Failed to dynamically import LLMProvider in main block.")
                      # Exit or handle appropriately
                      sys.exit(1)
                      
            try:
                # Pass the loaded schema dictionary to the constructor
                generator = CsvToCypherGenerator(loaded_schema, csv_file, provider, model)
                if generator.schema and generator.dataframe is not None and generator.llm:
                    generated_queries = generator.generate_cypher_for_rows()
                    print("\n--- Final Generated Cypher Queries ---")
                    for i, query in enumerate(generated_queries):
                        print(f"Query for Row {i+1}:")
                        if query:
                            print(query)
                        else:
                            print("None")
                        print("---")
                else:
                     print("Generator initialization failed. Check logs.")
            except ImportError as e:
                 print(f"Import Error during generation: {e}")
            except Exception as e:
                 print(f"An unexpected error occurred during generation: {e}")
