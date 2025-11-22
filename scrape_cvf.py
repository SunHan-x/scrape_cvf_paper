import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import os
import json
import argparse
from urllib.parse import urljoin
from datetime import datetime
import re

# Base URL
BASE_URL = "https://openaccess.thecvf.com/"

# Global list to track failed papers
failed_papers = []

def sanitize_filename(filename):
    """
    Sanitize filename by removing invalid characters.
    """
    # Remove invalid characters for Windows/Linux filenames
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    # Replace multiple spaces with single space
    filename = re.sub(r'\s+', ' ', filename)
    # Limit length
    filename = filename.strip()[:200]
    return filename

def get_paper_details(paper_url):
    """
    Fetches the abstract, authors, and PDF URL from the paper's detail page.
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
        
        # Extract Authors
        authors = []
        authors_div = soup.find('div', id='authors')
        if authors_div:
            # Authors are usually in <i> tags or <b> tags
            author_tags = authors_div.find_all(['i', 'b'])
            for tag in author_tags:
                author_name = tag.get_text(strip=True)
                if author_name and author_name not in authors:
                    authors.append(author_name)
        
        # If no authors found, try alternative method
        if not authors:
            # Sometimes authors are just text in the div
            if authors_div:
                text = authors_div.get_text()
                # Split by common delimiters
                potential_authors = re.split(r'[,;]', text)
                for author in potential_authors:
                    author = author.strip()
                    if author and len(author) > 2:
                        authors.append(author)
        
        authors_str = "; ".join(authors) if authors else ""
        
        # Extract PDF URL
        pdf_url = ""
        # Look for PDF link (usually an <a> tag with href ending in .pdf)
        pdf_link = soup.find('a', href=lambda x: x and x.endswith('.pdf'))
        if pdf_link:
            pdf_url = urljoin(BASE_URL, pdf_link['href'])
        
        return authors_str, abstract, pdf_url, None

    except Exception as e:
        error_msg = f"Error fetching details: {str(e)}"
        print(f"    {error_msg}")
        return "", "", "", error_msg

def download_pdf(pdf_url, save_dir, filename):
    """
    Downloads a PDF file from the given URL.
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(save_dir, exist_ok=True)
        
        # Sanitize filename
        safe_filename = sanitize_filename(filename)
        filepath = os.path.join(save_dir, "paper.pdf")
        
        # Skip if file already exists
        if os.path.exists(filepath):
            print(f"    PDF already exists: {safe_filename}")
            return filepath, None
        
        # Download PDF
        response = requests.get(pdf_url, timeout=30, stream=True)
        response.raise_for_status()
        
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"    Downloaded PDF: {safe_filename}")
        return filepath, None
        
    except Exception as e:
        error_msg = f"Error downloading PDF: {str(e)}"
        print(f"    {error_msg}")
        return "", error_msg

def retry_failed_papers(failed_list, year_dir, conference, year):
    """
    Retry fetching details for failed papers.
    Returns updated list of papers and still-failed papers.
    """
    print(f"\n  === Retrying {len(failed_list)} failed papers for {year} ===")
    
    recovered_papers = []
    still_failed = []
    
    for i, failed_item in enumerate(failed_list):
        print(f"  [Retry {i+1}/{len(failed_list)}] {failed_item['title'][:50]}...")
        
        title = failed_item['title']
        full_link = failed_item['url']
        
        # Retry fetching details
        authors, abstract, pdf_url, error = get_paper_details(full_link)
        
        has_error = False
        error_details = []
        
        if error:
            has_error = True
            error_details.append(f"Details fetch failed: {error}")
        
        # Create paper directory
        safe_title = sanitize_filename(title)
        paper_dir = os.path.join(year_dir, safe_title)
        
        # Prepare paper info
        paper_info = {
            "Conference": conference.upper(),
            "Year": year,
            "Title": title,
            "Authors": authors,
            "Abstract": abstract,
            "URL": full_link,
            "PDF_URL": pdf_url
        }
        
        # Save paper data and create github_links.json
        if not save_paper_data(paper_info, paper_dir):
            has_error = True
            error_details.append("Failed to save paper_data.json")
        
        # Download PDF if available
        pdf_error = None
        if pdf_url:
            _, pdf_error = download_pdf(pdf_url, paper_dir, title)
            if pdf_error:
                has_error = True
                error_details.append(pdf_error)
        else:
            if not error:  # Only mark as error if detail fetch succeeded but no PDF URL
                error_details.append("No PDF URL found")
        
        if has_error:
            still_failed.append({
                "conference": conference.upper(),
                "year": year,
                "title": title,
                "url": full_link,
                "errors": error_details,
                "retry_attempt": True
            })
        else:
            recovered_papers.append({
                "Conference": conference.upper(),
                "Year": year,
                "Title": title,
                "Authors": authors,
                "Abstract": abstract,
                "URL": full_link,
                "PDF_URL": pdf_url
            })
        
        time.sleep(0.5)
    
    print(f"  Retry complete: {len(recovered_papers)} recovered, {len(still_failed)} still failed")
    return recovered_papers, still_failed

def save_paper_data(paper_info, paper_dir):
    """
    Save paper data as JSON file and create empty github_links.json
    """
    try:
        os.makedirs(paper_dir, exist_ok=True)
        
        # Save paper_data.json
        paper_data_path = os.path.join(paper_dir, "paper_data.json")
        with open(paper_data_path, 'w', encoding='utf-8') as f:
            json.dump(paper_info, f, ensure_ascii=False, indent=2)
        
        # Create empty github_links.json
        github_links_path = os.path.join(paper_dir, "github_links.json")
        if not os.path.exists(github_links_path):
            with open(github_links_path, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=2)
        
        return True
    except Exception as e:
        print(f"    Error saving paper data: {e}")
        return False

def save_failure_report(failed_list, base_dir, conference, start_year, end_year):
    """
    Save a report of all failed papers.
    """
    if not failed_list:
        print("\n✓ No failures to report!")
        return
    
    report_file = os.path.join(base_dir, f"failure_report_{conference}_{start_year}_{end_year}.json")
    
    report = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "conference": conference,
        "year_range": f"{start_year}-{end_year}",
        "total_failures": len(failed_list),
        "failures": failed_list
    }
    
    try:
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\n⚠ Failure report saved to: {report_file}")
        print(f"  Total failures: {len(failed_list)}")
        
        # Print summary by year
        year_counts = {}
        for item in failed_list:
            yr = item['year']
            year_counts[yr] = year_counts.get(yr, 0) + 1
        
        print("  Failures by year:")
        for yr in sorted(year_counts.keys()):
            print(f"    {yr}: {year_counts[yr]} papers")
            
    except Exception as e:
        print(f"\n✗ Error saving failure report: {e}")

def scrape_year(year, conference, base_dir="CVPR"):
    """
    Scrapes all papers for a specific year and conference.
    """
    print(f"Starting scrape for {conference.upper()} {year}...")
    
    # Create year directory
    year_dir = os.path.join(base_dir, str(year))
    os.makedirs(year_dir, exist_ok=True)
    
    # Track failed papers for this year
    year_failed_papers = []
    
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
            all_papers = scrape_day(url_all, year, "all", conference, year_dir, year_failed_papers)
        else:
            # day=all returned no papers, need to try individual days
            print(f"  day=all returned no papers, trying to find individual days...")
            all_papers = []
            all_papers.extend(scrape_individual_days(year, conference, year_dir, year_failed_papers))
            
    except Exception as e:
        print(f"  day=all failed: {e}, trying to find individual days...")
        all_papers = []
        all_papers.extend(scrape_individual_days(year, conference, year_dir, year_failed_papers))
    
    # Retry failed papers
    if year_failed_papers:
        recovered_papers, still_failed = retry_failed_papers(year_failed_papers, year_dir, conference, year)
        all_papers.extend(recovered_papers)
        
        # Add still-failed papers to global failed_papers list
        failed_papers.extend(still_failed)
    
    return all_papers

def scrape_individual_days(year, conference, year_dir, year_failed_papers):
    """
    Helper function to scrape individual days when day=all doesn't work.
    """
    main_url = f"{BASE_URL}{conference.upper()}{year}"
    
    try:
        response = requests.get(main_url, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find day links in the navigation
        day_links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            if '?day=' in href and href not in day_links:
                day_links.append(href)
        
        if day_links:
            print(f"  Found {len(day_links)} day(s) to scrape")
            all_papers = []
            for link in day_links:
                day_param = link.split('day=')[1].split('&')[0] if '&' in link.split('day=')[1] else link.split('day=')[1]
                full_url = urljoin(BASE_URL, link)
                papers = scrape_day(full_url, year, day_param, conference, year_dir, year_failed_papers)
                all_papers.extend(papers)
            return all_papers
        else:
            print(f"  Warning: Could not find day links for {conference.upper()} {year}")
            url_all = f"{BASE_URL}{conference.upper()}{year}?day=all"
            return scrape_day(url_all, year, "all", conference, year_dir, year_failed_papers)
            
    except Exception as e:
        print(f"  Error accessing main page: {e}")
        url_all = f"{BASE_URL}{conference.upper()}{year}?day=all"
        return scrape_day(url_all, year, "all", conference, year_dir, year_failed_papers)

def scrape_day(url, year, day, conference, year_dir, year_failed_papers):
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
        
        print(f"  [{i+1}/{len(dt_elements)}] Fetching details for: {title[:50]}...")
        authors, abstract, pdf_url, error = get_paper_details(full_link)
        
        has_error = False
        error_details = []
        
        if error:
            has_error = True
            error_details.append(f"Details fetch failed: {error}")
        
        # Create paper directory
        safe_title = sanitize_filename(title)
        paper_dir = os.path.join(year_dir, safe_title)
        
        # Prepare paper info
        paper_info = {
            "Conference": conference.upper(),
            "Year": year,
            "Title": title,
            "Authors": authors,
            "Abstract": abstract,
            "URL": full_link,
            "PDF_URL": pdf_url
        }
        
        # Save paper data and create github_links.json
        if not save_paper_data(paper_info, paper_dir):
            has_error = True
            error_details.append("Failed to save paper_data.json")
        
        # Download PDF if available
        pdf_error = None
        if pdf_url:
            _, pdf_error = download_pdf(pdf_url, paper_dir, title)
            if pdf_error:
                has_error = True
                error_details.append(pdf_error)
        else:
            if not error:  # Only mark as warning if detail fetch succeeded but no PDF URL
                print(f"    Warning: No PDF URL found for this paper")
        
        # Track failures
        if has_error:
            year_failed_papers.append({
                "conference": conference.upper(),
                "year": year,
                "title": title,
                "url": full_link,
                "errors": error_details,
                "retry_attempt": False
            })
            print(f"    ⚠ Paper had errors, will retry later")
        
        papers_data.append({
            "Conference": conference.upper(),
            "Year": year,
            "Title": title,
            "Authors": authors,
            "Abstract": abstract,
            "URL": full_link,
            "PDF_URL": pdf_url
        })
        
        # Sleep to be polite
        time.sleep(0.5)

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
  # Scrape CVPR papers from 2013 to 2025
  python scrape_cvf.py --conference CVPR --start-year 2013 --end-year 2025
  
  # Scrape CVPR papers from 2020 to 2022
  python scrape_cvf.py --conference CVPR --start-year 2020 --end-year 2022
  
  # Specify base directory
  python scrape_cvf.py --conference CVPR --start-year 2013 --end-year 2025 --base-dir data
        """
    )
    
    parser.add_argument(
        '--conference', '-c',
        type=str,
        choices=['CVPR', 'ICCV', 'WACV', 'ECCV', 'ACCV'],
        default='CVPR',
        help='Conference to scrape (default: CVPR)'
    )
    
    parser.add_argument(
        '--start-year', '-s',
        type=int,
        default=2013,
        help='Start year (inclusive, default: 2013)'
    )
    
    parser.add_argument(
        '--end-year', '-e',
        type=int,
        default=2025,
        help='End year (inclusive, default: 2025)'
    )
    
    parser.add_argument(
        '--base-dir', '-bd',
        type=str,
        default='CVPR',
        help='Base directory to save papers (default: CVPR)'
    )
    
    args = parser.parse_args()
    
    # Validate year range
    if args.start_year > args.end_year:
        parser.error(f"Start year ({args.start_year}) must be <= end year ({args.end_year})")
    
    return args

def main():
    args = parse_arguments()
    
    conference = args.conference
    years = list(range(args.start_year, args.end_year + 1))
    base_dir = args.base_dir
    
    # Clear global failed_papers list
    global failed_papers
    failed_papers = []
    
    # Create base directory if it doesn't exist
    os.makedirs(base_dir, exist_ok=True)
    
    # Generate Excel filename
    excel_file = os.path.join(base_dir, f"CVPR_{args.start_year}_{args.end_year}.xlsx")
    
    print(f"Configuration:")
    print(f"  Conference: {conference}")
    print(f"  Years: {args.start_year} - {args.end_year}")
    print(f"  Base directory: {base_dir}")
    print(f"  Excel file: {excel_file}")
    print()
    
    all_papers = []
    papers_by_year = {}  # Dictionary to organize papers by year
    
    for year in years:
        year_papers = scrape_year(year, conference, base_dir)
        all_papers.extend(year_papers)
        
        # Organize papers by year for Excel sheets
        papers_by_year[year] = year_papers
        
        print(f"Finished {conference} {year}. Total papers: {len(year_papers)}")
        
        # Save to Excel with multiple sheets (one per year)
        try:
            with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
                for yr, papers in papers_by_year.items():
                    if papers:  # Only create sheet if there are papers
                        df = pd.DataFrame(papers)
                        # Reorder columns
                        column_order = ["Conference", "Year", "Title", "Authors", "Abstract", "URL", "PDF_URL"]
                        df = df[column_order]
                        df.to_excel(writer, sheet_name=str(yr), index=False)
            print(f"Saved progress to {excel_file}")
        except Exception as e:
            print(f"Error saving Excel file: {e}")
        print()

    print("\n" + "="*70)
    print("Scraping complete!")
    print("="*70)
    print(f"Total papers scraped: {len(all_papers)}")
    print(f"Sheets created: {', '.join(str(y) for y in papers_by_year.keys())}")
    print(f"Data saved to {excel_file}")
    print(f"Papers organized in directory structure under: {base_dir}/")
    
    # Save failure report if there are any failures
    if failed_papers:
        save_failure_report(failed_papers, base_dir, conference, args.start_year, args.end_year)
    else:
        print("\n✓ All papers scraped successfully with no failures!")

if __name__ == "__main__":
    main()