
import openai
from openai import OpenAI
import sys
from dotenv import load_dotenv

load_dotenv()

print(f"OpenAI Version: {openai.__version__}")
print(f"OpenAI File: {openai.__file__}")

try:
    client = OpenAI()
    print("Client created")
    print(f"Client beta: {client.beta}")
    print("Attributes of client.beta:")
    print(dir(client.beta))
    
    if hasattr(client.beta, 'vector_stores'):
        print("Vectors stores found on client.beta")
    else:
        print("Vector stores NOT found on client.beta")

    print("\nAttributes of client:")
    print(dir(client))
    if hasattr(client, 'vector_stores'):
        print("Vector stores found on client (stable)")
except Exception as e:
    print(f"Error: {e}")
