import time
import random
import csv
import os
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    WebDriverException,
    ElementClickInterceptedException,
    StaleElementReferenceException,
)
from bs4 import BeautifulSoup
from webdriver_manager.chrome import ChromeDriverManager

# Configuration
START_ID = 1
END_ID = 1000  # Start with a small range for testing
MAX_REVIEWS_PER_BOOK = 10
DELAY_MIN = 3.0  # Minimum delay between actions
DELAY_MAX = 6.0  # Maximum delay between actions
OUTPUT_FILE = "goodreads_reviews.csv"
DEBUG = False
HEADLESS = True  # Keep visible for debugging
CHROME_BINARY_PATH = "/usr/bin/google-chrome-beta"  # Your Chrome Beta path


def get_random_delay():
    """Return a random delay between requests"""
    return random.uniform(DELAY_MIN, DELAY_MAX)


def clean_text(text):
    """Clean and normalize text"""
    if text is None:
        return ""
    text = text.replace("\n", " ").replace("\r", " ").replace("\t", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_rating(rating_element):
    """Extract numeric rating from the rating element"""
    if not rating_element:
        return None

    # Try to get from aria-label first
    aria_label = (
        rating_element.get_attribute("aria-label")
        if hasattr(rating_element, "get_attribute")
        else rating_element.get("aria-label", "")
    )
    if aria_label:
        match = re.search(r"(\d+\.?\d*)", aria_label)
        if match:
            return float(match.group(1))

    return None


def save_debug_html(book_id, html, prefix="book"):
    """Save HTML for debugging purposes"""
    if not DEBUG:
        return
    os.makedirs("debug", exist_ok=True)
    filename = f"debug/{prefix}_{book_id}_{int(time.time())}.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Saved debug HTML: {filename}")


def setup_driver():
    """Configure and return a Chrome WebDriver using specific Chrome binary in incognito mode"""
    options = Options()

    # Set your Chrome Beta binary path
    options.binary_location = CHROME_BINARY_PATH

    # Enable incognito mode
    options.add_argument("--incognito")

    # Other privacy-focused settings
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-plugins")
    options.add_argument("--disable-popup-blocking")

    if HEADLESS:
        options.add_argument("--headless=new")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,720")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    )

    # Add additional options to make browser appear more human-like
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--disable-blink-features=AutomationControlled")

    # Automatically download and use the correct chromedriver
    service = Service(ChromeDriverManager().install())

    driver = webdriver.Chrome(service=service, options=options)

    # Execute JavaScript to hide automation
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )

    return driver


def expand_reviews_on_page(driver):
    """Click 'Show more' buttons safely without triggering login"""
    try:
        # Find only the specific "Show more" buttons for review text
        expand_buttons = driver.find_elements(
            By.CSS_SELECTOR, 'button[aria-label="Tap to show more review"]'
        )

        print(f"Found {len(expand_buttons)} safe expand buttons on the page")

        # Click each button with JavaScript
        for i, button in enumerate(expand_buttons):
            try:
                # Scroll to the button
                driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});",
                    button,
                )
                time.sleep(0.3)

                # Click using JavaScript to avoid redirects
                driver.execute_script("arguments[0].click();", button)
                print(f"Clicked safe expand button {i + 1}/{len(expand_buttons)}")

                # Random delay between clicks
                time.sleep(random.uniform(1.0, 2.0))
            except Exception as e:
                print(f"Skipping button: {str(e)}")
                continue

        return True
    except Exception as e:
        print(f"Error expanding reviews: {str(e)}")
        return False


def scrape_book_page(driver, book_id):
    """Scrape book details and reviews using Selenium only"""
    url = f"https://www.goodreads.com/book/show/{book_id}"

    try:
        print(f"Navigating to book page: {url}")
        driver.get(url)
        time.sleep(get_random_delay() + 3)  # Extra time for page to load

        # Wait for main content to load
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, 'h1[data-testid="bookTitle"], h1.Text__title1')
                )
            )
        except TimeoutException:
            print("Timed out waiting for book title to load")
            return None

        # Expand reviews safely
        print("Expanding reviews...")
        expand_reviews_on_page(driver)
        time.sleep(2)  # Allow expansion to complete

        # DEBUG: Take screenshot after expansion
        if DEBUG:
            driver.save_screenshot(f"debug/screenshot_{book_id}.png")
            print(f"Screenshot saved: debug/screenshot_{book_id}.png")

        # Extract book details using Selenium
        try:
            title = driver.find_element(
                By.CSS_SELECTOR, 'h1[data-testid="bookTitle"]'
            ).text
        except:
            try:
                title = driver.find_element(By.CSS_SELECTOR, "h1.Text__title1").text
            except:
                title = "Unknown Title"
        print(f"Book Title: {title}")

        try:
            author = driver.find_element(
                By.CSS_SELECTOR, "span.ContributorLink__name"
            ).text
        except:
            try:
                author = driver.find_element(
                    By.CSS_SELECTOR, 'a[data-testid="nameLink"]'
                ).text
            except:
                author = "Unknown Author"
        print(f"Author: {author}")

        # Extract rating statistics
        try:
            avg_rating = driver.find_element(
                By.CSS_SELECTOR, 'div[data-testid="avgRating"]'
            ).text
        except:
            try:
                avg_rating = driver.find_element(
                    By.CSS_SELECTOR, ".RatingStatistics__rating"
                ).text
            except:
                avg_rating = "N/A"
        print(f"Avg Rating: {avg_rating}")

        try:
            ratings_count = driver.find_element(
                By.CSS_SELECTOR, 'span[data-testid="ratingsCount"]'
            ).text.split()[0]
        except:
            try:
                ratings_count = driver.find_element(
                    By.CSS_SELECTOR, '[data-testid="ratingsCount"]'
                ).text.split()[0]
            except:
                ratings_count = "0"
        print(f"Ratings Count: {ratings_count}")

        try:
            reviews_count = driver.find_element(
                By.CSS_SELECTOR, 'span[data-testid="reviewsCount"]'
            ).text.split()[0]
        except:
            try:
                reviews_count = driver.find_element(
                    By.CSS_SELECTOR, '[data-testid="reviewsCount"]'
                ).text.split()[0]
            except:
                reviews_count = "0"
        print(f"Reviews Count: {reviews_count}")

        # SCRAPE REVIEWS USING SELENIUM ONLY
        reviews = []
        print("Searching for reviews...")

        # Find review cards directly without section container
        try:
            review_cards = driver.find_elements(
                By.CSS_SELECTOR, "article.ReviewCard, div.ReviewCard"
            )
            print(f"Found {len(review_cards)} review cards on the page")

            for i, card in enumerate(review_cards):
                try:
                    # Scroll to review card
                    driver.execute_script(
                        "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                        card,
                    )
                    time.sleep(0.2)

                    # Reviewer
                    try:
                        reviewer = card.find_element(
                            By.CSS_SELECTOR, ".ReviewerProfile__name"
                        ).text
                    except:
                        try:
                            reviewer = card.find_element(By.CSS_SELECTOR, "a.user").text
                        except:
                            reviewer = "Anonymous"

                    # Rating
                    rating = None
                    try:
                        rating_el = card.find_element(
                            By.CSS_SELECTOR, "span[aria-label]"
                        )
                        rating = extract_rating(rating_el)
                    except:
                        pass

                    # Date
                    try:
                        date = card.find_element(
                            By.CSS_SELECTOR, ".Text__metadata, .ReviewCard-date"
                        ).text
                    except:
                        date = "Unknown date"

                    # Review text - get expanded content
                    review_text = ""
                    try:
                        # First try expanded content
                        text_container = card.find_element(
                            By.CSS_SELECTOR, ".TruncatedContent_text--expanded"
                        )
                        review_text = text_container.text
                    except:
                        try:
                            # Fallback to regular text container
                            text_container = card.find_element(
                                By.CSS_SELECTOR, ".ReviewText"
                            )
                            review_text = text_container.text
                        except:
                            # Final fallback to entire card text
                            review_text = card.text

                    # Clean review text
                    review_text = clean_text(review_text)

                    # Generate review ID
                    review_id = card.get_attribute("id") or f"review_{book_id}_{i}"

                    reviews.append(
                        {
                            "review_id": review_id,
                            "book_id": book_id,
                            "reviewer": reviewer,
                            "rating": rating,
                            "date": date,
                            "review_text": review_text,
                        }
                    )

                    print(f"Scraped review {i + 1}/{len(review_cards)} from {reviewer}")

                except Exception as e:
                    print(f"Error processing review card {i + 1}: {str(e)}")
                    continue
        except Exception as e:
            print(f"Error finding review cards: {str(e)}")

        print(f"Total reviews scraped: {len(reviews)}")

        return {
            "book_id": book_id,
            "title": clean_text(title),
            "author": clean_text(author),
            "avg_rating": avg_rating,
            "ratings_count": ratings_count,
            "reviews_count": reviews_count,
            "url": url,
            "reviews": reviews,
        }

    except (TimeoutException, NoSuchElementException) as e:
        print(f"Timeout or element not found for book {book_id}: {str(e)}")
        return None
    except Exception as e:
        print(f"Error scraping book page {book_id}: {str(e)}")
        return None


def main():
    # Create output directory
    os.makedirs("output", exist_ok=True)
    output_path = os.path.join("output", OUTPUT_FILE)

    # Initialize browser
    driver = setup_driver()
    print("Browser started in incognito mode")

    # CSV headers
    fieldnames = [
        "review_id",
        "book_id",
        "reviewer",
        "rating",
        "date",
        "review_text",
        "book_title",
        "book_author",
        "book_avg_rating",
        "book_ratings_count",
    ]

    try:
        # Open CSV file for writing
        with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            successful_books = 0
            successful_reviews = 0
            skipped_books = 0

            for book_id in range(START_ID, END_ID + 1):
                print(f"\n{'=' * 50}")
                print(f"Processing book ID: {book_id}")

                # Scrape the book page (details and reviews)
                book_data = scrape_book_page(driver, book_id)
                if not book_data:
                    skipped_books += 1
                    print(f"⏩ Skipped book ID {book_id}")
                    continue

                print(f"📖 Book: {book_data['title']} by {book_data['author']}")
                print(
                    f"⭐ Avg Rating: {book_data['avg_rating']} ({book_data['ratings_count']} ratings)"
                )
                print(f"📝 Found {len(book_data['reviews'])} reviews on the page")

                # Write reviews to CSV
                for review in book_data["reviews"]:
                    # Add book details to each review row
                    review.update(
                        {
                            "book_title": book_data["title"],
                            "book_author": book_data["author"],
                            "book_avg_rating": book_data["avg_rating"],
                            "book_ratings_count": book_data["ratings_count"],
                        }
                    )
                    writer.writerow(review)
                    successful_reviews += 1

                successful_books += 1

                # Progress update
                print(f"✅ Completed book ID {book_id}: {book_data['title']}")
                print(
                    f"📊 Progress: Books {book_id}/{END_ID}, Reviews: {successful_reviews}\n"
                )

                # Pause between books
                time.sleep(get_random_delay() * 2)

        print("\nScraping completed!")
        print(f"Total books processed: {successful_books}")
        print(f"Total reviews scraped: {successful_reviews}")
        print(f"Total books skipped: {skipped_books}")
        print(f"Results saved to: {output_path}")

    finally:
        # Close the browser when done
        driver.quit()
        print("Browser closed")


if __name__ == "__main__":
    main()
