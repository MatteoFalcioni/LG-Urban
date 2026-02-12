# Modal Runtime

In this folder you can find the implementation of the core funcionality of UrbIA: its data analysis capabilities. 

We assume that the ability to execute python code with context knowledge and complex reasoning can give rise to high data-analysis capabilities; therefore we give the agent the possibility to write and run Python code **in a sandbox environment**. The latter is managed by *Modal*. 

## Implementation Details

Following [Modal's documentation](https://modal.com/docs) we first create an **app** in [app.py](./app.py)

```python
app = modal.App("lg-urban-executor")
```

and a **driver** in [driver.py](./driver.py). 

**CRUCIAL**: you need to deploy these objects into the cloud with 

```bash

modal deploy backend/modal_runtime/app.py

```

The purpose of this driver is to be always running while the sandbox exist, in order to keep it warm, and to redirect code input with stdin/stdout: it can do this since the driver is running *inside the sandbox*.

Furthermore, it also: 
- mantains the sandbox stateful by updating the `globals` dictionary with the local variables produced at each run;
- scans the work directory for produced artifacts and uploads them to S3 directly from inside the sandbox using `boto3`.

S3 specifics:
- The bucket name is read from the `S3_BUCKET` env var inside the sandbox.
- AWS credentials must be available in the sandbox (Modal Secret or env vars).
- Uploads use content-addressed keys: `output/artifacts/<sha256[:2]>/<sha256[2:4]>/<sha256>`.

We put everything together inside the [**SandboxExecutor**](./executor.py) class: at inizialition, it creates the sandbox with a mounted volume for persistence of the workspace during the run, and starts the driver. 

It only has 2 methods: 

- `execute` to execute a given code (through the driver);
- `terminate` to terminate the sandbox istance at session end;

## Important Notes

There is an important difference between using `App.lookup` or just `App` in `Modal`. 

### `app = modal.App("name")`
Creates/defines an app with functions attached to it.

- Use this in your source code where you define functions with @app.function()
- The app object has your functions registered on it

### `app = modal.App.lookup("name")`

Finds an already-deployed app by name.

Use this to call functions from a deployed app

- Returns an empty app object (no functions attached)
- You then use modal.Function.from_name() to get the deployed functions

## Tests

Inside the [tests/](./tests/) folder we wrote basic tests to check the implementation:

- `test_driver_artifacts.py`: unit tests for the `scan_and_upload_artifacts` function in the driver, using a `FakeS3Client`.
  - Verifies upload and metadata (content-addressed keys, url, mime type, size)
  - Verifies idempotency/deduplication on a second scan

- `test_driver_e2e.py`: a lightweight end-to-end test that runs `driver.py` in a subprocess and communicates via stdin/stdout.
  - Verifies persistent Python state with `exec(code, globals_dict)` (example: define `x=41` then `print(x+1)`)
  - Uses a temporary `ARTIFACTS_DIR` to avoid uploading to S3 during the test

- `test_code_exec.py`: tests the full `SandboxExecutor` class (instantiation, execution, and termination).



