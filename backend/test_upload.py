#!/usr/bin/env python3
"""
Test script to upload sample document for debugging.
This requires a valid Supabase auth token.
"""
import asyncio
import aiohttp
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

API_URL = "http://localhost:8000/api/v1"
SAMPLE_DOC = "../sample/doc.pdf"

async def upload_document(token: str):
    """Upload the sample document using the provided token."""
    if not os.path.exists(SAMPLE_DOC):
        print(f"Error: Sample document not found at {SAMPLE_DOC}")
        return
    
    with open(SAMPLE_DOC, 'rb') as f:
        files = {'file': ('doc.pdf', f, 'application/pdf')}
        headers = {'Authorization': f'Bearer {token}'}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API_URL}/documents/upload",
                headers=headers,
                data=files
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"✓ Upload successful!")
                    print(f"  Document ID: {result.get('id')}")
                    print(f"  Status: {result.get('status')}")
                    print(f"  Message: {result.get('message')}")
                    print(f"\nNow check the backend logs to see processing status...")
                else:
                    error = await response.text()
                    print(f"✗ Upload failed: {response.status}")
                    print(f"  Error: {error}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_upload.py <supabase_auth_token>")
        print("\nTo get a token:")
        print("1. Log in through the frontend")
        print("2. Check localStorage.getItem('supabase_token') in browser console")
        print("3. Copy the token and run: python test_upload.py <token>")
        sys.exit(1)
    
    token = sys.argv[1]
    asyncio.run(upload_document(token))

