#!/usr/bin/env python3
"""
SmugMug Client Selection Tool

This script identifies images in a SmugMug gallery that have comments,
allowing photographers to generate lists of client-selected images for further processing.
"""

import os
import sys
import json
import requests
from datetime import datetime
from urllib.parse import urlparse, parse_qs
import time

# Add the parent directory to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import load_credentials


class SmugMugClient:
    def __init__(self):
        self.credentials = load_credentials()
        self.base_url = "https://api.smugmug.com/api/v2"
        self.session = requests.Session()
        self.setup_oauth_session()
        
    def setup_oauth_session(self):
        """Set up OAuth 1.0a session with SmugMug credentials"""
        from requests_oauthlib import OAuth1
        
        auth = OAuth1(
            self.credentials['consumer_key'],
            client_secret=self.credentials['consumer_secret'],
            resource_owner_key=self.credentials['oauth_token'],
            resource_owner_secret=self.credentials['oauth_secret']
        )
        self.session.auth = auth
        
    def make_request(self, endpoint, params=None):
        """Make authenticated request to SmugMug API with error handling"""
        url = f"{self.base_url}{endpoint}"
        
        # Add proper headers for SmugMug API
        headers = {
            'Accept': 'application/json',
            'User-Agent': 'SmugMug-Client-Selection-Tool/1.0'
        }
        
        try:
            response = self.session.get(url, params=params, headers=headers)
            response.raise_for_status()
            
            # Rate limiting - be respectful
            time.sleep(0.1)
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"Error making request to {endpoint}: {e}")
            return None
            
    def get_user_albums(self):
        """Get all albums for the authenticated user"""
        print("Fetching your SmugMug albums...")
        
        # First get user info
        user_info = self.make_request("/user/triggbowlin")
        if not user_info:
            print("Failed to get user information")
            return []
            
        # Get the user's folder structure
        response = self.make_request("/user/triggbowlin!albums")
        if not response or 'Response' not in response:
            print("Failed to fetch albums")
            return []
            
        albums = response['Response']['Album']
        return albums
        
    def get_album_images(self, album_key):
        """Get all images in a specific album"""
        print(f"Fetching images from album...")
        
        images = []
        start = 1
        count = 100  # Get images in batches
        
        while True:
            params = {'start': start, 'count': count}
            response = self.make_request(f"/album/{album_key}!images", params)
            
            if not response or 'Response' not in response:
                break
                
            batch_images = response['Response'].get('AlbumImage', [])
            if not batch_images:
                break
                
            images.extend(batch_images)
            
            # Check if we got all images
            if len(batch_images) < count:
                break
                
            start += count
            
        print(f"Found {len(images)} images in album")
        return images
        
    def get_image_comments(self, image_key, serial=0):
        """Check if an image has comments"""
        # SmugMug requires serial number format: imagekey-serial
        full_image_key = f"{image_key}-{serial}"
        response = self.make_request(f"/image/{full_image_key}!comments")
        
        if not response or 'Response' not in response:
            return []
            
        comments = response['Response'].get('Comment', [])
        return comments
        
    def get_image_details(self, image_key, serial=0):
        """Get detailed information about an image including filename"""
        # SmugMug requires serial number format: imagekey-serial
        full_image_key = f"{image_key}-{serial}"
        response = self.make_request(f"/image/{full_image_key}")
        
        if not response or 'Response' not in response:
            return None
            
        return response['Response']['Image']
        
    def process_album_for_comments(self, album_key, album_name):
        """Process an entire album and find images with comments"""
        print(f"\nProcessing album: {album_name}")
        print("=" * 50)
        
        # Get all images in the album
        album_images = self.get_album_images(album_key)
        
        if not album_images:
            print("No images found in this album")
            return []
            
        commented_images = []
        
        for i, album_image in enumerate(album_images):
            image_key = album_image['ImageKey']
            
            # Show progress
            print(f"Checking image {i+1}/{len(album_images)}...", end='\r')
            
            # Check for comments
            comments = self.get_image_comments(image_key)
            
            if comments:
                # Get image details including filename
                image_details = self.get_image_details(image_key)
                
                if image_details:
                    filename = image_details.get('FileName', f'Image_{image_key}')
                    comment_count = len(comments)
                    
                    commented_images.append({
                        'filename': filename,
                        'image_key': image_key,
                        'comment_count': comment_count,
                        'comments': comments
                    })
        
        print(f"\nFound {len(commented_images)} images with comments")
        return commented_images
        
    def save_results(self, commented_images, album_name):
        """Save the results to a text file"""
        if not commented_images:
            print("No commented images to save")
            return
            
        # Create output directory if it doesn't exist
        output_dir = "/Users/trigg/Development/SmugMug-Client-Selection-Tool/output"
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_album_name = "".join(c for c in album_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        filename = f"commented_images_{safe_album_name}_{timestamp}.txt"
        filepath = os.path.join(output_dir, filename)
        
        # Write the results
        with open(filepath, 'w') as f:
            f.write(f"Images with Comments - {album_name}\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 50 + "\n\n")
            
            for item in commented_images:
                f.write(f"{item['filename']}\n")
                
            f.write(f"\nTotal: {len(commented_images)} images with comments\n")
            
            # Optional: include comment details
            f.write("\n" + "=" * 50 + "\n")
            f.write("COMMENT DETAILS:\n")
            f.write("=" * 50 + "\n\n")
            
            for item in commented_images:
                f.write(f"File: {item['filename']}\n")
                f.write(f"Comments ({item['comment_count']}):\n")
                
                for comment in item['comments']:
                    author = comment.get('Name', 'Anonymous')
                    text = comment.get('Text', '')
                    date = comment.get('Date', '')
                    f.write(f"  - {author}: {text}\n")
                    if date:
                        f.write(f"    {date}\n")
                        
                f.write("\n")
        
        print(f"\nResults saved to: {filepath}")
        return filepath


def main():
    """Main function to run the SmugMug Client Selection Tool"""
    print("SmugMug Client Selection Tool")
    print("=" * 40)
    
    try:
        client = SmugMugClient()
        
        # Get user's albums
        albums = client.get_user_albums()
        
        if not albums:
            print("No albums found or unable to fetch albums")
            return
            
        # Display albums for user selection
        print(f"\nFound {len(albums)} albums:")
        print("-" * 40)
        
        for i, album in enumerate(albums):
            album_name = album.get('Name', 'Untitled')
            image_count = album.get('ImageCount', 0)
            print(f"{i+1:2d}. {album_name} ({image_count} images)")
        
        # Get user selection
        while True:
            try:
                choice = input(f"\nSelect album to process (1-{len(albums)}): ")
                album_index = int(choice) - 1
                
                if 0 <= album_index < len(albums):
                    break
                else:
                    print(f"Please enter a number between 1 and {len(albums)}")
                    
            except ValueError:
                print("Please enter a valid number")
        
        selected_album = albums[album_index]
        album_key = selected_album['AlbumKey']
        album_name = selected_album.get('Name', 'Untitled')
        
        # Process the selected album
        commented_images = client.process_album_for_comments(album_key, album_name)
        
        if commented_images:
            # Save results
            output_file = client.save_results(commented_images, album_name)
            
            # Summary
            print(f"\nSUMMARY:")
            print(f"Album: {album_name}")
            print(f"Images with comments: {len(commented_images)}")
            print(f"Output file: {output_file}")
            
            # Show first few filenames as preview
            print(f"\nPreview of commented image filenames:")
            for i, item in enumerate(commented_images[:10]):
                print(f"  {item['filename']}")
                
            if len(commented_images) > 10:
                print(f"  ... and {len(commented_images) - 10} more")
        else:
            print(f"\nNo images with comments found in album: {album_name}")
            
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
    except Exception as e:
        print(f"\nError: {e}")
        

if __name__ == "__main__":
    main()
