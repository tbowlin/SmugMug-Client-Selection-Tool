#!/usr/bin/env python3
"""
Debug script to analyze SmugMug gallery structure
"""

import asyncio
from playwright.async_api import async_playwright

async def debug_gallery_structure():
    print("SmugMug Gallery Structure Debugger")
    print("=" * 50)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # Navigate to gallery
            gallery_url = "https://triggbowlin.smugmug.com/Dragonhood/n-B4hbdN"
            print(f"Navigating to: {gallery_url}")
            await page.goto(gallery_url, timeout=30000)
            
            # Enter password
            await page.wait_for_timeout(3000)
            password_input = await page.query_selector('input[type="password"]')
            if password_input:
                print("Entering password...")
                await password_input.fill("firebreathing")
                await password_input.press('Enter')
                await page.wait_for_timeout(3000)
            
            print("\n--- GALLERY PAGE ANALYSIS ---")
            
            # Check pagination elements
            print("\n1. PAGINATION ANALYSIS:")
            pagination_selectors = [
                'a:has-text("Next")',
                'button:has-text("Next")', 
                'a:has-text("2")',
                'a:has-text("Show more")',
                'button:has-text("Load more")',
                '.pagination',
                '.sm-pagination',
                '[class*="page"]',
                '[class*="next"]',
                'a[rel="next"]'
            ]
            
            for selector in pagination_selectors:
                elements = await page.query_selector_all(selector)
                if elements:
                    print(f"  ✓ Found {len(elements)} elements with: {selector}")
                    for i, element in enumerate(elements[:3]):  # Show first 3
                        try:
                            text = await element.inner_text()
                            href = await element.get_attribute('href') if element else None
                            print(f"    [{i+1}] Text: '{text}' | Href: {href}")
                        except:
                            print(f"    [{i+1}] Could not read element")
                else:
                    print(f"  - No elements found with: {selector}")
            
            # Get page HTML to analyze structure
            print("\n2. PAGE STRUCTURE ANALYSIS:")
            page_html = await page.content()
            
            # Look for pagination keywords in HTML
            pagination_keywords = ['next', 'page', 'more', '2', 'pagination']
            for keyword in pagination_keywords:
                count = page_html.lower().count(keyword)
                if count > 0:
                    print(f"  - '{keyword}' appears {count} times in HTML")
            
            # Click on first image to analyze lightbox
            print("\n3. LIGHTBOX ANALYSIS:")
            image_links = await page.query_selector_all('a[href*="/i-"], img')
            if image_links:
                print(f"Found {len(image_links)} image elements, clicking first one...")
                await image_links[0].click()
                await page.wait_for_timeout(3000)
                
                # Look for comment-related elements
                print("\n4. COMMENT BUTTON ANALYSIS:")
                comment_button_selectors = [
                    'button:has-text("view comments")',
                    'button:has-text("View Comments")',
                    'a:has-text("Comments")',
                    'button:has-text("comments")',
                    '[class*="comment"]',
                    'button[aria-label*="comment"]',
                    '.sm-comments-toggle'
                ]
                
                for selector in comment_button_selectors:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        print(f"  ✓ Found comment button with: {selector}")
                        element = elements[0]
                        text = await element.inner_text()
                        print(f"    Text: '{text}'")
                    else:
                        print(f"  - No comment button found with: {selector}")
                
                # Show all buttons on the page
                print("\n5. ALL BUTTONS ANALYSIS:")
                all_buttons = await page.query_selector_all('button, a, [role="button"]')
                print(f"Found {len(all_buttons)} clickable elements:")
                
                for i, button in enumerate(all_buttons[:20]):  # Show first 20
                    try:
                        text = await button.inner_text()
                        tag = await button.evaluate('el => el.tagName')
                        classes = await button.get_attribute('class')
                        if text and len(text.strip()) > 0 and len(text.strip()) < 50:
                            print(f"  [{i+1}] {tag}: '{text.strip()}' | Classes: {classes}")
                    except:
                        continue
                
                # Take screenshots for manual analysis
                await page.screenshot(path="/Users/trigg/Development/SmugMug-Client-Selection-Tool/output/debug_lightbox.png")
                print(f"\nScreenshot saved: debug_lightbox.png")
            
            await page.screenshot(path="/Users/trigg/Development/SmugMug-Client-Selection-Tool/output/debug_gallery_main.png")
            print(f"Screenshot saved: debug_gallery_main.png")
            
        except Exception as e:
            print(f"Error during debugging: {str(e)}")
            
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_gallery_structure())
