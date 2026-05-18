import modal
import json
import threading
import time
import uuid
from typing import Dict, Any

# Import the Modal app and image from app.py
from .app import image
from .session import volume_name, session_base_dir

# FIX: Create volume at module level to avoid race conditions
_volume = modal.Volume.from_name(volume_name(), create_if_missing=True)


class SandboxExecutor:
    """
    Manages per-session Modal Sandboxes with persistent state.
    
    Args:
        session_id (str): The ID of the session.
        env (dict[str, str]): The environment variables to pass to the sandbox.
    """

    def __init__(self, session_id: str, env: dict[str, str] | None = None):

        self.session_id = session_id
        self.env = env or {}
        # Ensure unbuffered I/O inside sandbox (critical for CI/CD environments)
        self.env.setdefault("PYTHONUNBUFFERED", "1")
        
        print(f"[EXECUTOR] Initializing for session {session_id}")
        
        # Use module-level volume to avoid race conditions
        print("[EXECUTOR] Using module-level volume...")
        self.volume = _volume
        base_dir = session_base_dir(session_id)
        
        # Only load AWS secrets if S3 upload is not disabled
        secrets = []
        if self.env.get("S3_DISABLE_UPLOAD") != "1":
            secrets.append(modal.Secret.from_name("aws-credentials-IAM"))
            secrets.append(modal.Secret.from_name("modal-token-id"))
            secrets.append(modal.Secret.from_name("modal-token-secret"))
        
        # Important: fixed sandbox creation by hydrating the Modal App inline (required outside Modal containers).
        print("[EXECUTOR] Looking up app...")
        hydrated_app = modal.App.lookup("urbia", create_if_missing=True)
        
        print(f"[EXECUTOR] Creating sandbox (image: {image})...")
        self.sandbox = modal.Sandbox.create(
            app=hydrated_app,
            image=image,
            timeout=60 * 60 * 2,  # 2 hours session timeout
            idle_timeout=60 * 20,  # 20 min idle timeout (increased for long LLM reasoning)
            volumes={"/workspace": self.volume},  # link it to above volume
            workdir=base_dir,  # NEW: per session cwd
            secrets=secrets,  # AWS creds for S3 uploads (optional)
        )
        print(f"[EXECUTOR] Sandbox created: {self.sandbox.object_id}")

        # ensure per-session dir exists before starting the driver
        print("[EXECUTOR] Creating base dir...")
        self.sandbox.exec("mkdir", "-p", base_dir).wait()

        # Start driver with optional environment variables
        print("[EXECUTOR] Starting driver process...")
        self.process = self.sandbox.exec(
            "python",
            "-u",  # Force unbuffered output to prevent hangs in CI
            "/root/driver.py",
            bufsize=0,  # CRITICAL: bufsize=0 for unbuffered I/O
            workdir=base_dir,  # Set working directory for driver process
            env=self.env,  # Pass custom env vars to driver process
        )
        print("[EXECUTOR] Driver started.")
        
        # CRITICAL: Create stdout iterator ONCE and reuse it for all reads
        # Creating a new iterator on each execute() call breaks the state
        self.stdout_reader = iter(self.process.stdout)
        self._execute_lock = threading.Lock()
        print("[EXECUTOR] Stdout iterator created.")

    def execute(self, code: str, timeout: int = 120) -> Dict[str, Any]:
        """Execute code and return results.

        Args:
            code (str): The code to execute.
            timeout (int): The timeout for the execution.

        Returns:
            Dict[str, Any]: The result of the execution.
                - stdout (str): The standard output of the execution.
                - stderr (str): The standard error of the execution.
                - artifacts (list): The artifacts of the execution.
                - error (str): The error message if the execution fails.

        NOTE: The driver handles all artifact scanning and S3 upload, so we just need to send the code and return the response.
        """
        # FIX: Check if process is still alive before trying to write
        # Use poll() instead of returncode to avoid "wait() not called" error
        returncode = self.process.poll()
        if returncode is not None:
            return {
                "error": f"Process died with code {returncode}",
                "stdout": "",
                "stderr": "Driver process terminated unexpectedly. Check logs.",
                "artifacts": [],
            }

        try:
            print(f"[EXECUTOR] Executing code (len={len(code)})...")
            request_id = uuid.uuid4().hex
            command = json.dumps({"request_id": request_id, "code": code})
            command_with_newline = command + "\n"

            with self._execute_lock:
                # Write in chunks to avoid buffer overflow for large datasets
                chunk_size = 8192  # 8KB chunks - safe size for Modal's buffer
                print(f"[EXECUTOR] Writing {len(command_with_newline)} bytes to stdin...")
                for i in range(0, len(command_with_newline), chunk_size):
                    chunk = command_with_newline[i : i + chunk_size]
                    self.process.stdin.write(chunk)
                    self.process.stdin.drain()  # Flush after each chunk to prevent buffer overflow

                print("[EXECUTOR] Waiting for response from stdout...")
                
                # FIX: Add retry loop with debug logging for empty responses
                max_retries = 10
                result_line = None
                for attempt in range(max_retries):
                    result_line = next(self.stdout_reader, None)
                    
                    # Debug: log what we received
                    if result_line is None:
                        print(f"[EXECUTOR] Attempt {attempt + 1}/{max_retries}: Got None from stdout")
                    elif not result_line.strip():
                        print(f"[EXECUTOR] Attempt {attempt + 1}/{max_retries}: Got empty string from stdout")
                    else:
                        print(f"[EXECUTOR] Attempt {attempt + 1}/{max_retries}: Got response ({len(result_line)} bytes)")
                        break  # Got valid response
                    
                    # Check if process died
                    poll_result = self.process.poll()
                    if poll_result is not None:
                        print(f"[EXECUTOR] Process died with code {poll_result} during read")
                        break
                    
                    # Wait before retry with exponential backoff
                    time.sleep(0.1 * (attempt + 1))
                else:
                    # Exhausted all retries
                    print(f"[EXECUTOR] WARNING: All {max_retries} retries exhausted")
                    # Try one more time to get any available data
                    try:
                        remaining = next(self.stdout_reader, None)
                        print(f"[EXECUTOR] Final read attempt: {repr(remaining)[:100] if remaining else 'None'}")
                        if remaining and remaining.strip():
                            result_line = remaining
                    except Exception as e:
                        print(f"[EXECUTOR] Final read error: {e}")

            # Check if we got a valid response
            if not result_line or not result_line.strip():
                # Try to read stderr to see why the driver terminated
                print("[EXECUTOR] Stream closed or empty, reading stderr...")
                stderr_lines = []
                try:
                    # Read all available stderr lines (non-blocking)
                    for line in self.process.stderr:
                        stderr_lines.append(line)
                        if len(stderr_lines) >= 50:  # Limit to prevent hanging
                            break
                except Exception:
                    pass
                
                stderr_output = "".join(stderr_lines) if stderr_lines else "No stderr output captured"
                print(f"[EXECUTOR] Stderr captured: {stderr_output}")
                
                # Check if process is still running
                try:
                    returncode = self.process.returncode
                    process_status = f"Process returncode: {returncode}"
                except Exception:
                    process_status = "Process status unknown"
                
                return {
                    "stdout": "",
                    "stderr": f"Driver process terminated unexpectedly.\n{process_status}\nDriver stderr:\n{stderr_output}",
                    "artifacts": [],
                }

            # DEBUG: Log what we're about to parse
            print(f"[EXECUTOR] About to parse JSON from: {repr(result_line.strip()[:200])}")
            result = json.loads(result_line.strip())
            received_id = result.get("request_id")
            print(f"[EXECUTOR] Successfully parsed JSON, request_id: {received_id}")

            if received_id != request_id:
                # The response belongs to a different (likely stale) request.
                # Drain up to a few lines looking for ours before giving up.
                print(
                    f"[EXECUTOR] request_id mismatch: expected={request_id}, "
                    f"got={received_id}. Draining stdout..."
                )
                for _drain in range(10):
                    extra_line = next(self.stdout_reader, None)
                    if not extra_line:
                        break
                    try:
                        extra = json.loads(extra_line.strip())
                    except json.JSONDecodeError:
                        continue
                    if extra.get("request_id") == request_id:
                        print(f"[EXECUTOR] Found matching response after draining {_drain + 1} line(s).")
                        result = extra
                        break
                else:
                    # Exhausted retries — surface a helpful diagnostic
                    hint = (
                        "This usually means the driver.py inside the Modal image is "
                        "stale (missing request_id support). Rebuild the image by "
                        "restarting the process or running `modal app stop urbia` "
                        "and retrying."
                    )
                    return {
                        "stdout": "",
                        "stderr": (
                            f"Mismatched sandbox response: expected request_id "
                            f"{request_id!r}, got {received_id!r}. {hint}"
                        ),
                        "artifacts": [],
                    }

            # Driver already handled artifacts, just return result
            return result

        except json.JSONDecodeError as e:
            # DEBUG: Log the raw response that failed to parse
            print(f"[EXECUTOR] JSONDecodeError: {e}")
            print(f"[EXECUTOR] Failed to parse: {repr(result_line) if result_line else 'None'}")
            return {
                "stdout": "",
                "stderr": f"Invalid JSON response from driver: {e}. Raw response: {repr(result_line) if result_line else 'None'}",
                "artifacts": [],
            }
        except Exception as e:
            print(f"[EXECUTOR] Exception during execution: {e}")
            return {
                "stdout": "",
                "stderr": f"Execution failed: {str(e)}",
                "artifacts": [],
            }

    def terminate(self):
        """Clean up sandbox and persist volume."""
        try:
            # Signal EOF to driver instead of closing
            self.process.stdin.write_eof()
            self.process.stdin.drain()  # Ensure EOF is sent

            # Wait for process to finish gracefully
            self.process.wait()

        except Exception as e:
            print(f"Error during graceful termination: {e}")

        finally:
            # Always terminate sandbox
            try:
                self.sandbox.terminate()
                self.sandbox.wait(raise_on_termination=False)
            except Exception as e:
                print(f"Error terminating sandbox: {e}")
