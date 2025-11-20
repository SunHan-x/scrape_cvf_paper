import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import os
from urllib.parse import urljoin

# Configuration
YEARS = [2022, 2021, 2020]
BASE_URL = "https://openaccess.thecvf.com/"
OUTPUT_FILE = "cvpr_papers_2020_2022.csv"

def get_paper_details(paper_url):
    """
    Fetches the abstract and keywords from the paper's detail page.
    """
    try:
        response = requests.get(paper_url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract Abstract
        abstract_div = soup.find('div', id='abstract')
        abstract = abstract_div.get_text(strip=True) if abstract_div else ""
        
        # Remove the leading "Abstract" label if present
        if abstract.startswith("Abstract"):
            abstract = abstract[len("Abstract"):].strip()

        # Extract Keywords
        # Keywords are often not explicitly listed in a div, but might be in meta tags or just missing.
        # CVF pages usually don't have a dedicated keywords section in HTML.
        # We will check meta tags first.
        keywords = ""
        meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
        if meta_keywords:
            keywords = meta_keywords.get('content', '')
        
        # If not in meta, sometimes it's in the text, but hard to parse reliably.
        # We'll leave it as found (or empty).
        
        return abstract, keywords

    except Exception as e:
        print(f"Error fetching details for {paper_url}: {e}")
        return "", ""

def scrape_year(year):
    """
    Scrapes all papers for a specific year.
    """
    print(f"Starting scrape for CVPR {year}...")
    
    # CVPR 2020 uses a different URL structure (by day, not 'all')
    if year == 2020:
        # For 2020, we need to scrape multiple days
        days = ["2020-06-16", "2020-06-17", "2020-06-18"]
        all_papers = []
        for day in days:
            url = f"{BASE_URL}CVPR{year}?day={day}"
            papers = scrape_day(url, year, day)
            all_papers.extend(papers)
        return all_papers
    else:
        # The 'all' day usually lists all papers for other years
        url = f"{BASE_URL}CVPR{year}?day=all"
        return scrape_day(url, year, "all")

def scrape_day(url, year, day):
    """
    Scrapes papers from a specific day/page.
    """
    print(f"  Fetching {day} for {year}...")
    
    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to fetch page for {year} {day}: {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find all paper titles. They are usually in <dt> tags with class 'ptitle'
    # Or just links inside <dt> tags.
    # Structure is usually:
    # <dt class="ptitle"><br><a href="path/to/paper.html">Title</a></dt>
    # <dd>...authors...</dd>
    
    papers_data = []
    
    # Find all dt elements with class 'ptitle'
    dt_elements = soup.find_all('dt', class_='ptitle')
    
    print(f"  Found {len(dt_elements)} papers for {year} {day}.")
    
    for i, dt in enumerate(dt_elements):
        a_tag = dt.find('a')
        if not a_tag:
            continue
            
        title = a_tag.get_text(strip=True)
        relative_link = a_tag['href']
        full_link = urljoin(BASE_URL, relative_link)
        
        # Get details (Abstract, Keywords)
        # To be polite and avoid rate limits, we might want to sleep, 
        # but for 2000+ papers it will take forever. 
        # We'll try to run without sleep but handle errors.
        # For the user's script, I'll add a small delay or just let it run.
        # To speed up, one could use threading, but let's keep it simple and robust first.
        
        print(f"  [{i+1}/{len(dt_elements)}] Fetching details for: {title[:50]}...")
        abstract, keywords = get_paper_details(full_link)
        
        papers_data.append({
            "Year": year,
            "Title": title,
            "Abstract": abstract,
            "Keywords": keywords,
            "URL": full_link
        })
        
        # Optional: Sleep to be polite
        # time.sleep(0.1) 

    return papers_data

def main():
    all_papers = []
    
    for year in YEARS:
        year_papers = scrape_year(year)
        all_papers.extend(year_papers)
        print(f"Finished {year}. Total papers so far: {len(all_papers)}")
        
        # Save intermediate results
        df = pd.DataFrame(all_papers)
        df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
        print(f"Saved progress to {OUTPUT_FILE}")

    print("Scraping complete!")
    print(f"Total papers scraped: {len(all_papers)}")
    print(f"Data saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
