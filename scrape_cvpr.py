import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import os
import argparse
from urllib.parse import urljoin

# Base URL
BASE_URL = "https://openaccess.thecvf.com/"

def get_paper_details(paper_url):
    """
    Fetches the abstract and PDF URL from the paper's detail page.
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
        
        # Extract PDF URL
        pdf_url = ""
        # Look for PDF link (usually an <a> tag with href ending in .pdf)
        pdf_link = soup.find('a', href=lambda x: x and x.endswith('.pdf'))
        if pdf_link:
            pdf_url = urljoin(BASE_URL, pdf_link['href'])
        
        return abstract, pdf_url

    except Exception as e:
        print(f"Error fetching details for {paper_url}: {e}")
        return "", ""

def download_pdf(pdf_url, save_dir, filename):
    """
    Downloads a PDF file from the given URL.
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(save_dir, exist_ok=True)
        
        # Sanitize filename
        safe_filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_filename = safe_filename[:200]  # Limit filename length
        filepath = os.path.join(save_dir, f"{safe_filename}.pdf")
        
        # Skip if file already exists
        if os.path.exists(filepath):
            print(f"    PDF already exists: {safe_filename}.pdf")
            return filepath
        
        # Download PDF
        response = requests.get(pdf_url, timeout=30, stream=True)
        response.raise_for_status()
        
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"    Downloaded PDF: {safe_filename}.pdf")
        return filepath
        
    except Exception as e:
        print(f"    Error downloading PDF: {e}")
        return ""

def scrape_year(year, conference, download_pdfs=False, pdf_dir=""):
    """
    Scrapes all papers for a specific year and conference.
    """
    print(f"Starting scrape for {conference.upper()} {year}...")
    
    # CVPR 2020 uses a different URL structure (by day, not 'all')
    if conference.upper() == "CVPR" and year == 2020:
        # For 2020, we need to scrape multiple days
        days = ["2020-06-16", "2020-06-17", "2020-06-18"]
        all_papers = []
        for day in days:
            url = f"{BASE_URL}{conference.upper()}{year}?day={day}"
            papers = scrape_day(url, year, day, conference, download_pdfs, pdf_dir)
            all_papers.extend(papers)
        return all_papers
    else:
        # The 'all' day usually lists all papers for other years
        url = f"{BASE_URL}{conference.upper()}{year}?day=all"
        return scrape_day(url, year, "all", conference, download_pdfs, pdf_dir)

def scrape_day(url, year, day, conference, download_pdfs=False, pdf_dir=""):
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
        abstract, pdf_url = get_paper_details(full_link)
        
        # Download PDF if requested
        pdf_path = ""
        if download_pdfs and pdf_url:
            pdf_filename = f"{conference}_{year}_{title}"
            pdf_path = download_pdf(pdf_url, pdf_dir, pdf_filename)
        
        papers_data.append({
            "Conference": conference.upper(),
            "Year": year,
            "Title": title,
            "Abstract": abstract,
            "URL": full_link,
            "PDF_URL": pdf_url,
            "PDF_Path": pdf_path
        })
        
        # Optional: Sleep to be polite
        # time.sleep(0.1) 

    return papers_data

def parse_arguments():
    """
    Parse command line arguments.
    """
    parser = argparse.ArgumentParser(
        description='Scrape papers from CVF conferences (CVPR, ICCV, WACV, ECCV, ACCV)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scrape CVPR papers from 2020 to 2022
  python scrape_cvpr.py --conference CVPR --start-year 2020 --end-year 2022
  
  # Scrape multiple conferences
  python scrape_cvpr.py --conference CVPR ICCV --start-year 2021 --end-year 2023
  
  # Specify output and PDF directories
  python scrape_cvpr.py --conference CVPR --start-year 2020 --end-year 2022 --output-dir data --pdf-dir papers
  
  # Download PDFs
  python scrape_cvpr.py --conference CVPR --start-year 2020 --end-year 2022 --download-pdf
        """
    )
    
    parser.add_argument(
        '--conference', '-c',
        nargs='+',
        choices=['CVPR', 'ICCV', 'WACV', 'ECCV', 'ACCV'],
        required=True,
        help='Conference(s) to scrape. Can specify multiple conferences.'
    )
    
    parser.add_argument(
        '--start-year', '-s',
        type=int,
        required=True,
        help='Start year (inclusive)'
    )
    
    parser.add_argument(
        '--end-year', '-e',
        type=int,
        required=True,
        help='End year (inclusive)'
    )
    
    parser.add_argument(
        '--output-dir', '-od',
        type=str,
        default='xlsx',
        help='Directory to save output Excel files (default: xlsx)'
    )
    
    parser.add_argument(
        '--download-pdf', '-dp',
        action='store_true',
        help='Download PDF files for all papers'
    )
    
    parser.add_argument(
        '--pdf-dir', '-pd',
        type=str,
        default='pdf',
        help='Directory to save PDF files (default: pdf)'
    )
    
    args = parser.parse_args()
    
    # Validate year range
    if args.start_year > args.end_year:
        parser.error(f"Start year ({args.start_year}) must be <= end year ({args.end_year})")
    
    # Validate pdf-dir only when download-pdf is enabled
    if not args.download_pdf and args.pdf_dir != 'pdf':
        parser.error("--pdf-dir can only be used with --download-pdf")
    
    return args

def main():
    args = parse_arguments()
    
    conferences = args.conference
    years = list(range(args.start_year, args.end_year + 1))
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Generate output filename
    conference_str = '_'.join(conferences)
    output_file = os.path.join(args.output_dir, f"{conference_str}_{args.start_year}_{args.end_year}.xlsx")
    
    print(f"Configuration:")
    print(f"  Conferences: {', '.join(conferences)}")
    print(f"  Years: {args.start_year} - {args.end_year}")
    print(f"  Output directory: {args.output_dir}")
    print(f"  Output file: {output_file}")
    print(f"  Download PDFs: {args.download_pdf}")
    if args.download_pdf:
        print(f"  PDF directory: {args.pdf_dir}")
    print()
    
    all_papers = []
    
    for conference in conferences:
        for year in years:
            year_papers = scrape_year(year, conference, args.download_pdf, args.pdf_dir)
            all_papers.extend(year_papers)
            print(f"Finished {conference} {year}. Total papers so far: {len(all_papers)}")
            
            # Save intermediate results
            df = pd.DataFrame(all_papers)
            df.to_excel(output_file, index=False, engine='openpyxl')
            print(f"Saved progress to {output_file}")
            print()

    print("Scraping complete!")
    print(f"Total papers scraped: {len(all_papers)}")
    print(f"Data saved to {output_file}")

if __name__ == "__main__":
    main()
