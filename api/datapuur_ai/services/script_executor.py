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
                           timeout: int = 300,
                           job_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute a Python script safely with timeout"""
        
        # Generate unique execution ID
        exec_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        context_id = f"job_{job_id}" if job_id else exec_id
        
        logger.info(f"[EXEC {context_id}] Starting script execution with input_file={input_file_path}, output_file={output_file_path}")
        
        # Validate input file path exists
        input_path = Path(input_file_path)
        if not input_path.is_absolute():
            input_path = (self.data_dir / input_file_path).absolute()
            logger.info(f"[EXEC {context_id}] Converted input path to absolute: {input_path}")
        
        if not input_path.exists():
            error_msg = f"Input file not found at path: {input_path}"
            logger.error(f"[EXEC {context_id}] {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "execution_id": exec_id
            }
        else:
            logger.info(f"[EXEC {context_id}] Input file exists: {input_path} (size: {input_path.stat().st_size} bytes)")
        
        # Ensure output path is absolute if provided
        output_path = None
        if output_file_path:
            output_path = Path(output_file_path)
            if not output_path.is_absolute():
                output_path = (self.data_dir / output_file_path).absolute()
                logger.info(f"[EXEC {context_id}] Converted output path to absolute: {output_path}")
            
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            logger.info(f"[EXEC {context_id}] Ensured output directory exists: {output_path.parent}")
        
        # Create temporary script file
        script_path = self.temp_dir / f"script_{exec_id}.py"
        
        # Prepare the script with safety wrapper
        try:
            logger.info(f"[EXEC {context_id}] Wrapping script (length: {len(script)} chars)")
            wrapped_script = self._wrap_script(script, str(input_path), str(output_path) if output_path else None)
            logger.info(f"[EXEC {context_id}] Successfully wrapped script (wrapped length: {len(wrapped_script)} chars)")
        except Exception as wrap_error:
            error_msg = f"Failed to wrap script: {str(wrap_error)}"
            logger.error(f"[EXEC {context_id}] {error_msg}")
            logger.error(f"[EXEC {context_id}] Wrap error traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "error": error_msg,
                "traceback": traceback.format_exc(),
                "execution_id": exec_id
            }
        
        try:
            # Write script to file
            logger.info(f"[EXEC {context_id}] Writing wrapped script to {script_path}")
            script_path.write_text(wrapped_script)
            logger.info(f"[EXEC {context_id}] Script written successfully")
            
            # Execute in subprocess with timeout
            logger.info(f"[EXEC {context_id}] Starting subprocess execution with timeout {timeout}s")
            result = await self._run_script_subprocess(script_path, timeout)
            
            # Add input/output paths to result
            result["input_file_path"] = str(input_path)
            if output_path:
                result["output_file_path"] = str(output_path)
                
                # Check if output file was created
                if output_path.exists():
                    result["output_file_exists"] = True
                    result["output_file_size"] = output_path.stat().st_size
                    logger.info(f"[EXEC {context_id}] Output file created successfully: {output_path} (size: {output_path.stat().st_size} bytes)")
                else:
                    result["output_file_exists"] = False
                    logger.warning(f"[EXEC {context_id}] Output file was not created at expected location: {output_path}")
            
            # Add context ID to result
            result["context_id"] = context_id
            
            # Log execution result
            success_status = "SUCCESS" if result.get("success") else "FAILED"
            logger.info(f"[EXEC {context_id}] Script execution {success_status}")
            if not result.get("success") and result.get("error"):
                logger.error(f"[EXEC {context_id}] Execution error: {result.get('error')}")
            
            return result
            
        except Exception as e:
            error_traceback = traceback.format_exc()
            logger.error(f"[EXEC {context_id}] Script execution error: {str(e)}")
            logger.error(f"[EXEC {context_id}] Error traceback: {error_traceback}")
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
        
        # Generate unique execution ID for this wrapping operation
        wrap_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        logger.info(f"[WRAP {wrap_id}] Wrapping script with input_file_path={input_file_path}, output_file_path={output_file_path}")
        
        # Resolve input file path to absolute path
        input_path = Path(input_file_path)
        if not input_path.is_absolute():
            # Try different locations to find the file
            possible_paths = [
                Path.cwd() / input_file_path,
                self.data_dir / input_file_path,
                self.temp_dir / input_file_path
            ]
            
            # Find first existing path
            for path in possible_paths:
                if path.exists():
                    input_path = path.absolute()
                    logger.info(f"[WRAP {wrap_id}] Found input file at: {input_path}")
                    break
            else:
                # Default to data_dir if not found
                input_path = (self.data_dir / input_file_path).absolute()
                logger.info(f"[WRAP {wrap_id}] Using default data_dir path for input: {input_path}")
        
        # Resolve output file path to absolute path
        output_path = None
        if output_file_path:
            output_path = Path(output_file_path)
            if not output_path.is_absolute():
                # Default to data_dir for output
                output_path = (self.data_dir / output_file_path).absolute()
                logger.info(f"[WRAP {wrap_id}] Using absolute path for output: {output_path}")
        
        # Define input and output settings with absolute paths
        input_setting = f"INPUT_FILE = Path(r\"{input_path}\")"  # Use raw string to handle Windows paths
        output_setting = f"OUTPUT_FILE = Path(r\"{output_path}\")" if output_path else 'OUTPUT_FILE = None'
        
        # Build wrapper script with absolute paths
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
DATA_DIR = Path(r"{self.data_dir}")
{input_setting}

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
        """Run script in subprocess with timeout and enhanced monitoring"""
        
        # Generate unique execution ID for this subprocess run
        exec_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        cmd = [sys.executable, str(script_path)]
        
        logger.info(f"[EXEC {exec_id}] Running script: {script_path} with Python: {sys.executable}")
        logger.info(f"[EXEC {exec_id}] Script absolute path exists: {script_path.exists()}")
        
        process = None
        start_time = datetime.now()
        
        try:
            # Run subprocess with enhanced error handling
            try:
                logger.info(f"[EXEC {exec_id}] Starting subprocess execution")
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                logger.info(f"[EXEC {exec_id}] Subprocess started with PID: {process.pid}")
            except Exception as proc_error:
                logger.error(f"[EXEC {exec_id}] Failed to create subprocess: {str(proc_error)}")
                return {
                    "success": False,
                    "error": f"Failed to create subprocess: {str(proc_error)}",
                    "traceback": traceback.format_exc()
                }
            
            # Wait for completion with timeout and capture output
            try:
                logger.info(f"[EXEC {exec_id}] Waiting for subprocess completion (timeout: {timeout}s)")
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
                execution_time = (datetime.now() - start_time).total_seconds()
                logger.info(f"[EXEC {exec_id}] Subprocess completed in {execution_time:.2f}s with return code: {process.returncode}")
            except asyncio.TimeoutError:
                logger.error(f"[EXEC {exec_id}] Subprocess execution timed out after {timeout}s")
                
                # Try to terminate the process
                if process and process.returncode is None:
                    try:
                        process.terminate()
                        logger.info(f"[EXEC {exec_id}] Terminated timed out process")
                    except Exception as term_error:
                        logger.error(f"[EXEC {exec_id}] Failed to terminate process: {str(term_error)}")
                
                return {
                    "success": False,
                    "error": f"Script execution timed out after {timeout} seconds",
                    "execution_id": exec_id
                }
            
            # Parse and decode output with explicit error handling
            try:
                output = stdout.decode('utf-8', errors='replace')
                stderr_output = stderr.decode('utf-8', errors='replace') if stderr else ""
            except Exception as decode_error:
                logger.error(f"[EXEC {exec_id}] Failed to decode subprocess output: {str(decode_error)}")
                return {
                    "success": False,
                    "error": f"Failed to decode subprocess output: {str(decode_error)}",
                    "execution_id": exec_id
                }
            
            # Log process results
            if process.returncode != 0:
                logger.warning(f"[EXEC {exec_id}] Script process exited with non-zero return code: {process.returncode}")
            
            if stderr_output:
                logger.warning(f"[EXEC {exec_id}] Script stderr output:\n{stderr_output[:1000]}" + 
                              ("..." if len(stderr_output) > 1000 else ""))
            
            # Extract JSON result with robust parsing
            if "===RESULT_START===" in output and "===RESULT_END===" in output:
                try:
                    start = output.find("===RESULT_START===") + len("===RESULT_START===")
                    end = output.find("===RESULT_END===")
                    result_json = output[start:end].strip()
                    
                    logger.info(f"[EXEC {exec_id}] Found result JSON markers in output")
                    
                    try:
                        result = json.loads(result_json)
                        logger.info(f"[EXEC {exec_id}] Successfully parsed result JSON")
                        
                        # Add execution metadata
                        result["execution_id"] = exec_id
                        result["execution_time_seconds"] = execution_time
                        result["return_code"] = process.returncode
                        
                        # Capture all console output before the result
                        console_output = output[:start].strip()
                        if console_output:
                            if not result.get("messages"):
                                result["messages"] = []
                            result["messages"].insert(0, {
                                "timestamp": datetime.now().isoformat(),
                                "level": "INFO",
                                "message": f"Script console output: {console_output}"
                            })
                            
                        # Add stderr output to messages if present
                        if stderr_output and not result.get("error"):
                            if not result.get("messages"):
                                result["messages"] = []
                            result["messages"].append({
                                "timestamp": datetime.now().isoformat(),
                                "level": "WARNING",
                                "message": f"Script stderr output: {stderr_output}"
                            })
                            
                    except json.JSONDecodeError as e:
                        logger.error(f"[EXEC {exec_id}] Failed to parse script result JSON: {e}")
                        logger.error(f"[EXEC {exec_id}] Raw JSON (first 500 chars): {result_json[:500]}")
                        result = {
                            "success": False,
                            "error": f"Failed to parse script result: {e}",
                            "output": output[:1000] + ("..." if len(output) > 1000 else ""),
                            "execution_id": exec_id,
                            "execution_time_seconds": execution_time,
                            "return_code": process.returncode
                        }
                except Exception as extract_error:
                    logger.error(f"[EXEC {exec_id}] Error extracting result from output: {str(extract_error)}")
                    result = {
                        "success": False,
                        "error": f"Error extracting result from output: {str(extract_error)}",
                        "execution_id": exec_id,
                        "execution_time_seconds": execution_time,
                        "return_code": process.returncode if process else None
                    }
            else:
                # Fallback if no structured output
                logger.warning(f"[EXEC {exec_id}] Script output doesn't contain result markers")
                result = {
                    "success": process.returncode == 0,
                    "output": output[:1000] + ("..." if len(output) > 1000 else ""),
                    "error": stderr_output if stderr_output else None,
                    "execution_id": exec_id,
                    "execution_time_seconds": execution_time,
                    "return_code": process.returncode,
                    "messages": [{
                        "timestamp": datetime.now().isoformat(),
                        "level": "INFO",
                        "message": f"Raw script output: {output[:500]}" + ("..." if len(output) > 500 else "")
                    }] if output else []
                }
            
            return result
            
        except Exception as e:
            # Catch-all for any other exceptions
            error_traceback = traceback.format_exc()
            logger.error(f"[EXEC {exec_id}] Unexpected error in script execution: {str(e)}")
            logger.error(f"[EXEC {exec_id}] Error traceback: {error_traceback}")
            
            # Try to get process info if available
            proc_info = {}
            if process:
                proc_info = {
                    "pid": process.pid,
                    "returncode": process.returncode,
                    "running_time": (datetime.now() - start_time).total_seconds()
                }
            
            return {
                "success": False,
                "error": f"Unexpected error in script execution: {str(e)}",
                "traceback": error_traceback,
                "execution_id": exec_id,
                "process_info": proc_info
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
        """Execute transformation script with progress tracking and enhanced error handling"""
        
        # Create transformation context ID for logging
        transform_id = f"transform_{job_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        logger.info(f"[{transform_id}] Starting transformation execution for job {job_id}")
        
        # Resolve and validate input file path
        try:
            input_path = Path(input_file)
            if not input_path.is_absolute():
                # Convert to absolute path
                input_path = (self.data_dir / input_file).absolute()
                logger.info(f"[{transform_id}] Converted input path to absolute: {input_path}")
            
            # Check if input file exists
            if not input_path.exists():
                error_msg = f"Input file not found: {input_path}"
                logger.error(f"[{transform_id}] {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "job_id": job_id,
                    "transform_id": transform_id
                }
            
            # Log input file details
            file_size = input_path.stat().st_size
            logger.info(f"[{transform_id}] Input file validated: {input_path} (size: {file_size} bytes)")
            input_file = str(input_path)  # Use absolute path for all operations
        except Exception as e:
            error_msg = f"Error resolving input file path: {str(e)}"
            logger.error(f"[{transform_id}] {error_msg}")
            logger.error(f"[{transform_id}] Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "error": error_msg,
                "traceback": traceback.format_exc(),
                "job_id": job_id,
                "transform_id": transform_id
            }
        
        # Generate output filename with transformed_ prefix
        try:
            # Extract just the filename from the input path
            input_filename = input_path.name
            
            # Create output filename with transformed_ prefix if not already present
            if not input_filename.startswith("transformed_"):
                output_filename = f"transformed_{input_filename}"
            else:
                output_filename = input_filename
                
            # Ensure output is parquet format
            if not output_filename.lower().endswith(".parquet"):
                # Strip any existing extension and add .parquet
                base_name = output_filename.rsplit(".", 1)[0] if "." in output_filename else output_filename
                output_filename = f"{base_name}.parquet"
                
            # Create absolute output path
            output_path = (self.data_dir / output_filename).absolute()
            logger.info(f"[{transform_id}] Output will be saved as: {output_path}")
        except Exception as e:
            error_msg = f"Error generating output filename: {str(e)}"
            logger.error(f"[{transform_id}] {error_msg}")
            logger.error(f"[{transform_id}] Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "error": error_msg,
                "traceback": traceback.format_exc(),
                "job_id": job_id,
                "transform_id": transform_id
            }
        
        # Ensure data directory exists
        try:
            self.data_dir.mkdir(exist_ok=True)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            logger.info(f"[{transform_id}] Ensured data directory exists: {self.data_dir}")
        except Exception as e:
            error_msg = f"Error creating data directory: {str(e)}"
            logger.error(f"[{transform_id}] {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "traceback": traceback.format_exc(),
                "job_id": job_id,
                "transform_id": transform_id
            }
        
        # Add progress tracking to script if callback provided
        if progress_callback:
            logger.info(f"[{transform_id}] Adding progress tracking to script")
            script = self._add_progress_tracking(script, progress_callback)
        
        # Execute script with enhanced error handling
        try:
            logger.info(f"[{transform_id}] Executing transformation script (length: {len(script)} chars)")
            result = await self.execute_script(
                script=script,
                input_file_path=str(input_path),  # Use absolute path
                output_file_path=str(output_path),  # Use absolute path
                timeout=600,  # 10 minutes for transformations
                job_id=job_id  # Pass job_id for context
            )
            
            # Add transformation metadata to result
            result["job_id"] = job_id
            result["transform_id"] = transform_id
            result["input_file"] = str(input_path)
            
            # Process result and handle output file
            if result.get("success"):
                logger.info(f"[{transform_id}] Transformation script executed successfully")
                
                # Store full path for internal use
                full_output_path = str(output_path)
                # Store relative path for database (relative to data_dir)
                relative_output_path = output_filename
                
                result["output_file_path"] = relative_output_path
                result["output_file_id"] = output_filename.replace(".parquet", "")
                result["full_output_path"] = full_output_path
                result["source_file"] = str(input_path)
                
                # Verify output file exists and handle potential location issues
                if not output_path.exists():
                    logger.warning(f"[{transform_id}] Expected output file not found at: {output_path}")
                    
                    # Check temp directory as fallback
                    temp_path = self.temp_dir / output_filename
                    if temp_path.exists():
                        logger.info(f"[{transform_id}] Found output file in temp directory, moving to data dir: {temp_path}")
                        try:
                            # Copy from temp to data dir
                            import shutil
                            shutil.copy2(temp_path, output_path)
                            logger.info(f"[{transform_id}] File moved successfully to: {output_path}")
                            
                            # Calculate file size after copy
                            if output_path.exists():
                                file_size = output_path.stat().st_size
                                result["output_file_size"] = file_size
                                logger.info(f"[{transform_id}] Output file size: {file_size} bytes")
                        except Exception as copy_error:
                            logger.error(f"[{transform_id}] Error copying file from temp: {str(copy_error)}")
                            result["copy_error"] = str(copy_error)
                    else:
                        # Look for any file with similar name pattern in temp or data dir
                        logger.warning(f"[{transform_id}] Output file not found in temp directory either")
                        possible_files = list(self.temp_dir.glob(f"*{output_filename}*")) + list(self.data_dir.glob(f"*{output_filename}*"))
                        if possible_files:
                            logger.info(f"[{transform_id}] Found possible output files: {[str(f) for f in possible_files]}")
                            result["possible_output_files"] = [str(f) for f in possible_files]
                else:
                    # Output file exists at expected location
                    file_size = output_path.stat().st_size
                    result["output_file_size"] = file_size
                    logger.info(f"[{transform_id}] Transformation output saved to: {output_path} (size: {file_size} bytes)")
            else:
                # Script execution failed
                logger.error(f"[{transform_id}] Transformation failed: {result.get('error', 'Unknown error')}")
                if result.get("traceback"):
                    logger.error(f"[{transform_id}] Error traceback: {result.get('traceback')}")
                if result.get("messages"):
                    log_messages = result.get("messages")
                    if isinstance(log_messages, list) and len(log_messages) > 0:
                        logger.info(f"[{transform_id}] Execution produced {len(log_messages)} log messages")
                        for i, msg in enumerate(log_messages[:5]):  # Log first 5 messages
                            if isinstance(msg, dict):
                                logger.info(f"[{transform_id}] Log {i+1}: {msg.get('message', str(msg))}")
                            else:
                                logger.info(f"[{transform_id}] Log {i+1}: {str(msg)}")
            
            return result
            
        except Exception as e:
            # Catch any unexpected errors during execution
            error_traceback = traceback.format_exc()
            logger.error(f"[{transform_id}] Unexpected error during transformation: {str(e)}")
            logger.error(f"[{transform_id}] Error traceback: {error_traceback}")
            
            return {
                "success": False,
                "error": f"Unexpected error during transformation: {str(e)}",
                "traceback": error_traceback,
                "job_id": job_id,
                "transform_id": transform_id,
                "input_file": str(input_path)
            }
    
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
