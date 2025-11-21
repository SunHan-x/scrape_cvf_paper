"""
Example: How to customize Excel column formatting

This file shows how to use excel_formatter.py to customize
the appearance of your Excel output files.
"""

from excel_formatter import create_custom_column_config, save_papers_to_excel

# Example 1: Use default configuration
# The default config is already applied automatically

# Example 2: Customize specific columns
custom_config = create_custom_column_config({
    "Title": {
        "width": 80,           # Wider column for titles
        "wrap_text": True,     # Enable text wrapping
        "alignment": "left"    # Left align text
    },
    "Abstract": {
        "width": 100,          # Even wider for abstracts
        "wrap_text": True,
        "alignment": "justify" # Justify text
    },
    "Year": {
        "width": 10,
        "wrap_text": False,
        "alignment": "center"
    }
})

# Example 3: Complete custom configuration
complete_custom_config = {
    "Conference": {
        "width": 15,
        "wrap_text": False,
        "alignment": "center"
    },
    "Year": {
        "width": 8,
        "wrap_text": False,
        "alignment": "center"
    },
    "Title": {
        "width": 70,
        "wrap_text": True,
        "alignment": "left"
    },
    "Abstract": {
        "width": 90,
        "wrap_text": True,
        "alignment": "left"
    },
    "URL": {
        "width": 45,
        "wrap_text": False,
        "alignment": "left"
    },
    "PDF_URL": {
        "width": 45,
        "wrap_text": False,
        "alignment": "left"
    },
    "PDF_Path": {
        "width": 55,
        "wrap_text": False,
        "alignment": "left"
    }
}

# How to use in your script:
"""
from excel_formatter import save_papers_to_excel, create_custom_column_config

# Your paper data
papers_by_sheet = {
    "CVPR_2020": [
        {"Conference": "CVPR", "Year": 2020, "Title": "...", ...},
        {"Conference": "CVPR", "Year": 2020, "Title": "...", ...}
    ]
}

# Option 1: Use default formatting (automatic)
save_papers_to_excel("output.xlsx", papers_by_sheet)

# Option 2: Use custom formatting
custom_config = create_custom_column_config({
    "Title": {"width": 80, "wrap_text": True}
})
save_papers_to_excel("output.xlsx", papers_by_sheet, custom_config)

# Option 3: Use completely custom configuration
save_papers_to_excel("output.xlsx", papers_by_sheet, complete_custom_config)
"""

# Alignment options available:
# - "left"        : Align text to the left
# - "center"      : Center text
# - "right"       : Align text to the right
# - "justify"     : Justify text (distribute evenly)
# - "distributed" : Distribute text with spacing

print("Excel formatting examples loaded!")
print("\nDefault column widths:")
from excel_formatter import DEFAULT_COLUMN_CONFIG
for col, config in DEFAULT_COLUMN_CONFIG.items():
    print(f"  {col:15} width={config['width']:3} wrap={config['wrap_text']!s:5} align={config['alignment']:10}")
