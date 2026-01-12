import os
import sys
from openai import OpenAI
from dotenv import load_dotenv

# Load env from root
load_dotenv(".env")

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("Error: OPENAI_API_KEY not found in .env")
    sys.exit(1)

client = OpenAI(api_key=api_key)

def test_upload():
    print(f"Testing OpenAI File Upload with key: {api_key[:10]}...")
    
    # Create dummy file
    filename = "test_upload.txt"
    with open(filename, "w") as f:
        f.write("This is a test file for OpenAI upload.")
        
    try:
        print("Uploading file...")
        with open(filename, "rb") as f:
            file_obj = client.files.create(
                file=f,
                purpose="assistants"
            )
        print(f"✅ Success! File ID: {file_obj.id}")
        return file_obj.id
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        return None
    finally:
        if os.path.exists(filename):
            os.remove(filename)

if __name__ == "__main__":
    test_upload()
