import pdfplumber
import json

pdf_path = r"C:\Users\angit\OneDrive\Documents\closing stock 07-03-2026.pdf"

with pdfplumber.open(pdf_path) as pdf:
    first_page = pdf.pages[0]
    tables = first_page.extract_tables()
    
    if tables and len(tables) > 0:
        table = tables[0]
        with open("pdf_out.txt", "w", encoding="utf-8") as f:
            f.write("COLUMNS:\n")
            for col in table[0]:
                if col:
                    f.write(repr(str(col).replace('\n', ' ')) + "\n")
            
            f.write("\nFIRST 2 DATA ROWS:\n")
            for row in table[1:3]:
                f.write(str([str(r).replace('\n', ' ') for r in row]) + "\n")
