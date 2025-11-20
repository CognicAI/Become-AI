import os
import requests
from bs4 import BeautifulSoup

def scrape_single_page(url, output_file="output/scraped_content.txt"):
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    try:
        # Fetch the webpage
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        response.raise_for_status()

        # Parse the page content
        soup = BeautifulSoup(response.text, "html.parser")

        # Extract only readable text (no scripts, styles, etc.)
        for element in soup(["script", "style", "noscript"]):
            element.extract()

        text = soup.get_text(separator="\n", strip=True)

        # Save text to file
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"URL: {url}\n\n")
            f.write(text)

        print(f"✅ Page scraped successfully and saved to {output_file}")

    except Exception as e:
        print(f"❌ Error scraping {url}: {e}")

if __name__ == "__main__":
    page_url = input("Enter the page URL to scrape: ").strip()
    scrape_single_page(page_url)
