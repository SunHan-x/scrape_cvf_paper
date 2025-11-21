import os
import re
import argparse
from pathlib import Path
import PyPDF2
import pandas as pd

# Common code repository patterns
CODE_PATTERNS = [
    r'github\.com/[\w\-\.]+/[\w\-\.]+',
    r'gitlab\.com/[\w\-\.]+/[\w\-\.]+',
    r'bitbucket\.org/[\w\-\.]+/[\w\-\.]+',
    r'gitee\.com/[\w\-\.]+/[\w\-\.]+',
    r'code\.google\.com/[\w\-\.]+/[\w\-\.]+',
    r'sourceforge\.net/projects/[\w\-\.]+',
    r'huggingface\.co/[\w\-\.]+',
]

def extract_text_from_pdf(pdf_path):
    """
    Extract text content from a PDF file.
    """
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
            return text
    except Exception as e:
        print(f"Error reading {pdf_path}: {e}")
        return ""

def find_code_links(text):
    """
    Find code repository links in text.
    Returns a list of unique URLs.
    """
    links = []
    for pattern in CODE_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        links.extend(matches)
    
    # Clean up and deduplicate
    clean_links = []
    seen = set()
    for link in links:
        # Remove trailing punctuation
        link = link.rstrip('.,;:)')
        # Add https:// if not present
        if not link.startswith('http'):
            full_link = 'https://' + link
        else:
            full_link = link
        
        if full_link.lower() not in seen:
            seen.add(full_link.lower())
            clean_links.append(full_link)
    
    return clean_links

def scan_directory(directory, recursive=True, output_file=None):
    """
    Scan directory for PDF files and extract code links.
    """
    pdf_files = []
    
    if recursive:
        # Recursively find all PDF files
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.lower().endswith('.pdf'):
                    pdf_files.append(os.path.join(root, file))
    else:
        # Only scan current directory
        pdf_files = [os.path.join(directory, f) for f in os.listdir(directory) 
                     if f.lower().endswith('.pdf') and os.path.isfile(os.path.join(directory, f))]
    
    print(f"Found {len(pdf_files)} PDF files")
    print()
    
    results = []
    papers_with_code = 0
    
    for idx, pdf_path in enumerate(pdf_files, 1):
        pdf_name = os.path.basename(pdf_path)
        rel_path = os.path.relpath(pdf_path, directory)
        
        print(f"[{idx}/{len(pdf_files)}] Scanning: {rel_path[:60]}...")
        
        text = extract_text_from_pdf(pdf_path)
        if not text:
            print(f"  ⚠ Could not extract text")
            results.append({
                'pdf_path': rel_path,
                'pdf_name': pdf_name,
                'has_code': False,
                'code_links': '',
                'link_count': 0,
                'status': 'extraction_failed'
            })
            continue
        
        links = find_code_links(text)
        
        if links:
            papers_with_code += 1
            print(f"  ✓ Found {len(links)} code link(s):")
            for link in links:
                print(f"    - {link}")
            
            results.append({
                'pdf_path': rel_path,
                'pdf_name': pdf_name,
                'has_code': True,
                'code_links': '; '.join(links),
                'link_count': len(links),
                'status': 'success'
            })
        else:
            print(f"  ✗ No code links found")
            results.append({
                'pdf_path': rel_path,
                'pdf_name': pdf_name,
                'has_code': False,
                'code_links': '',
                'link_count': 0,
                'status': 'no_links'
            })
    
    print()
    print("="*60)
    print(f"Scan complete!")
    print(f"Total PDFs scanned: {len(pdf_files)}")
    print(f"Papers with code links: {papers_with_code} ({papers_with_code/len(pdf_files)*100:.1f}%)")
    print(f"Papers without code links: {len(pdf_files) - papers_with_code}")
    
    # Save results to CSV/Excel
    if output_file:
        df = pd.DataFrame(results)
        
        if output_file.endswith('.xlsx'):
            df.to_excel(output_file, index=False, engine='openpyxl')
        else:
            df.to_csv(output_file, index=False, encoding='utf-8-sig')
        
        print(f"\nResults saved to: {output_file}")
    
    return results

def parse_arguments():
    """
    Parse command line arguments.
    """
    parser = argparse.ArgumentParser(
        description='Scan PDF files for source code repository links',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scan pdf directory recursively
  python extract_code_links.py --dir pdf
  
  # Scan specific directory without recursion
  python extract_code_links.py --dir CVPR_pdf --no-recursive
  
  # Save results to Excel
  python extract_code_links.py --dir pdf --output code_links.xlsx
  
  # Save results to CSV
  python extract_code_links.py --dir pdf --output code_links.csv
        """
    )
    
    parser.add_argument(
        '--dir', '-d',
        type=str,
        required=True,
        help='Directory containing PDF files'
    )
    
    parser.add_argument(
        '--no-recursive',
        action='store_true',
        help='Do not scan subdirectories'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='code_links.csv',
        help='Output file for results (CSV or Excel, default: code_links.csv)'
    )
    
    args = parser.parse_args()
    
    # Validate directory exists
    if not os.path.exists(args.dir):
        parser.error(f"Directory does not exist: {args.dir}")
    
    if not os.path.isdir(args.dir):
        parser.error(f"Not a directory: {args.dir}")
    
    return args

def main():
    args = parse_arguments()
    
    print("="*60)
    print("PDF Code Link Extractor")
    print("="*60)
    print(f"Directory: {args.dir}")
    print(f"Recursive: {not args.no_recursive}")
    print(f"Output file: {args.output}")
    print("="*60)
    print()
    
    scan_directory(
        directory=args.dir,
        recursive=not args.no_recursive,
        output_file=args.output
    )

if __name__ == "__main__":
    main()
