import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sangi_hospital.settings')
django.setup()

from patients.models import ServiceMaster

def run_import():
    try:
        import openpyxl
    except ImportError:
        print("❌ Error: 'openpyxl' is not installed. Run 'pip install openpyxl' first.")
        return

    # Clear existing data so we don't get duplicates
    ServiceMaster.objects.all().delete()
    
    filepath = './data/SANGIESIC.xlsx'
    
    # Check if the file exists
    if not os.path.exists(filepath):
        print(f"❌ Error: Could not find '{filepath}'")
        return

    print(f"📂 Opening Excel file: {filepath}...")
    # Load the workbook (data_only=True means we get calculated values, not formulas)
    wb = openpyxl.load_workbook(filepath, data_only=True)
    
    count = 0

    # Loop through every sheet in the Excel file
    for sheet_name in wb.sheetnames:
        sheet = wb[sheet_name]
        print(f"  ➡️ Reading sheet: {sheet_name}...")

        # 1. Find the header row (the row that says 'Description', 'Code', 'Rate', etc.)
        header_row_idx = None
        headers = []
        
        # iter_rows gives us the rows. values_only gives us just the text.
        for row_idx, row in enumerate(sheet.iter_rows(values_only=True)):
            # If the row has data and contains 'Description'
            if row and 'Description' in [str(c).strip() for c in row if c]:
                header_row_idx = row_idx
                headers = [str(c).strip() if c else '' for c in row]
                break

        if header_row_idx is None:
            print(f"     ⚠️ Warning: Could not find 'Description' header in sheet '{sheet_name}'. Skipping.")
            continue

        # 2. Extract the actual data starting from the row AFTER the header
        # (min_row is 1-indexed in openpyxl, so we add 2 to the 0-indexed header_row_idx)
        for row in sheet.iter_rows(min_row=header_row_idx + 2, values_only=True):
            if not row:
                continue

            # Zip pairs the headers with the row values into a dictionary
            row_dict = dict(zip(headers, row))

            # Safely get description
            desc = str(row_dict.get('Description', '')).strip()
            if not desc or desc == 'None':
                continue

            # Safely get rate
            raw_rate = row_dict.get('Rate', 0)
            try:
                rate = float(raw_rate) if raw_rate else 0.0
            except (ValueError, TypeError):
                rate = 0.0

            # Safely get code
            code = str(row_dict.get('Code', '')).strip()
            if code == 'None': 
                code = ''

            # Safely get category (Fallback to the sheet name if the column is empty)
            cat = str(row_dict.get('Type of Service', '')).strip().upper()
            if not cat or cat == 'NONE': 
                cat = sheet_name.upper()

            # Create the database record
            ServiceMaster.objects.create(
                category=cat,
                description=desc,
                code=code,
                rate=rate
            )
            count += 1
            
    print(f"\n🎉 BOOM! {count} services successfully imported from Excel into PostgreSQL!")

if __name__ == '__main__':
    run_import()