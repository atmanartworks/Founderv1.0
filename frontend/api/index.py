import sys
import os

# Add the backend directory to Python path for serverless environment
# This allows 'from app.*' imports to work correctly
# Backend is now in the same directory as this file (api/backend/)
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_path = os.path.abspath(os.path.join(current_dir, 'backend'))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# Verify critical dependencies are available
try:
    import pydantic_settings
except ImportError:
    raise ImportError(
        "pydantic_settings module not found. "
        "Please ensure pydantic-settings>=2.0.0 is installed. "
        "Check that api/requirements.txt contains 'pydantic-settings>=2.0.0'"
    )

# Now we can import using the app module structure
try:
    from app.main import app
except Exception as e:
    # Provide better error message for debugging
    import traceback
    error_msg = f"Failed to import app.main: {str(e)}\n{traceback.format_exc()}"
    raise ImportError(error_msg)

# Vercel expects a variable named 'app' or 'handler'
# We import the FastAPI app instance from our backend
