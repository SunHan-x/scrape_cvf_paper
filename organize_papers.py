import pandas as pd
import shutil
import os
import json
import argparse
from pathlib import Path

def sanitize_filename(filename):
    """
    Sanitize filename to remove invalid characters.
    """
    # Remove invalid characters for file/folder names
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '')
    # Remove leading/trailing spaces and dots
    filename = filename.strip('. ')
    # Limit length
    return filename[:200]

def copy_pdf(pdf_path_in_xlsx, save_path, pdf_dir='pdf'):
    """
    Copy PDF file from pdf directory to specified path.
    """
    try:
        if os.path.exists(save_path):
            print(f"    PDF already exists: {os.path.basename(save_path)}")
            return True
        
        # Check if PDF_Path column has a value
        if pdf_path_in_xlsx and os.path.exists(pdf_path_in_xlsx):
            # Use the path directly from xlsx
            source_path = pdf_path_in_xlsx
        else:
            # If not found, return False
            return False
        
        # Copy the file
        shutil.copy2(source_path, save_path)
        print(f"    Copied: {os.path.basename(save_path)}")
        return True
        
    except Exception as e:
        print(f"    Error copying PDF: {e}")
        return False

def create_paper_metadata(row):
    """
    Create metadata dictionary from DataFrame row.
    """
    metadata = {
        "conference": row.get("Conference", ""),
        "year": int(row.get("Year", 0)),
        "title": row.get("Title", ""),
        "abstract": row.get("Abstract", ""),
        "url": row.get("URL", ""),
        "pdf_url": row.get("PDF_URL", "")
    }
    return metadata

def organize_papers(xlsx_file, output_dir, copy_pdfs=True, pdf_dir='pdf'):
    """
    Organize papers from xlsx file into structured directory.
    
    Structure:
    output_dir/
    ├─CVPR/
    │  ├─2020/
    │  │  ├─paper_title_1/
    │  │  │  ├─paper_title_1.json
    │  │  │  └─paper_title_1.pdf
    """
    print(f"Reading Excel file: {xlsx_file}")
    
    # Read all sheets from Excel file
    excel_file = pd.ExcelFile(xlsx_file)
    sheet_names = excel_file.sheet_names
    
    print(f"Found {len(sheet_names)} sheets: {', '.join(sheet_names)}")
    print()
    
    total_papers = 0
    total_copied = 0
    
    for sheet_name in sheet_names:
        print(f"Processing sheet: {sheet_name}")
        df = pd.read_excel(xlsx_file, sheet_name=sheet_name)
        
        if df.empty:
            print(f"  Sheet is empty, skipping...")
            continue
        
        print(f"  Found {len(df)} papers")
        
        for idx, row in df.iterrows():
            conference = row.get("Conference", "")
            year = str(int(row.get("Year", 0)))
            title = row.get("Title", "")
            pdf_path_in_xlsx = row.get("PDF_Path", "")
            
            if not title:
                print(f"  [{idx+1}/{len(df)}] Skipping paper with no title")
                continue
            
            # Sanitize paper title for folder/file name
            safe_title = sanitize_filename(title)
            
            # Create directory structure: output_dir/CONFERENCE/YEAR/PAPER_TITLE/
            paper_dir = os.path.join(output_dir, conference, year, safe_title)
            os.makedirs(paper_dir, exist_ok=True)
            
            # Create JSON metadata file
            json_path = os.path.join(paper_dir, f"{safe_title}.json")
            metadata = create_paper_metadata(row)
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            print(f"  [{idx+1}/{len(df)}] {safe_title[:50]}...")
            print(f"    Created metadata: {json_path}")
            
            # Copy PDF if requested and path is available
            if copy_pdfs and pdf_path_in_xlsx:
                pdf_path = os.path.join(paper_dir, f"{safe_title}.pdf")
                if copy_pdf(pdf_path_in_xlsx, pdf_path, pdf_dir):
                    total_copied += 1
            elif not pdf_path_in_xlsx:
                print(f"    No PDF available")
            
            total_papers += 1
        
        print()
    
    print("="*60)
    print(f"Organization complete!")
    print(f"Total papers processed: {total_papers}")
    if copy_pdfs:
        print(f"PDFs copied: {total_copied}")
    print(f"Output directory: {output_dir}")

def parse_arguments():
    """
    Parse command line arguments.
    """
    parser = argparse.ArgumentParser(
        description='Organize papers from Excel file into structured directories',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Organize papers with PDF copying
  python organize_papers.py --input xlsx/CVPR_ICCV_2020_2021.xlsx --output PAPERS
  
  # Organize without copying PDFs
  python organize_papers.py --input xlsx/CVPR_ICCV_2020_2021.xlsx --output PAPERS --no-copy
  
  # Custom output directory
  python organize_papers.py --input my_papers.xlsx --output my_organized_papers
        """
    )
    
    parser.add_argument(
        '--input', '-i',
        type=str,
        required=True,
        help='Path to input Excel file'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='PAPERS',
        help='Output directory for organized papers (default: PAPERS)'
    )
    
    parser.add_argument(
        '--no-copy',
        action='store_true',
        help='Do not copy PDF files (only create JSON metadata)'
    )
    
    parser.add_argument(
        '--pdf-dir',
        type=str,
        default='pdf',
        help='Directory where PDF files are stored (default: pdf)'
    )
    
    args = parser.parse_args()
    
    # Validate input file exists
    if not os.path.exists(args.input):
        parser.error(f"Input file does not exist: {args.input}")
    
    return args

def main():
    args = parse_arguments()
    
    print("="*60)
    print("Paper Organization Tool")
    print("="*60)
    print(f"Input file: {args.input}")
    print(f"Output directory: {args.output}")
    print(f"Copy PDFs: {not args.no_copy}")
    if not args.no_copy:
        print(f"PDF source directory: {args.pdf_dir}")
    print("="*60)
    print()
    
    organize_papers(
        xlsx_file=args.input,
        output_dir=args.output,
        copy_pdfs=not args.no_copy,
        pdf_dir=args.pdf_dir
    )

if __name__ == "__main__":
    main()
