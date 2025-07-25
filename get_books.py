import requests
from bs4 import BeautifulSoup
import time
import random
import csv
from datetime import datetime


def scrape_goodreads_book(book_id):
    """Scrape book details from Goodreads by book ID"""
    url = f"https://www.goodreads.com/book/show/{book_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        if "Page not found" in response.text:
            return None

        soup = BeautifulSoup(response.text, "html.parser")

        # Extract book details
        title = (
            soup.select_one("h1.Text__title1").get_text(strip=True)
            if soup.select_one("h1.Text__title1")
            else None
        )

        author = (
            soup.select_one(".ContributorLink__name").get_text(strip=True)
            if soup.select_one(".ContributorLink__name")
            else None
        )

        rating_element = soup.select_one(".RatingStatistics__rating")
        avg_rating = rating_element.get_text(strip=True) if rating_element else None

        ratings_count = (
            soup.select_one('[data-testid="ratingsCount"]')
            .get_text(strip=True)
            .split()[0]
            if soup.select_one('[data-testid="ratingsCount"]')
            else None
        )

        reviews_count = (
            soup.select_one('[data-testid="reviewsCount"]')
            .get_text(strip=True)
            .split()[0]
            if soup.select_one('[data-testid="reviewsCount"]')
            else None
        )

        isbn = None
        pages = None
        pub_info = None
        details = soup.select(".FeaturedDetails p")
        for detail in details:
            text = detail.get_text(strip=True)
            if "ISBN" in text:
                isbn = text.split(":")[-1].strip()
            elif "pages" in text:
                pages = text.split()[0]
            elif "Published" in text:
                pub_info = text.split("by")[-1].strip()

        genres = [
            a.get_text(strip=True)
            for a in soup.select(".BookPageMetadataSection__genreButton a")
        ]

        return {
            "book_id": book_id,
            "url": url,
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

    except requests.exceptions.RequestException as e:
        print(f"Request failed for book {book_id}: {str(e)}")
        return None
    except Exception as e:
        print(f"Error scraping book {book_id}: {str(e)}")
        return None


def main():
    # Configuration
    START_ID = 1
    END_ID = 100000
    OUTPUT_FILE = "goodreads_books.csv"
    DELAY = 1.5  # Base delay in seconds
    MAX_DELAY = 3  # Maximum delay for random variation

    # CSV headers
    fieldnames = [
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
    ]

    # Open CSV file for writing
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        successful = 0
        skipped = 0

        for book_id in range(START_ID, END_ID + 1):
            # Random delay to avoid rate limiting
            time.sleep(DELAY + random.uniform(0, MAX_DELAY))

            book_data = scrape_goodreads_book(book_id)

            if book_data:
                writer.writerow(book_data)
                successful += 1
                print(f"✅ Scraped book {book_id}: {book_data['title']}")
            else:
                skipped += 1
                print(f"⏩ Skipped book {book_id}")

            # Progress update
            if (book_id - START_ID + 1) % 100 == 0:
                print(f"\n📊 Progress: {book_id}/{END_ID}")
                print(f"📥 Successful: {successful} | 🚫 Skipped: {skipped}\n")

    print(f"\nScraping completed! Results saved to {OUTPUT_FILE}")
    print(f"Total books scraped: {successful}")
    print(f"Total books skipped: {skipped}")


if __name__ == "__main__":
    main()
