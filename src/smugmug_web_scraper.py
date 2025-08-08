#!/usr/bin/env python3
"""
SmugMug Web Scraper for Client Selection Tool

This script uses a headless browser to access password-protected SmugMug galleries
and extract comments from images, generating lists of client-selected images.
"""

import asyncio
import os
import sys
from datetime import datetime
from playwright.async_api import async_playwright
import re

# Add the parent directory to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class SmugMugWebScraper:
    def __init__(self, gallery_url, password):
        self.gallery_url = gallery_url
        self.password = password
        self.commented_images = []
        self.output_file = None
        self._setup_output_file()
    
    def _setup_output_file(self, album_name="Dragonhood"):
        """Setup output file for iterative writing"""
        # Create output directory if it doesn't exist
        output_dir = "/Users/trigg/Development/SmugMug-Client-Selection-Tool/output"
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"commented_images_{album_name}_webscrape_{timestamp}.txt"
        self.output_file = os.path.join(output_dir, filename)
        
        # Write header
        with open(self.output_file, 'w') as f:
            f.write(f"Images with Comments - {album_name} (Web Scrape)\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Gallery URL: {self.gallery_url}\n")
            f.write("=" * 50 + "\n")
            f.write("LIVE RESULTS (written as found):\n")
            f.write("=" * 50 + "\n\n")
        
        print(f"Output file initialized: {self.output_file}")
    
    def _append_result_to_file(self, filename, comments, image_index):
        """Append a single result to output file immediately"""
        try:
            with open(self.output_file, 'a') as f:
                f.write(f"{filename}\n")
                f.flush()  # Force write to disk
            print(f"  ✓ Added to output file: {filename}")
        except Exception as e:
            print(f"  ! Error writing to file: {e}")
        
    async def scrape_gallery_comments(self):
        """Main method to scrape comments from SmugMug gallery"""
        print("SmugMug Web Scraper - Client Selection Tool")
        print("=" * 50)
        print(f"Gallery URL: {self.gallery_url}")
        print("Starting browser...")
        
        async with async_playwright() as p:
            # Launch browser (headless=False for debugging, True for production)
            browser = await p.chromium.launch(headless=False)  # Set to True for production
            context = await browser.new_context()
            page = await context.new_page()
            
            try:
                # Navigate to gallery
                print("Navigating to gallery...")
                await page.goto(self.gallery_url, timeout=30000)
                
                # Wait a moment for page to load
                await page.wait_for_timeout(3000)
                
                # Check if password is required
                password_input = await page.query_selector('input[type="password"]')
                if password_input:
                    print("Password required - entering password...")
                    await password_input.fill(self.password)
                    
                    # Look for submit button
                    submit_button = await page.query_selector('button[type="submit"], input[type="submit"], button:has-text("Enter"), button:has-text("Submit")')
                    if submit_button:
                        await submit_button.click()
                    else:
                        # Try pressing Enter
                        await password_input.press('Enter')
                    
                    # Wait for gallery to load
                    await page.wait_for_timeout(3000)
                
                print("Gallery loaded. Scanning for images...")
                
                # Wait for gallery images to load
                await page.wait_for_selector('img, .sm-tile, .sm-gallery-image', timeout=15000)
                
                # Handle lazy loading by scrolling to load all images
                print("Scrolling to lazy-load all images...")
                
                # Scroll down multiple times to trigger lazy loading
                last_count = 0
                scroll_attempts = 0
                max_scroll_attempts = 20
                
                while scroll_attempts < max_scroll_attempts:
                    # Get current image count
                    current_images = await page.query_selector_all('a[href*="/i-"], img[src*="smugmug"]')
                    current_count = len(current_images)
                    
                    print(f"  Scroll attempt {scroll_attempts + 1}: Found {current_count} images")
                    
                    # If no new images loaded, try a few more times then stop
                    if current_count == last_count:
                        if scroll_attempts >= 3:  # Give it 3 more tries
                            print(f"  No new images loaded after {scroll_attempts + 1} attempts")
                            break
                    else:
                        scroll_attempts = 0  # Reset if we found new images
                    
                    last_count = current_count
                    
                    # Scroll down to load more images
                    await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                    await page.wait_for_timeout(2000)
                    scroll_attempts += 1
                
                # Get final image count - use more specific selector to avoid duplicates
                # Try to get unique clickable image elements (prefer links over images)
                link_elements = await page.query_selector_all('a[href*="/i-"]')
                
                # If no links found, try image elements
                if not link_elements:
                    image_elements = await page.query_selector_all('img[src*="smugmug"], .sm-tile img, .sm-gallery-image img')
                else:
                    image_elements = link_elements
                
                # Deduplicate by href/src to get actual unique images
                unique_elements = []
                seen_urls = set()
                
                for element in image_elements:
                    try:
                        if element.evaluate:
                            href = await element.get_attribute('href')
                            if href and '/i-' in href:
                                if href not in seen_urls:
                                    unique_elements.append(element)
                                    seen_urls.add(href)
                            else:
                                src = await element.get_attribute('src')
                                if src and src not in seen_urls:
                                    unique_elements.append(element)
                                    seen_urls.add(src)
                    except:
                        continue
                
                image_elements = unique_elements
                print(f"Total UNIQUE images found: {len(image_elements)} (expected ~268)")
                print(f"Deduplication removed {len(await page.query_selector_all('a[href*=\"/i-\"], img[src*=\"smugmug\"]')) - len(image_elements)} duplicate elements")
                
                if len(image_elements) == 0:
                    print("ERROR: No image elements found. The gallery structure may be different than expected.")
                    # Take a screenshot for debugging
                    await page.screenshot(path="/Users/trigg/Development/SmugMug-Client-Selection-Tool/output/debug_gallery.png")
                    print("Debug screenshot saved to output/debug_gallery.png")
                    return []
                
                # Click first image to enter lightbox mode
                if len(image_elements) > 0:
                    print("Entering lightbox mode with first image...")
                    first_image = image_elements[0]
                    await first_image.click()
                    await page.wait_for_timeout(3000)
                    
                    # Process all images using arrow key navigation
                    for i in range(len(image_elements)):
                        try:
                            print(f"Checking image {i+1}/{len(image_elements)}...")
                            
                            # Look for and click comment button (icon-based, no text)
                            view_comments_button = await page.query_selector('[class*="comment"]')
                            if view_comments_button:
                                print(f"    Found comment button (icon), clicking...")
                                await view_comments_button.click()
                                await page.wait_for_timeout(2000)
                            
                            # Check for comments on the current image
                            comments_found = await self.extract_image_comments(page)
                            
                            if comments_found:
                                # Get image filename/title
                                filename = await self.get_image_filename(page)
                                if filename:
                                    result_item = {
                                        'filename': filename,
                                        'comments': comments_found,
                                        'image_index': i + 1
                                    }
                                    self.commented_images.append(result_item)
                                    
                                    # Write to file immediately (iterative writing)
                                    self._append_result_to_file(filename, comments_found, i + 1)
                                    
                                    print(f"  ✓ Found {len(comments_found)} comments on {filename}")
                                else:
                                    print(f"  ✓ Found comments but couldn't extract filename")
                            else:
                                print(f"  - No comments found")
                            
                            # Move to next image using right arrow key (except for last image)
                            if i < len(image_elements) - 1:
                                await page.keyboard.press('ArrowRight')
                                await page.wait_for_timeout(2000)  # Wait for next image to load
                            
                        except Exception as e:
                            print(f"  Error processing image {i+1}: {str(e)}")
                            # Try to continue to next image
                            if i < len(image_elements) - 1:
                                await page.keyboard.press('ArrowRight')
                                await page.wait_for_timeout(2000)
                            continue
                else:
                    print("No images found to process")
                
                print(f"\nScan complete! Found {len(self.commented_images)} images with comments")
                
                # Update output file with final summary
                self._finalize_output_file()
                
            except Exception as e:
                print(f"Error during scraping: {str(e)}")
                # Take screenshot for debugging
                await page.screenshot(path="/Users/trigg/Development/SmugMug-Client-Selection-Tool/output/debug_error.png")
                print("Debug screenshot saved to output/debug_error.png")
                
            finally:
                await browser.close()
        
        return self.commented_images
    
    async def extract_image_comments(self, page):
        """Extract comments from the current image page - specifically looking for Clair Polleti"""
        comments = []
        
        try:
            # Wait for comments to load
            await page.wait_for_timeout(3000)
            
            # Get all page text to search for Clair Polleti specifically
            all_page_text = await page.evaluate('() => document.body.innerText')
            
            # Check specifically for "Clair Polleti" (and variations)
            target_names = ['clair polleti', 'clair', 'polleti']
            has_clair_comment = any(name in all_page_text.lower() for name in target_names)
            
            if has_clair_comment:
                print(f"    Found Clair Polleti comment!")
                
                # Look for comment elements specifically containing Clair's name
                comment_selectors = [
                    '.sm-comments .sm-comment',
                    '.comments .comment', 
                    '.sm-user-ui-comments .sm-user-ui-comment',
                    '[class*="comment"]',
                    '[id*="comment"]',
                    '.sm-comment',
                    '.sm-comments',
                    'div[class*="user"]',
                    'div[class*="message"]',
                    'span[class*="comment"]',
                    'p[class*="comment"]'
                ]
                
                comment_elements = []
                found_selector = None
                
                for selector in comment_selectors:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        # Check if any elements contain Clair's name
                        for element in elements:
                            try:
                                text = await element.inner_text()
                                if text and any(name in text.lower() for name in target_names):
                                    comment_elements.append(element)
                                    found_selector = selector
                            except:
                                continue
                        if comment_elements:
                            break
                
                if comment_elements:
                    print(f"    Found {len(comment_elements)} comments from Clair using selector: {found_selector}")
                    
                    # Extract Clair's comments
                    for element in comment_elements:
                        try:
                            comment_text = await element.inner_text()
                            if comment_text and any(name in comment_text.lower() for name in target_names):
                                comments.append({
                                    'author': 'Clair Polleti',
                                    'text': comment_text.strip(),
                                    'timestamp': '',
                                    'selector_used': found_selector
                                })
                        except Exception as e:
                            continue
                
                # Also search in all page text for Clair's comments
                if not comments:
                    print(f"    Searching page text for Clair's comments...")
                    
                    # Split text into potential comment blocks and look for Clair's name
                    text_blocks = all_page_text.split('\n')
                    for block in text_blocks:
                        block = block.strip()
                        if block and len(block) > 10 and any(name in block.lower() for name in target_names):
                            comments.append({
                                'author': 'Clair Polleti', 
                                'text': block,
                                'timestamp': '',
                                'selector_used': 'text_search'
                            })
            
            # Debug output if no Clair comments found
            if not comments:
                print(f"    No comments from Clair Polleti found")
            else:
                print(f"    Found {len(comments)} comments from Clair Polleti")
                        
        except Exception as e:
            print(f"    Error extracting comments: {str(e)}")
        
        return comments
    
    async def get_image_filename(self, page):
        """Extract the filename from the bottom left corner overlay of the image"""
        try:
            # Method 1: Look for filename overlay text in bottom left corner
            # SmugMug typically shows filename as overlay text on images
            
            # Try various selectors for overlay text
            overlay_selectors = [
                '.sm-lightbox-overlay-text',
                '.sm-image-overlay',
                '.sm-filename-overlay',
                '[class*="overlay"][class*="text"]',
                '[class*="filename"]',
                '.sm-lightbox-info',
                '.sm-image-title',
                '.sm-image-name'
            ]
            
            for selector in overlay_selectors:
                overlay_element = await page.query_selector(selector)
                if overlay_element:
                    overlay_text = await overlay_element.inner_text()
                    if overlay_text:
                        # Look for filename pattern in overlay text
                        filename_match = re.search(r'([^/\\:]*\.(jpg|jpeg|png|gif|raw|dng|tiff|bmp|cr2|nef|arw))', overlay_text, re.IGNORECASE)
                        if filename_match:
                            print(f"    Found filename in overlay: {filename_match.group(1)}")
                            return filename_match.group(1)
            
            # Method 2: Look for any text elements that might contain filename
            # SmugMug might show filename as regular text overlay
            all_text_elements = await page.query_selector_all('div, span, p')
            for element in all_text_elements:
                try:
                    text = await element.inner_text()
                    if text and len(text) < 100:  # Filename shouldn't be too long
                        filename_match = re.search(r'([^/\\:]*\.(jpg|jpeg|png|gif|raw|dng|tiff|bmp|cr2|nef|arw))', text, re.IGNORECASE)
                        if filename_match:
                            # Check if this element is positioned like an overlay (bottom area)
                            bbox = await element.bounding_box()
                            if bbox and bbox['y'] > 400:  # Likely in bottom area
                                print(f"    Found filename in bottom overlay: {filename_match.group(1)}")
                                return filename_match.group(1)
                except:
                    continue
            
            # Method 3: Check page title
            title = await page.title()
            if title and title != "SmugMug":
                filename_match = re.search(r'([^/\\:]*\.(jpg|jpeg|png|gif|raw|dng|tiff|bmp|cr2|nef|arw))', title, re.IGNORECASE)
                if filename_match:
                    print(f"    Found filename in title: {filename_match.group(1)}")
                    return filename_match.group(1)
            
            # Method 4: Extract from URL
            current_url = page.url
            url_match = re.search(r'/i-([a-zA-Z0-9]+)', current_url)
            if url_match:
                return f"Image_{url_match.group(1)}"
            
            # Method 5: Try to get from img src attribute
            img_element = await page.query_selector('img[src*="smugmug"]')
            if img_element:
                img_src = await img_element.get_attribute('src')
                if img_src:
                    filename_match = re.search(r'/([^/]*\.(jpg|jpeg|png|gif|raw|dng|tiff|bmp))', img_src, re.IGNORECASE)
                    if filename_match:
                        return filename_match.group(1)
            
            return f"Unknown_{datetime.now().strftime('%H%M%S')}"
            
        except Exception as e:
            print(f"    Error getting filename: {str(e)}")
            return f"Unknown_{datetime.now().strftime('%H%M%S')}"
    
    def _finalize_output_file(self):
        """Add final summary to output file"""
        try:
            with open(self.output_file, 'a') as f:
                f.write(f"\n" + "=" * 50 + "\n")
                f.write(f"FINAL SUMMARY:\n")
                f.write(f"=" * 50 + "\n")
                f.write(f"Total: {len(self.commented_images)} images with comments\n")
                f.write(f"Scan completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                
                # Include comment details
                f.write(f"\n" + "=" * 50 + "\n")
                f.write(f"COMMENT DETAILS:\n")
                f.write(f"=" * 50 + "\n\n")
                
                for item in self.commented_images:
                    f.write(f"File: {item['filename']}\n")
                    f.write(f"Comments ({len(item['comments'])}):\n")
                    
                    for comment in item['comments']:
                        author = comment.get('author', 'Unknown')
                        text = comment.get('text', '')
                        f.write(f"  - {author}: {text}\n")
                    
                    f.write(f"\n")
        except Exception as e:
            print(f"Error finalizing output file: {e}")
    
    def save_results(self, album_name="Dragonhood"):
        """Return the output file path (file already written iteratively)"""
        if not self.commented_images:
            print("No commented images found")
            return self.output_file
        
        print(f"\nResults written iteratively to: {self.output_file}")
        return self.output_file


async def main():
    """Main function"""
    gallery_url = "https://triggbowlin.smugmug.com/Dragonhood/n-B4hbdN"
    password = "firebreathing"
    
    scraper = SmugMugWebScraper(gallery_url, password)
    commented_images = await scraper.scrape_gallery_comments()
    
    if commented_images:
        output_file = scraper.save_results()
        print(f"\nSUMMARY:")
        print(f"Gallery: Dragonhood")
        print(f"Images with comments: {len(commented_images)}")
        print(f"Output file: {output_file}")
        
        # Show preview of commented image filenames
        print(f"\nPreview of commented image filenames:")
        for i, item in enumerate(commented_images[:10]):
            print(f"  {item['filename']}")
        
        if len(commented_images) > 10:
            print(f"  ... and {len(commented_images) - 10} more")
    else:
        print("\nNo images with comments found in the gallery")


if __name__ == "__main__":
    asyncio.run(main())
