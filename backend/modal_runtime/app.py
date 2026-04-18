import modal
import os
import hashlib

# Get the directory where this file is located
_modal_runtime_dir = os.path.dirname(os.path.abspath(__file__))

# Compute a content hash of driver.py so Modal detects changes and rebuilds
# the image even when only the driver logic changes.
_driver_path = os.path.join(_modal_runtime_dir, "driver.py")
with open(_driver_path, "rb") as _f:
    _driver_hash = hashlib.sha256(_f.read()).hexdigest()[:12]

# Define Modal image with all data science dependencies
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install_from_requirements(os.path.join(_modal_runtime_dir, "requirements.txt"))
    # Force cache-bust when driver.py content changes
    .env({"DRIVER_HASH": _driver_hash})
    .add_local_file(_driver_path, "/root/driver.py")
)

# Create Modal app
app = modal.App("urbia", image=image)
