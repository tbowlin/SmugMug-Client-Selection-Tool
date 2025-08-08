"""
Configuration module for SmugMug Client Selection Tool

Handles loading and parsing of environment variables and configuration.
"""

import os
from dotenv import load_dotenv


def load_credentials():
    """Load SmugMug API credentials from .env file"""
    
    # Load .env file from project root
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    load_dotenv(env_path)
    
    # Get required credentials
    credentials = {
        'consumer_key': os.getenv('SMUGMUG_CONSUMER_KEY'),
        'consumer_secret': os.getenv('SMUGMUG_CONSUMER_SECRET'),
        'oauth_token': os.getenv('SMUGMUG_OAUTH_TOKEN'),
        'oauth_secret': os.getenv('SMUGMUG_OAUTH_SECRET')
    }
    
    # Validate all credentials are present
    missing_creds = [key for key, value in credentials.items() if not value]
    if missing_creds:
        raise ValueError(f"Missing required credentials: {', '.join(missing_creds)}")
    
    return credentials


def get_project_root():
    """Get the project root directory"""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_output_directory():
    """Get the output directory path"""
    return os.path.join(get_project_root(), 'output')
