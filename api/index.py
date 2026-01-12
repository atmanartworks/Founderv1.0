import sys
import os

# Add the backend directory to Python path for serverless environment
# This allows 'from app.*' imports to work correctly
# Get the absolute path to the backend directory
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_path = os.path.abspath(os.path.join(current_dir, '..', 'backend'))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# Now we can import using the app module structure
from app.main import app

# Vercel expects a variable named 'app' or 'handler'
# We import the FastAPI app instance from our backend
