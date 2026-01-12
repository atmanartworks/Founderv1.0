from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

print("OpenAI Version:", client.__module__) # Proxied
import openai
print("Real Version:", openai.__version__)

print("Client Beta dir:", dir(client.beta))

try:
    print("Vector Stores in beta:", client.beta.vector_stores)
except Exception as e:
    print("Error accessing client.beta.vector_stores:", e)
    
try:
    print("Vector Stores in root:", client.vector_stores)
except Exception as e:
    print("Error accessing client.vector_stores:", e)
