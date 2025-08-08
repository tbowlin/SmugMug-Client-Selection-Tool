#!/usr/bin/env python3
"""
Simple test script to verify SmugMug API connection
"""

import sys
import os

# Add the parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import load_credentials
import requests
from requests_oauthlib import OAuth1


def test_connection():
    """Test connection to SmugMug API"""
    print("Testing SmugMug API connection...")
    
    try:
        # Load credentials
        credentials = load_credentials()
        print("✓ Credentials loaded successfully")
        
        # Set up OAuth
        auth = OAuth1(
            credentials['consumer_key'],
            client_secret=credentials['consumer_secret'],
            resource_owner_key=credentials['oauth_token'],
            resource_owner_secret=credentials['oauth_secret']
        )
        
        # Test API call - try the general user endpoint first with proper headers
        headers = {
            'Accept': 'application/json',
            'User-Agent': 'SmugMug-Client-Selection-Tool/1.0'
        }
        response = requests.get("https://api.smugmug.com/api/v2!authuser", auth=auth, headers=headers)
        
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            try:
                user_data = response.json()
                user_name = user_data['Response']['User']['Name']
                print(f"✓ API connection successful!")
                print(f"  Connected as: {user_name}")
                return True
            except ValueError as json_error:
                print(f"✗ Invalid JSON response: {json_error}")
                print(f"  Raw response: {response.text[:500]}...")
                return False
        else:
            print(f"✗ API connection failed: {response.status_code}")
            print(f"  Response: {response.text[:500]}...")
            return False
            
    except Exception as e:
        print(f"✗ Connection test failed: {e}")
        return False


if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
