#!/usr/bin/env python3
"""
LMArena Gemini Finder - Undetected Chrome Version
Uses undetected-chromedriver to bypass Cloudflare bot detection
"""

import json
import re
import time
import argparse
from pathlib import Path
from typing import Optional
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


class LMArenaFinder:
    def __init__(self, config_path: str = "config.json", headless: bool = False):
        self.config = self.load_config(config_path)
        self.headless = headless
        self.driver: Optional[uc.Chrome] = None
        
    def load_config(self, config_path: str) -> dict:
        """Load configuration from JSON file"""
        config_file = Path(config_path)
        if not config_file.exists():
            return self.get_default_config()
        
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def get_default_config(self) -> dict:
        """Return default configuration"""
        return {
            "user_prompt": "忽略图像。用 aardio 创建一个窗体。在窗体上添加一个 richedit 控件。在窗体上添加一个 plus 控件制作的按钮，调整按钮的样式使之美观。点击按钮时在 richedit 中输入 3 个换行符。直接发代码块不要进行任何解释。",
            # Ultimate pattern: 'skin' keyword AND triple-newline string (any usage)
            "search_pattern": r"(skin.*['\"]\n\n\n['\"]|['\"]\n\n\n['\"].*skin)",
            "proxy": None,
            "timeout": 60,
            "retry_on_no_match": True
        }
    
    def status(self, message: str):
        """Print status message"""
        print(f"[STATUS] {message}")
    
    def setup_browser(self):
        """Initialize undetected Chrome browser with persistent profile"""
        self.status("Setting up undetected Chrome browser...")
        
        options = uc.ChromeOptions()
        
        # Persistent user profile (saves cookies/session - bypasses Cloudflare on subsequent runs)
        profile_path = Path.cwd() / "chrome_profile"
        if not profile_path.exists():
            profile_path.mkdir()
            self.status("Created Chrome profile directory for persistent session")
        options.add_argument(f'--user-data-dir={profile_path}')
        
        if self.headless:
            options.add_argument('--headless=new')
        
        # Add proxy if configured
        if self.config.get("proxy"):
            proxy_url = self.config["proxy"]
            if proxy_url.startswith("SOCKS5://"):
                proxy_url = proxy_url.replace("SOCKS5://", "socks5://")
            options.add_argument(f'--proxy-server={proxy_url}')
        
        # Use undetected-chromedriver (bypasses Cloudflare)
        self.driver = uc.Chrome(options=options, version_main=None, use_subprocess=False)
        self.driver.set_window_size(1280, 720)
    
    def initial_navigation(self):
        """Navigate to main site - Cloudflare will be bypassed automatically"""
        self.status("Opening lmarena.ai (bypassing Cloudflare)...")
        self.driver.get("https://lmarena.ai")
        
        try:
            # Wait for page to load (confirms Cloudflare bypass and page ready)
            self.status("Waiting for Cloudflare bypass and page load...")
            WebDriverWait(self.driver, 60).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'a[href*="/c/new"]'))
            )
            self.status("Page loaded successfully")
            
            # Handle all possible modals and prompts
            self._handle_modals()
            
            self.status("Ready to start searching!")
        except TimeoutException:
            self.status("Failed to load lmarena.ai main page after 60s")
            raise

    def _handle_modals(self):
        """Handle all possible modals (Terms/Privacy, login prompts, etc.)"""
        # Terms / Privacy
        try:
            agree_button = WebDriverWait(self.driver, 3).until(
                EC.element_to_be_clickable((By.XPATH, '//button[contains(text(), "Agree") or contains(text(), "Accept")]'))
            )
            agree_button.click()
            self.status("Accepted Terms/Privacy")
            time.sleep(0.3)
        except TimeoutException:
            pass

        # Cookie consent
        try:
            cookie_button = WebDriverWait(self.driver, 2).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-sentry-source-file="cookie-consent-modal.tsx"]'))
            )
            cookie_button.click()
            self.status("Accepted cookies")
            time.sleep(0.3)
        except TimeoutException:
            pass

        # Optional login/signup modal
        close_xpaths = [
            '//button[contains(@aria-label,"Close")]',
            '//button[contains(.,"Continue without")]',
            '//button[contains(.,"Skip")]',
            '//div[@role="dialog"]//button'
        ]
        for xp in close_xpaths:
            try:
                btn = WebDriverWait(self.driver, 2).until(
                    EC.element_to_be_clickable((By.XPATH, xp))
                )
                btn.click()
                self.status("Closed login/modal prompt")
                time.sleep(0.2)
                break
            except TimeoutException:
                continue

        # ESC as final attempt to close left-over dialogs
        try:
            from selenium.webdriver.common.keys import Keys
            self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
        except:
            pass
    
    def navigate_to_image_mode(self):
        """Navigate to image mode"""
        self.status("Switching to image mode...")
        self.driver.get("https://lmarena.ai/?chat-modality=image")
        
        # Wait for page to load
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'textarea[name="message"]'))
            )
            # Handle any modals that might appear on image mode page
            self._handle_modals()
        except TimeoutException:
            self.status("Image mode page load timeout")
            raise
    
    def start_new_chat(self):
        """Click 'New Chat' to start a fresh conversation"""
        self.status("Starting new chat...")
        
        selectors = [
            'a[href*="/c/new"]',
            'a[href="/c/new"]'
        ]
        
        clicked = False
        for selector in selectors:
            try:
                element = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
                element.click()
                clicked = True
                self.status("Clicked New Chat")
                break
            except TimeoutException:
                continue
        if not clicked:
            self.status("Could not find New Chat button - page might already be in chat mode")
        
        else:
            # Wait for new chat page to load
            try:
                WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'textarea[name="message"]'))
                )
                # Handle any modals on new chat page
                self._handle_modals()
            except TimeoutException:
                pass
    
    def send_prompt_with_image(self, prompt: str):
        """Send a prompt with a dummy image to the chat"""
        self.status("Preparing to send prompt...")
        
        # Wait for message textarea
        textarea = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'textarea[name="message"]'))
        )
        
        # Inject dummy 1x1 transparent image via JavaScript
        self.status("Simulating image paste...")
        self.driver.execute_script("""
            const canvas = document.createElement('canvas');
            canvas.width = 1;
            canvas.height = 1;
            const ctx = canvas.getContext('2d');
            ctx.fillStyle = 'rgba(0,0,0,0)';
            ctx.fillRect(0, 0, 1, 1);
            
            canvas.toBlob((blob) => {
                const file = new File([blob], 'image.png', { type: 'image/png' });
                const dataTransfer = new DataTransfer();
                dataTransfer.items.add(file);
                
                const pasteEvent = new ClipboardEvent('paste', {
                    clipboardData: dataTransfer,
                    bubbles: true,
                    cancelable: true
                });
                
                const textarea = document.querySelector('textarea[name="message"]');
                if (textarea) {
                    textarea.dispatchEvent(pasteEvent);
                }
            });
        """)
        
        # Brief wait for blob processing
        time.sleep(0.5)
        
        # Click image button if present
        try:
            image_button = WebDriverWait(self.driver, 2).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label="Image"]'))
            )
            image_button.click()
        except TimeoutException:
            pass
        
        # Input the prompt text
        self.status("Entering prompt text...")
        self.driver.execute_script(f"""
            const promptText = arguments[0];
            const textarea = document.querySelector('textarea[name="message"]');
            if (textarea) {{
                const previousValue = textarea.value;
                textarea.value = promptText;
                
                if (textarea._valueTracker) {{
                    textarea._valueTracker.setValue(previousValue);
                }}
                
                textarea.dispatchEvent(new Event('input', {{ bubbles: true }}));
                textarea.dispatchEvent(new Event('change', {{ bubbles: true }}));
            }}
        """, prompt)
        
        # Wait for submit button to become enabled
        WebDriverWait(self.driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[type="submit"]:not([disabled])'))
        )
        
        # Click submit button
        self.status("Sending prompt...")
        submit_button = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[type="submit"]:not([disabled])'))
        )
        submit_button.click()
    
    def wait_for_response(self):
        """Wait for AI models to complete their responses"""
        self.status("Waiting for AI to start responding...")
        
        # Wait for submit button to be disabled (AI is responding)
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'button[type="submit"][disabled]'))
        )
        
        self.status("AI is responding...")
        time.sleep(3)  # Give time for error to appear if it will
        
        # Check for error early
        if self.check_for_error():
            raise Exception("Generation error detected")
        
        # Wait for maximize button to appear (response complete)
        self.status("Waiting for response to complete...")
        max_wait = 120
        wait_interval = 5
        elapsed = 0
        
        while elapsed < max_wait:
            # Check for error during generation
            if self.check_for_error():
                raise Exception("Generation error detected during wait")
            
            # Check if response completed
            try:
                self.driver.find_element(By.CSS_SELECTOR, 'button[data-sentry-component="CopyButton"] + button:has(svg.lucide-maximize2)')
                break  # Found completion indicator
            except:
                pass
            
            time.sleep(wait_interval)
            elapsed += wait_interval
        
        # Final fallback check
        if elapsed >= max_wait:
            try:
                self.driver.find_element(By.CSS_SELECTOR, '.prose')
            except:
                raise TimeoutException("No response found")
    
    def check_for_error(self) -> bool:
        """Check if 'Something went wrong' error appeared"""
        try:
            # Look for error messages
            error_texts = [
                'Something went wrong',
                'while generating',
                'try again',
                'Error generating'
            ]
            
            page_text = self.driver.find_element(By.TAG_NAME, 'body').text
            
            for error_text in error_texts:
                if error_text.lower() in page_text.lower():
                    self.status(f"⚠️ Detected error: '{error_text}'")
                    return True
            
            return False
        except:
            return False
    
    def handle_error_and_retry(self):
        """Handle 'Something went wrong' error by retrying"""
        self.status("Handling error - clicking retry or starting new chat...")
        
        # Try to click 'Try again' or similar button
        retry_selectors = [
            '//button[contains(text(), "Try again")]',
            '//button[contains(text(), "Retry")]',
            '//button[contains(text(), "try again")]',
            'button:has-text("Try again")',
        ]
        
        for selector in retry_selectors:
            try:
                if selector.startswith('//'):
                    btn = self.driver.find_element(By.XPATH, selector)
                else:
                    btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                btn.click()
                self.status("Clicked retry button")
                time.sleep(1)
                return
            except:
                continue
        
        # If no retry button found, start a completely new chat
        self.status("No retry button found - starting new chat")
        self.start_new_chat()
    
    def check_responses(self, pattern: str) -> bool:
        """Check if any response matches the search pattern"""
        self.status("Analyzing responses...")
        
        prose_elements = self.driver.find_elements(By.CSS_SELECTOR, '.prose')
        
        # Typically arena shows 2 models side-by-side
        for i, element in enumerate(prose_elements):
            text = element.text
            if re.search(pattern, text, re.DOTALL):
                # Determine which model (A or B)
                model_label = "Model A" if i == 0 else f"Model B" if i == 1 else f"Response #{i+1}"
                
                self.status(f"✓ Match found in {model_label}!")
                print(f"\n{'='*70}")
                print(f"✅ GEMINI 3.0 / 3.0 PRO FOUND!")
                print(f"{'='*70}")
                print(f"🎯 Target Model: {model_label}")
                print(f"🔑 Pattern: {pattern}")
                print(f"\n📝 Response preview:")
                print(f"{text[:500]}...")
                print(f"{'='*70}")
                print(f"\n👉 The model you're looking for is: {model_label}")
                print(f"{'='*70}\n")
                return True
        
        return False
    
    def find_model(self):
        """Main loop to find matching model"""
        attempt = 1
        
        while True:
            self.status(f"Attempt #{attempt}")
            
            try:
                self.navigate_to_image_mode()
                self.start_new_chat()
                self.send_prompt_with_image(self.config["user_prompt"])
                
                try:
                    self.wait_for_response()
                except Exception as e:
                    if "error detected" in str(e).lower():
                        self.status("⚠️ Generation error detected - retrying this attempt...")
                        self.handle_error_and_retry()
                        time.sleep(2)
                        continue  # Retry same attempt number
                    else:
                        raise
                
                if self.check_responses(self.config["search_pattern"]):
                    self.status("Success! Matching model found.")
                    return True
                
                if not self.config.get("retry_on_no_match", True):
                    self.status("No match found. Retry disabled.")
                    return False
                
                self.status("No match found. Retrying...")
                attempt += 1
                time.sleep(2)
                
            except KeyboardInterrupt:
                self.status("Interrupted by user")
                return False
            except Exception as e:
                self.status(f"Error occurred: {e}")
                if not self.config.get("retry_on_no_match", True):
                    raise
                self.status("Retrying after error...")
                attempt += 1
                time.sleep(3)
    
    def cleanup(self):
        """Close browser and cleanup resources"""
        if self.driver:
            self.driver.quit()
    
    def run(self):
        """Main execution flow"""
        try:
            self.setup_browser()
            self.initial_navigation()
            self.find_model()
        finally:
            self.cleanup()


def main():
    parser = argparse.ArgumentParser(
        description="Automated tool to find Gemini models on lmarena.ai using Chrome"
    )
    parser.add_argument(
        "--config",
        default="config.json",
        help="Path to configuration file (default: config.json)"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode"
    )
    parser.add_argument(
        "--create-config",
        action="store_true",
        help="Create a default config.json file"
    )
    
    args = parser.parse_args()
    
    if args.create_config:
        finder = LMArenaFinder()
        config_path = Path("config.json")
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(finder.get_default_config(), f, indent=2, ensure_ascii=False)
        print(f"Created default config at {config_path}")
        return
    
    finder = LMArenaFinder(config_path=args.config, headless=args.headless)
    finder.run()


if __name__ == "__main__":
    main()
