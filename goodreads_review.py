import scrapy
import re
import time
import random
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
from webdriver_manager.chrome import ChromeDriverManager
from scrapy_selenium import SeleniumRequest


class GoodreadsReviewsSpider(scrapy.Spider):
    name = "goodreads_reviews"
    allowed_domains = ["goodreads.com"]

    # Configuration
    START_ID = 1
    END_ID = 10
    MAX_REVIEWS_PER_BOOK = 10
    DELAY_MIN = 3.0
    DELAY_MAX = 6.0
    DEBUG = False
    HEADLESS = True
    CHROME_BINARY_PATH = "/usr/bin/google-chrome-beta"

    custom_settings = {
        "FEEDS": {
            "goodreads_reviews.csv": {
                "format": "csv",
                "fields": [
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
                ],
                "overwrite": True,
            },
        },
        "DOWNLOAD_DELAY": 0,  # We handle delays manually with Selenium
        "CONCURRENT_REQUESTS": 1,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "DOWNLOADER_MIDDLEWARES": {"scrapy_selenium.SeleniumMiddleware": 800},
        "SELENIUM_DRIVER_NAME": "chrome",
        "SELENIUM_DRIVER_EXECUTABLE_PATH": None,  # Will be set by ChromeDriverManager
        "SELENIUM_DRIVER_ARGUMENTS": [],  # Will be configured in spider
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.driver = None
        self.setup_selenium()

    def setup_selenium(self):
        """Configure Chrome WebDriver - preserving original setup logic"""
        options = Options()
        options.binary_location = self.CHROME_BINARY_PATH
        options.add_argument("--incognito")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-plugins")
        options.add_argument("--disable-popup-blocking")

        if self.HEADLESS:
            options.add_argument("--headless=new")

        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1280,720")
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        )

        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        # Update custom settings for scrapy-selenium
        self.custom_settings["SELENIUM_DRIVER_ARGUMENTS"] = [
            arg for arg in options.arguments
        ]

        # Store options for manual driver creation if needed
        self.chrome_options = options

    def start_requests(self):
        """Generate Selenium requests for all book IDs"""
        for book_id in range(self.START_ID, self.END_ID + 1):
            url = f"https://www.goodreads.com/book/show/{book_id}"
            yield SeleniumRequest(
                url=url,
                callback=self.parse_book_page,
                meta={"book_id": book_id},
                dont_filter=True,
                wait_time=15,
                wait_until=EC.presence_of_element_located(
                    (By.CSS_SELECTOR, 'h1[data-testid="bookTitle"], h1.Text__title1')
                ),
            )

    def parse_book_page(self, response):
        """Parse book page with Selenium - preserving original parsing logic"""
        book_id = response.meta["book_id"]
        driver = response.meta["driver"]

        self.logger.info(f"Processing book ID: {book_id}")

        try:
            # Expand reviews safely - preserving original logic
            self.expand_reviews_on_page(driver)
            time.sleep(2)

            # Extract book details using original Selenium logic
            title = self.extract_book_title(driver)
            author = self.extract_book_author(driver)
            avg_rating = self.extract_avg_rating(driver)
            ratings_count = self.extract_ratings_count(driver)
            reviews_count = self.extract_reviews_count(driver)

            self.logger.info(f"📖 Book: {title} by {author}")
            self.logger.info(f"⭐ Avg Rating: {avg_rating} ({ratings_count} ratings)")

            # Extract reviews - preserving original logic
            reviews = self.extract_reviews(driver, book_id)

            self.logger.info(f"📝 Found {len(reviews)} reviews on the page")

            # Yield each review with book details
            for review in reviews:
                review.update(
                    {
                        "book_title": self.clean_text(title),
                        "book_author": self.clean_text(author),
                        "book_avg_rating": avg_rating,
                        "book_ratings_count": ratings_count,
                    }
                )
                yield review

            self.logger.info(f"✅ Completed book ID {book_id}: {title}")

            # Manual delay between books
            time.sleep(self.get_random_delay() * 2)

        except Exception as e:
            self.logger.error(f"Error processing book {book_id}: {str(e)}")

    def expand_reviews_on_page(self, driver):
        """Click 'Show more' buttons safely - preserving original logic"""
        try:
            expand_buttons = driver.find_elements(
                By.CSS_SELECTOR, 'button[aria-label="Tap to show more review"]'
            )

            self.logger.info(
                f"Found {len(expand_buttons)} safe expand buttons on the page"
            )

            for i, button in enumerate(expand_buttons):
                try:
                    driver.execute_script(
                        "arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});",
                        button,
                    )
                    time.sleep(0.3)

                    driver.execute_script("arguments[0].click();", button)
                    self.logger.info(
                        f"Clicked safe expand button {i + 1}/{len(expand_buttons)}"
                    )

                    time.sleep(random.uniform(1.0, 2.0))
                except Exception as e:
                    self.logger.info(f"Skipping button: {str(e)}")
                    continue

            return True
        except Exception as e:
            self.logger.error(f"Error expanding reviews: {str(e)}")
            return False

    def extract_book_title(self, driver):
        """Extract book title - preserving original logic"""
        try:
            return driver.find_element(
                By.CSS_SELECTOR, 'h1[data-testid="bookTitle"]'
            ).text
        except:
            try:
                return driver.find_element(By.CSS_SELECTOR, "h1.Text__title1").text
            except:
                return "Unknown Title"

    def extract_book_author(self, driver):
        """Extract book author - preserving original logic"""
        try:
            return driver.find_element(
                By.CSS_SELECTOR, "span.ContributorLink__name"
            ).text
        except:
            try:
                return driver.find_element(
                    By.CSS_SELECTOR, 'a[data-testid="nameLink"]'
                ).text
            except:
                return "Unknown Author"

    def extract_avg_rating(self, driver):
        """Extract average rating - preserving original logic"""
        try:
            return driver.find_element(
                By.CSS_SELECTOR, 'div[data-testid="avgRating"]'
            ).text
        except:
            try:
                return driver.find_element(
                    By.CSS_SELECTOR, ".RatingStatistics__rating"
                ).text
            except:
                return "N/A"

    def extract_ratings_count(self, driver):
        """Extract ratings count - preserving original logic"""
        try:
            return driver.find_element(
                By.CSS_SELECTOR, 'span[data-testid="ratingsCount"]'
            ).text.split()[0]
        except:
            try:
                return driver.find_element(
                    By.CSS_SELECTOR, '[data-testid="ratingsCount"]'
                ).text.split()[0]
            except:
                return "0"

    def extract_reviews_count(self, driver):
        """Extract reviews count - preserving original logic"""
        try:
            return driver.find_element(
                By.CSS_SELECTOR, 'span[data-testid="reviewsCount"]'
            ).text.split()[0]
        except:
            try:
                return driver.find_element(
                    By.CSS_SELECTOR, '[data-testid="reviewsCount"]'
                ).text.split()[0]
            except:
                return "0"

    def extract_reviews(self, driver, book_id):
        """Extract reviews - preserving original parsing logic"""
        reviews = []

        try:
            review_cards = driver.find_elements(
                By.CSS_SELECTOR, "article.ReviewCard, div.ReviewCard"
            )
            self.logger.info(f"Found {len(review_cards)} review cards on the page")

            for i, card in enumerate(review_cards):
                try:
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
                        rating = self.extract_rating(rating_el)
                    except:
                        pass

                    # Date
                    try:
                        date = card.find_element(
                            By.CSS_SELECTOR, ".Text__metadata, .ReviewCard-date"
                        ).text
                    except:
                        date = "Unknown date"

                    # Review text - preserving original logic
                    review_text = ""
                    try:
                        text_container = card.find_element(
                            By.CSS_SELECTOR, ".TruncatedContent_text--expanded"
                        )
                        review_text = text_container.text
                    except:
                        try:
                            text_container = card.find_element(
                                By.CSS_SELECTOR, ".ReviewText"
                            )
                            review_text = text_container.text
                        except:
                            review_text = card.text

                    review_text = self.clean_text(review_text)
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

                    self.logger.info(
                        f"Scraped review {i + 1}/{len(review_cards)} from {reviewer}"
                    )

                except Exception as e:
                    self.logger.error(f"Error processing review card {i + 1}: {str(e)}")
                    continue

        except Exception as e:
            self.logger.error(f"Error finding review cards: {str(e)}")

        return reviews

    def extract_rating(self, rating_element):
        """Extract numeric rating - preserving original logic"""
        if not rating_element:
            return None

        aria_label = rating_element.get_attribute("aria-label")
        if aria_label:
            match = re.search(r"(\d+\.?\d*)", aria_label)
            if match:
                return float(match.group(1))

        return None

    def clean_text(self, text):
        """Clean and normalize text - preserving original logic"""
        if text is None:
            return ""
        text = text.replace("\n", " ").replace("\r", " ").replace("\t", " ")
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def get_random_delay(self):
        """Return a random delay - preserving original logic"""
        return random.uniform(self.DELAY_MIN, self.DELAY_MAX)

    def close(self, reason):
        """Clean up when spider closes"""
        if self.driver:
            self.driver.quit()
            self.logger.info("Browser closed")


# Pipeline for processing scraped reviews
class GoodreadsReviewsPipeline:
    def process_item(self, item, spider):
        # Additional processing if needed
        return item


# Additional settings
BOT_NAME = "goodreads_reviews_scraper"
ROBOTSTXT_OBEY = False
ITEM_PIPELINES = {
    "__main__.GoodreadsReviewsPipeline": 300,
}
