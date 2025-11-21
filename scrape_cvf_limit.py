import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import os
import argparse
import re
from urllib.parse import urljoin
from excel_formatter import save_papers_to_excel, DEFAULT_COLUMN_CONFIG

# Base URL
BASE_URL = "https://openaccess.thecvf.com/"

def clean_text(text):
    """
    Remove illegal characters for Excel cells.
    Excel doesn't allow certain control characters.
    """
    if not text:
        return ""
    # Remove control characters except tab, newline, and carriage return
    # Excel allows: 0x09 (tab), 0x0A (newline), 0x0D (carriage return)
    cleaned = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F-\x9F]', '', text)
    return cleaned

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
        
        # Clean illegal characters for Excel
        abstract = clean_text(abstract)
        
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

def scrape_year(year, conference, download_pdfs=False, pdf_dir="", limit=None):
    """
    Scrapes all papers for a specific year and conference.
    
    Args:
        limit: Maximum number of papers to scrape for this year (None = no limit)
    """
    print(f"Starting scrape for {conference.upper()} {year}...")
    if limit:
        print(f"  Limit: {limit} papers")
    
    # First try to get all papers at once using day=all
    url_all = f"{BASE_URL}{conference.upper()}{year}?day=all"
    
    try:
        response = requests.get(url_all, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Check if we actually got papers (look for ptitle elements)
        dt_elements = soup.find_all('dt', class_='ptitle')
        
        if len(dt_elements) > 0:
            # day=all works, use it
            print(f"  Using day=all for {conference.upper()} {year}")
            return scrape_day(url_all, year, "all", conference, download_pdfs, pdf_dir, limit)
        else:
            # day=all returned no papers, need to try individual days
            print(f"  day=all returned no papers, trying to find individual days...")
            
    except Exception as e:
        print(f"  day=all failed: {e}, trying to find individual days...")
    
    # If day=all doesn't work, try to scrape by individual days
    # First, get the main conference page to find available days
    main_url = f"{BASE_URL}{conference.upper()}{year}"
    
    try:
        response = requests.get(main_url, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find day links in the navigation (usually in <dd> tags or links with ?day= parameter)
        day_links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            if '?day=' in href and href not in day_links:
                # Extract the day parameter
                if 'day=' in href:
                    day_links.append(href)
        
        if day_links:
            print(f"  Found {len(day_links)} day(s) to scrape")
            all_papers = []
            for link in day_links:
                if limit and len(all_papers) >= limit:
                    print(f"  Reached limit of {limit} papers, stopping...")
                    break
                # Extract day value from the link
                day_param = link.split('day=')[1].split('&')[0] if '&' in link.split('day=')[1] else link.split('day=')[1]
                full_url = urljoin(BASE_URL, link)
                remaining_limit = limit - len(all_papers) if limit else None
                papers = scrape_day(full_url, year, day_param, conference, download_pdfs, pdf_dir, remaining_limit)
                all_papers.extend(papers)
            return all_papers
        else:
            print(f"  Warning: Could not find day links for {conference.upper()} {year}")
            # Last resort: try day=all anyway
            return scrape_day(url_all, year, "all", conference, download_pdfs, pdf_dir, limit)
            
    except Exception as e:
        print(f"  Error accessing main page: {e}")
        # Last resort: try day=all anyway
        return scrape_day(url_all, year, "all", conference, download_pdfs, pdf_dir, limit)

def scrape_day(url, year, day, conference, download_pdfs=False, pdf_dir="", limit=None):
    """
    Scrapes papers from a specific day/page.
    
    Args:
        limit: Maximum number of papers to scrape (None = no limit)
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
    
    # Apply limit if specified
    if limit and len(dt_elements) > limit:
        dt_elements = dt_elements[:limit]
        print(f"  Found {len(soup.find_all('dt', class_='ptitle'))} papers, limiting to {limit}.")
    else:
        print(f"  Found {len(dt_elements)} papers for {year} {day}.")
    
    for i, dt in enumerate(dt_elements):
        a_tag = dt.find('a')
        if not a_tag:
            continue
            
        title = a_tag.get_text(strip=True)
        title = clean_text(title)  # Clean illegal characters
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
  python scrape_cvf_limit.py --conference CVPR --start-year 2020 --end-year 2022
  
  # Scrape multiple conferences with limit
  python scrape_cvf_limit.py --conference CVPR ICCV --start-year 2021 --end-year 2023 --limit 100
  
  # Specify output and PDF directories
  python scrape_cvf_limit.py --conference CVPR --start-year 2020 --end-year 2022 --output-dir data --pdf-dir papers
  
  # Download PDFs with limit per year
  python scrape_cvf_limit.py --conference CVPR --start-year 2020 --end-year 2022 --download-pdf --limit 50
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
        default=2025,
        help='Start year (inclusive)'
    )
    
    parser.add_argument(
        '--end-year', '-e',
        type=int,
        default=2025,
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
    
    parser.add_argument(
        '--limit', '-l',
        type=int,
        default=None,
        help='Maximum number of papers to scrape per year (default: no limit)'
    )
    
    args = parser.parse_args()
    
    # Validate year range
    if args.start_year > args.end_year:
        parser.error(f"Start year ({args.start_year}) must be <= end year ({args.end_year})")
    
    # Validate limit
    if args.limit is not None and args.limit <= 0:
        parser.error(f"Limit must be a positive integer")
    
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
    
    # Check for existing progress
    all_papers = []
    papers_by_sheet = {}
    completed_sheets = set()
    
    if os.path.exists(output_file):
        print(f"Found existing file: {output_file}")
        print("Loading previous progress...")
        try:
            excel_file = pd.ExcelFile(output_file)
            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(output_file, sheet_name=sheet_name)
                
                # Validate sheet data
                is_valid = True
                validation_messages = []
                
                # Check if sheet is empty
                if df.empty:
                    validation_messages.append("Sheet is empty")
                    is_valid = False
                else:
                    # Check for required columns
                    required_columns = ["Conference", "Year", "Title", "Abstract", "URL", "PDF_URL"]
                    missing_columns = [col for col in required_columns if col not in df.columns]
                    if missing_columns:
                        validation_messages.append(f"Missing columns: {', '.join(missing_columns)}")
                        is_valid = False
                    
                    # Check for rows with empty critical fields (Title should not be empty)
                    empty_titles = df["Title"].isna().sum() if "Title" in df.columns else len(df)
                    if empty_titles > 0:
                        validation_messages.append(f"{empty_titles} rows with empty titles")
                        is_valid = False
                    
                    # Check for completely empty columns (excluding PDF_Path which might be empty)
                    for col in ["Conference", "Year", "Title", "URL"]:
                        if col in df.columns and df[col].isna().all():
                            validation_messages.append(f"Column '{col}' is completely empty")
                            is_valid = False
                
                if is_valid:
                    papers_list = df.to_dict('records')
                    papers_by_sheet[sheet_name] = papers_list
                    all_papers.extend(papers_list)
                    completed_sheets.add(sheet_name)
                    print(f"  ✓ {sheet_name}: {len(df)} papers (valid)")
                else:
                    print(f"  ✗ {sheet_name}: Invalid - {'; '.join(validation_messages)}")
                    print(f"    This sheet will be re-scraped")
            
            if completed_sheets:
                print(f"\nLoaded {len(completed_sheets)} valid sheets")
                print(f"Total papers loaded: {len(all_papers)}")
            else:
                print("\nNo valid sheets found, starting from scratch...")
            print()
        except Exception as e:
            print(f"Error loading existing file: {e}")
            print("Starting from scratch...")
            print()
    
    print(f"Configuration:")
    print(f"  Conferences: {', '.join(conferences)}")
    print(f"  Years: {args.start_year} - {args.end_year}")
    print(f"  Output directory: {args.output_dir}")
    print(f"  Output file: {output_file}")
    print(f"  Download PDFs: {args.download_pdf}")
    if args.download_pdf:
        print(f"  PDF directory: {args.pdf_dir}")
    if args.limit:
        print(f"  Limit per year: {args.limit} papers")
    print()
    
    for conference in conferences:
        for year in years:
            sheet_name = f"{conference}_{year}"
            
            # Skip if already completed
            if sheet_name in completed_sheets:
                print(f"Skipping {conference} {year} (already completed)")
                continue
            
            print(f"Starting {conference} {year}...")
            year_papers = scrape_year(year, conference, args.download_pdf, args.pdf_dir, args.limit)
            all_papers.extend(year_papers)
            
            # Organize papers by sheet name
            if sheet_name not in papers_by_sheet:
                papers_by_sheet[sheet_name] = []
            papers_by_sheet[sheet_name].extend(year_papers)
            
            print(f"Finished {conference} {year}. Total papers so far: {len(all_papers)}")
            
            # Save intermediate results with multiple sheets
            try:
                success = save_papers_to_excel(output_file, papers_by_sheet)
                if success:
                    print(f"Saved progress to {output_file}")
                    completed_sheets.add(sheet_name)
                else:
                    print(f"Failed to save progress!")
            except Exception as e:
                print(f"Error saving to Excel: {e}")
                print(f"Progress for {sheet_name} may be lost!")
            print()

    print("Scraping complete!")
    print(f"Total papers scraped: {len(all_papers)}")
    print(f"Sheets created: {', '.join(sorted(papers_by_sheet.keys()))}")
    print(f"Data saved to {output_file}")

if __name__ == "__main__":
    main()
