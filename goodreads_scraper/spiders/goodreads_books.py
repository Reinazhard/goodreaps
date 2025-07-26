import scrapy
import re
from datetime import datetime
from urllib.parse import urljoin


class GoodreadsBooksSpider(scrapy.Spider):
    name = "goodreads_books"
    allowed_domains = ["goodreads.com"]

    # Configuration
    START_ID = 1
    END_ID = 1000

    custom_settings = {
        "FEEDS": {
            "goodreads_books.csv": {
                "format": "csv",
                "fields": [
                    "book_id",
                    "url",
                    "title",
                    "author",
                    "avg_rating",
                    "ratings_count",
                    "reviews_count",
                    "isbn",
                    "pages",
                    "publisher",
                    "genres",
                    "scraped_at",
                ],
                "overwrite": True,
            },
        },
        "DOWNLOAD_DELAY": 1.5,
        "RANDOMIZE_DOWNLOAD_DELAY": 0.5,
        "CONCURRENT_REQUESTS": 1,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "DEFAULT_REQUEST_HEADERS": {
            "Accept-Language": "en-US,en;q=0.9",
        },
        "RETRY_TIMES": 3,
        "RETRY_HTTP_CODES": [500, 502, 503, 504, 408, 429],
    }

    def start_requests(self):
        """Generate requests for all book IDs"""
        for book_id in range(self.START_ID, self.END_ID + 1):
            url = f"https://www.goodreads.com/book/show/{book_id}"
            yield scrapy.Request(
                url=url,
                callback=self.parse_book,
                meta={"book_id": book_id},
                dont_filter=True,
                errback=self.handle_error,
            )

    def parse_book(self, response):
        """Parse book details from Goodreads page - preserving original logic"""
        book_id = response.meta["book_id"]

        # Check if page exists
        if "Page not found" in response.text:
            self.logger.info(f"⏩ Skipped book {book_id} - Page not found")
            return

        # Extract book details using original selectors
        title = self.extract_text(response, "h1.Text__title1")
        author = self.extract_text(response, ".ContributorLink__name")

        # Rating
        avg_rating = self.extract_text(response, ".RatingStatistics__rating")

        # Ratings and reviews count
        ratings_count = None
        ratings_element = response.css('[data-testid="ratingsCount"]::text').get()
        if ratings_element:
            ratings_count = ratings_element.strip().split()[0]

        reviews_count = None
        reviews_element = response.css('[data-testid="reviewsCount"]::text').get()
        if reviews_element:
            reviews_count = reviews_element.strip().split()[0]

        # Extract ISBN, pages, and publisher from details section
        isbn = None
        pages = None
        pub_info = None

        details = response.css(".FeaturedDetails p")
        for detail in details:
            text = detail.get()
            if text and "ISBN" in text:
                # Extract text content and get ISBN
                detail_text = "".join(detail.css("::text").getall())
                if ":" in detail_text:
                    isbn = detail_text.split(":")[-1].strip()
            elif text and "pages" in text:
                detail_text = "".join(detail.css("::text").getall())
                pages = detail_text.split()[0] if detail_text.split() else None
            elif text and "Published" in text:
                detail_text = "".join(detail.css("::text").getall())
                if "by" in detail_text:
                    pub_info = detail_text.split("by")[-1].strip()

        # Extract genres
        genres = []
        genre_elements = response.css(
            ".BookPageMetadataSection__genreButton a::text"
        ).getall()
        if genre_elements:
            genres = [genre.strip() for genre in genre_elements]

        book_data = {
            "book_id": book_id,
            "url": response.url,
            "title": title,
            "author": author,
            "avg_rating": avg_rating,
            "ratings_count": ratings_count,
            "reviews_count": reviews_count,
            "isbn": isbn,
            "pages": pages,
            "publisher": pub_info,
            "genres": ", ".join(genres) if genres else None,
            "scraped_at": datetime.now().isoformat(),
        }

        self.logger.info(f"✅ Scraped book {book_id}: {title}")
        yield book_data

    def extract_text(self, response, selector):
        """Helper method to extract text from CSS selector"""
        element = response.css(f"{selector}::text").get()
        return element.strip() if element else None

    def handle_error(self, failure):
        """Handle request errors"""
        book_id = failure.request.meta.get("book_id", "unknown")
        self.logger.error(f"Request failed for book {book_id}: {failure.value}")


# Custom pipeline to handle data cleaning if needed
class GoodreadsBooksPipeline:
    def process_item(self, item, spider):
        # Clean data if needed (preserving original data structure)
        return item


# Settings for the spider (can be in settings.py)
BOT_NAME = "goodreads_scraper"
ROBOTSTXT_OBEY = False
ITEM_PIPELINES = {
    "__main__.GoodreadsBooksPipeline": 300,
}
