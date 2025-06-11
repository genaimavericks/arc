"""
Script Executor - Safe execution of generated Python scripts
"""

import os
import sys
import json
import logging
import traceback
import tempfile
import subprocess
import re
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class ScriptExecutor:
    """Safely execute generated Python scripts in isolated environment"""
    
    def __init__(self):
        self.data_dir = Path(__file__).parent.parent / "data"
        self.temp_dir = Path(tempfile.gettempdir()) / "datapuur_ai"
        self.temp_dir.mkdir(exist_ok=True)
        self.executor = ThreadPoolExecutor(max_workers=2)
    
    async def execute_script(self,
                           script: str,
                           input_file_path: str,
                           output_file_path: Optional[str] = None,
                           timeout: int = 300) -> Dict[str, Any]:
        """Execute a Python script safely with timeout"""
        
        # Generate unique execution ID
        exec_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        
        # Create temporary script file
        script_path = self.temp_dir / f"script_{exec_id}.py"
        
        # Prepare the script with safety wrapper
        wrapped_script = self._wrap_script(script, input_file_path, output_file_path)
        
        try:
            # Write script to file
            script_path.write_text(wrapped_script)
            
            # Execute in subprocess with timeout
            result = await self._run_script_subprocess(script_path, timeout)
            
            return result
            
        except Exception as e:
            logger.error(f"Script execution error: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc()
            }
        finally:
            # Cleanup
            if script_path.exists():
                script_path.unlink()
    
    def _wrap_script(self, script: str, input_file_path: str, output_file_path: Optional[str]) -> str:
        """Wrap script with safety measures and standard interface"""
        
        # Define output file setting
        output_setting = f"OUTPUT_FILE = DATA_DIR / '{output_file_path}'" if output_file_path else 'OUTPUT_FILE = None'
        
        # Build wrapper script without complex f-string nesting
        wrapper = f'''
import sys
import json
import traceback
import pandas as pd
import numpy as np
import os
from pathlib import Path
from datetime import datetime

# Set up paths
DATA_DIR = Path("{self.data_dir}")
INPUT_FILE = DATA_DIR / "{input_file_path}"

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

# Set output file path
{output_setting}

log_messages = []

# Execution result container
result = {{
    "success": False,
    "input_file": str(INPUT_FILE),
    "output_file": str(OUTPUT_FILE) if OUTPUT_FILE else None,
    "statistics": {{}},
    "messages": [],
    "error": None
}}

def log_message(msg):
    """Log a message to the result"""
    timestamp = datetime.now().isoformat()
    formatted_msg = f"[{{datetime.now().strftime('%H:%M:%S')}}] {{msg}}"

    # Store in result for returning to frontend
    result["messages"].append({{
        "timestamp": timestamp,
        "message": str(msg)
    }})

    # Store in log_messages list for easy access
    log_messages.append(formatted_msg)

    # Print to stdout for capturing in logs
    print(formatted_msg)

try:
    # User script starts here
    log_message("Starting script execution...")
    
{self._indent_script(script)}
    
    # User script ends here
    
    result["success"] = True
    log_message("Script completed successfully")
    
except Exception as e:
    result["error"] = str(e)
    result["traceback"] = traceback.format_exc()
    log_message(f"Error: {{str(e)}}")

# Output result as JSON
print("\\n===RESULT_START===")
print(json.dumps(result, indent=2, default=str))
print("===RESULT_END===")
'''
        return wrapper
    
    def _indent_script(self, script: str) -> str:
        """Indent script lines for embedding"""
        lines = script.split('\n')
        return '\n'.join('    ' + line for line in lines)
    
    async def _run_script_subprocess(self, script_path: Path, timeout: int) -> Dict[str, Any]:
        """Run script in subprocess with timeout"""
        
        cmd = [sys.executable, str(script_path)]
        
        logger.info(f"Running script: {script_path} with Python: {sys.executable}")
        
        try:
            # Run subprocess
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Wait for completion with timeout
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
            
            # Parse output
            output = stdout.decode('utf-8')
            stderr_output = stderr.decode('utf-8') if stderr else ""
            
            # Log process return code and any stderr output
            logger.info(f"Script process completed with return code: {process.returncode}")
            if stderr_output:
                logger.warning(f"Script stderr output:\n{stderr_output}")
            
            # Extract JSON result
            if "===RESULT_START===" in output and "===RESULT_END===" in output:
                start = output.find("===RESULT_START===") + len("===RESULT_START===")
                end = output.find("===RESULT_END===")
                result_json = output[start:end].strip()
                
                try:
                    result = json.loads(result_json)
                    
                    # Capture all console output before the result
                    console_output = output[:start].strip()
                    if console_output:
                        if not result.get("messages"):
                            result["messages"] = []
                        result["messages"].insert(0, {
                            "timestamp": datetime.now().isoformat(),
                            "message": f"Script console output: {console_output}"
                        })
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse script result JSON: {e}")
                    logger.error(f"Raw JSON: {result_json}")
                    result = {
                        "success": False,
                        "error": f"Failed to parse script result: {e}",
                        "output": output
                    }
            else:
                # Fallback if no structured output
                logger.warning("Script output doesn't contain result markers")
                result = {
                    "success": process.returncode == 0,
                    "output": output,
                    "error": stderr_output if stderr_output else None,
                    "messages": [{
                        "timestamp": datetime.now().isoformat(),
                        "message": f"Raw script output: {output[:500]}...(truncated)"
                    }] if output else []
                }
            
            return result
            
        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": f"Script execution timed out after {timeout} seconds"
            }
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": "Failed to parse script output",
                "output": output if 'output' in locals() else None,
                "parse_error": str(e)
            }
    
    def clean_script(self, script: str) -> str:
        """Clean and fix common syntax issues in AI-generated scripts using LLM"""
        from api.gen_ai_layer.models import create_model
        
        if not script:
            return ""
            
        # Basic cleaning steps that don't require LLM
        
        # Remove markdown code blocks if present
        if script.startswith("```python") or script.startswith("```py"):
            lines = script.split("\n")
            in_code_block = False
            cleaned_lines = []
            
            for line in lines:
                if line.startswith("```"):
                    in_code_block = not in_code_block
                    continue
                    
                if in_code_block or not in_code_block and len(cleaned_lines) > 0:
                    cleaned_lines.append(line)
                    
            script = "\n".join(cleaned_lines)
        elif script.endswith("```"):
            # Just remove the end marker
            script = script.replace("```", "")
        
        # Try to compile the script to check for syntax errors
        try:
            compile(script, '<string>', 'exec')
            # If no errors, we can skip the LLM step
            return script
        except SyntaxError as e:
            # There's a syntax error, use LLM to fix it
            error_message = str(e)
            
            # Create LLM instance
            model = create_model()
            
            # Prepare prompt for script cleaning
            prompt = f"""
            I have a Python script with syntax errors that needs to be fixed. 
            Here is the error: {error_message}
            
            Please fix the script to make it valid Python code. Don't add any comments or explanations, 
            just return the fixed script. Don't change the functionality, just fix syntax issues like:
            - Unterminated string literals
            - Missing closing quotes or parentheses
            - Inconsistent indentation
            - Incorrectly escaped characters
            - Other syntax errors
            
            Here is the script:
            ```python
            {script}
            ```
            
            Return the fixed script as valid Python code without any markdown formatting or explanation.
            """
            
            # Get LLM response
            response = model.chat(
                messages=[{"role": "user", "content": prompt}],
                system_message="You are an expert Python programmer. Fix syntax errors in Python code while preserving functionality."
            )
            
            # Extract fixed script from LLM response
            fixed_script = response.content
            
            # Remove any markdown formatting the LLM might have added
            if fixed_script.startswith("```python") or fixed_script.startswith("```py"):
                lines = fixed_script.split("\n")
                code_lines = []
                in_code_block = False
                
                for line in lines:
                    if line.startswith("```"):
                        in_code_block = not in_code_block
                        continue
                        
                    if in_code_block:
                        code_lines.append(line)
                        
                fixed_script = "\n".join(code_lines)
            
            # Validate the fixed script
            try:
                compile(fixed_script, '<string>', 'exec')
                logger.info("LLM successfully fixed script syntax errors")
                return fixed_script
            except SyntaxError as e2:
                # If LLM couldn't fix it, log and return the original
                logger.warning(f"LLM failed to fix script: {str(e2)}")
                # Try one more basic fix - ensure imports
                if "import pandas" not in script:
                    script = "import pandas as pd\n" + script
                if "import numpy" not in script:
                    script = "import numpy as np\n" + script
                return script
    
    def validate_script(self, script: str) -> Dict[str, Any]:
        """Validate script for safety and syntax"""
        
        # Forbidden imports/operations
        forbidden_patterns = [
            "exec(", "eval(", "__import__",
            "subprocess", "os.system", "open(",
            "requests", "urllib", "socket"
        ]
        
        issues = []
        
        # First check for forbidden patterns in original script
        for pattern in forbidden_patterns:
            if pattern in script:
                issues.append(f"Forbidden operation: {pattern}")
        
        # If there are security issues, don't proceed with cleaning
        if issues:
            return {
                "valid": False,
                "issues": issues,
                "cleaned_script": None
            }
        
        # Clean script using the LLM-based approach
        cleaned_script = self.clean_script(script)
        
        # Double-check the LLM didn't add any forbidden patterns
        for pattern in forbidden_patterns:
            if pattern in cleaned_script and pattern not in script:
                # This would be suspicious - LLM added a forbidden pattern
                issues.append(f"LLM cleaning added forbidden operation: {pattern}")
                return {
                    "valid": False,
                    "issues": issues,
                    "cleaned_script": None
                }
        
        # Final syntax check
        try:
            compile(cleaned_script, '<string>', 'exec')
        except SyntaxError as e:
            issues.append(f"Syntax error: {str(e)}")
            # If we still have syntax errors after cleaning, log it
            logger.warning(f"LLM cleaning failed to fix all syntax errors: {str(e)}")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "cleaned_script": cleaned_script if len(issues) == 0 else None
        }
    
    async def execute_transformation(self,
                                   script: str,
                                   input_file: str,
                                   job_id: str,
                                   progress_callback=None) -> Dict[str, Any]:
        """Execute transformation script with progress tracking"""
        
        # Get the input filename to create output filename with transformed_ prefix
        try:
            input_filename = Path(input_file).name
            # For path-like inputs, use the basename; otherwise use the whole string
            if "/" in input_filename or "\\" in input_filename:
                input_filename = Path(input_filename).name
        except Exception as e:
            logger.error(f"Error processing input filename: {str(e)}")
            input_filename = "transformed_output.parquet"
        
        # Generate output file name with transformed_ prefix
        output_filename = input_filename
        if not output_filename.endswith(".parquet"):
            output_filename = f"{output_filename}.parquet"
        
        # Ensure data directory exists
        self.data_dir.mkdir(exist_ok=True)
        
        # Add progress tracking to script
        if progress_callback:
            script = self._add_progress_tracking(script, progress_callback)
        
        # Log execution details
        logger.info(f"Starting transformation execution for job {job_id}")
        logger.info(f"Input file: {input_file}")
        logger.info(f"Output will be saved as: {output_filename}")
        
        # Execute script
        result = await self.execute_script(
            script=script,
            input_file_path=input_file,
            output_file_path=output_filename,
            timeout=600  # 10 minutes for transformations
        )
        
        # Add output file info if successful
        if result.get("success"):
            # Store full path for internal use
            full_output_path = str(self.data_dir / output_filename)
            # Store relative path for database
            result["output_file_path"] = output_filename
            result["output_file_id"] = output_filename.replace(".parquet", "")
            result["full_output_path"] = full_output_path
            result["source_file"] = input_file
            
            # Verify file exists
            if not Path(full_output_path).exists():
                logger.warning(f"Expected output file not found at: {full_output_path}")
                # Check temp directory as fallback
                temp_path = self.temp_dir / output_filename
                if temp_path.exists():
                    logger.info(f"Found output file in temp directory, moving to data dir: {temp_path}")
                    # Copy from temp to data dir
                    import shutil
                    shutil.copy2(temp_path, self.data_dir / output_filename)
                    logger.info(f"File moved successfully to: {full_output_path}")
            else:
                logger.info(f"Transformation output saved to: {full_output_path}")
        else:
            logger.error(f"Transformation failed for job {job_id}: {result.get('error', 'Unknown error')}")
            if result.get("messages"):
                logger.info(f"Execution messages: {result.get('messages')}")
        
        return result
    
    def _add_progress_tracking(self, script: str, callback) -> str:
        """Add progress tracking calls to script"""
        # This is a simplified version - in production, you'd parse the AST
        # and inject progress calls at appropriate points
        
        progress_code = '''
# Progress tracking
import requests
def update_progress(progress, message=""):
    try:
        # Update job progress via callback
        pass  # Callback will be injected
    except:
        pass
'''
        return progress_code + "\n" + script
