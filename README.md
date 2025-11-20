# CVF Paper Scraper

A Python tool for bulk scraping computer vision conference papers from the CVF (Computer Vision Foundation) website : https://openaccess.thecvf.com/. Supports scraping paper metadata (title, abstract, link) and PDF files.

## Supported meetings

- **CVPR** - IEEE/CVF Conference on Computer Vision and Pattern Recognition
- **ICCV** - IEEE/CVF International Conference on Computer Vision
- **WACV** - IEEE/CVF Winter Conference on Applications of Computer Vision
- **ECCV** - European Conference on Computer Vision
- **ACCV** - Asian Conference on Computer Vision

## Quickstart

```bash
pip install -r requirements.txt
```

### Basic usage

```bash
# Scrape CVPR paper metadata for 2020-2022
python scrape_cvpr.py --conference CVPR --start-year 2020 --end-year 2022
```

### Scrape multiple meetings

```bash
# Scrape both CVPR and ICCV papers 2021-2023
python scrape_cvpr.py -c CVPR ICCV -s 2021 -e 2023
```

### Download PDF files

```bash
# Scrape the metadata and download the PDF
python scrape_cvpr.py -c CVPR -s 2020 -e 2022 --download-pdf
```

### Customize the output directory

```bash
# Specify the save directory for Excel and PDF
python scrape_cvpr.py -c CVPR -s 2020 -e 2022 --output-dir mydata --pdf-dir mypapers -dp
```

### Full example

```bash
# Scrape multiple meetings, download PDFs, customize the catalog
python scrape_cvpr.py -c CVPR ICCV ECCV -s 2020 -e 2023 -dp -od mydata -pd mypapers
```

## Command-line arguments

| parameter | abbreviation | Instructions | default | necessity |
|------|------|------|--------|------|
| `--conference` | `-c` | Multiple meeting names, which can be specified to capture | `-` | yes |
| `--start-year` | `-s` | Starting year (inclusive) | `2025` | no |
| `--end-year` | `-e` | End year (inclusive) | `2025` | no |
| `--output-dir` | `-od` | Excel file save directory | `xlsx` | no |
| `--download-pdf` | `-dp` | Whether to download PDF files | `False` | no |
| `--pdf-dir` | `-pd` | PDF file saving directory (requires '--download-pdf') | `pdf` | 否 |