#!/usr/bin/env python3
"""
Simple test script to verify Gemini API is working
"""
import os
from google import genai
from google.genai import types

# Hardcoded API key for testing
api_key = "AIzaSyBefE0c06h-bT6a9sHfYhHdskorzNZxMes"

print("=" * 60)
print("Testing Gemini 2.5 Flash API")
print("=" * 60)

# Initialize client
print("\n1. Initializing Gemini client...")
try:
    client = genai.Client(api_key=api_key)
    print("✓ Client initialized successfully")
except Exception as e:
    print(f"✗ Failed to initialize client: {e}")
    exit(1)

# Test simple content generation
print("\n2. Testing simple content generation...")
try:
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents="What is 2 + 2? Answer in one sentence."
    )

    print("✓ API call successful!")
    print(f"\nResponse: {response.text}")
except Exception as e:
    print(f"✗ API call failed: {e}")
    exit(1)

# Test JSON response
print("\n3. Testing JSON response...")
try:
    prompt = """Return a JSON object with these fields:
    - name: "Test"
    - value: 42
    - status: "working"

    Return ONLY the JSON, no markdown formatting."""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    print("✓ JSON test successful!")
    print(f"\nResponse: {response.text}")
except Exception as e:
    print(f"✗ JSON test failed: {e}")
    exit(1)

# Test metadata extraction format
print("\n4. Testing metadata extraction format...")
try:
    test_text = """
    Title: A Study on Machine Learning
    Authors: John Doe, Jane Smith
    Year: 2024
    Journal: AI Research Quarterly
    DOI: 10.1234/example

    Abstract: This paper presents a comprehensive study on machine learning techniques.
    """

    prompt = f"""Extract bibliographic information from this text and return as JSON:

{test_text}

Return ONLY a JSON object with these fields: title, authors (as array), year, journal, doi, abstract"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    print("✓ Metadata extraction test successful!")
    print(f"\nResponse: {response.text}")
except Exception as e:
    print(f"✗ Metadata extraction test failed: {e}")
    exit(1)

print("\n" + "=" * 60)
print("All tests passed! ✓")
print("=" * 60)
