from fpdf import FPDF
from datetime import datetime

class InvoicePDF(FPDF):
    def header(self):
        # Title
        self.set_font('Arial', 'B', 20)
        self.set_text_color(50, 50, 50)
        self.cell(0, 10, 'INVOICE', 0, 1, 'L')
        self.ln(2)
        self.set_draw_color(0, 0, 0)
        self.line(10, 22, 200, 22)
        self.ln(10)
        
        # Company Name and Logo Area
        self.set_font('Arial', 'B', 16)
        self.set_text_color(231, 76, 60)  # Reddish like Escala Solutions logo
        self.cell(0, 10, 'escala solutions', 0, 1, 'C')
        self.ln(5)

    def section_title(self, title):
        self.set_font('Arial', 'B', 14)
        self.set_text_color(50, 50, 50)
        self.cell(0, 10, title, 0, 1, 'L')
        self.ln(2)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def create_invoice(client_name: str, client_address: str, items: list, tax_rate: float, due_date: str):
    pdf = InvoicePDF()
    pdf.add_page()
    
    # 1. FROM - COMPANY INFO
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 8, 'FROM:', 0, 1, 'L')
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 6, 'Escala Solutions', 0, 1, 'L')
    pdf.set_font('Arial', '', 10)
    pdf.multi_cell(0, 5, 'Business Number: 78804 5417 RT 0001\n320 Sedgewood Street\nKitchener, Ontario, N2P0J6\nCanada\nEmail: igorgomides.ca@gmail.com\nPhone: (519) 502-8015', 0, 'L')
    pdf.ln(5)

    # 2. INVOICE DETAILS
    pdf.section_title('Invoice Details')
    
    # Table for Invoice Details
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(60, 8, 'Field', 1, 0, 'L', True)
    pdf.cell(130, 8, 'Details', 1, 1, 'L', True)
    
    pdf.set_font('Arial', '', 10)
    now = datetime.now()
    invoice_number = f'INV-{now.strftime("%Y%m%d-%H%M")}'
    issue_date = now.strftime('%B %d, %Y')
    
    details = [
        ('Invoice Number:', invoice_number),
        ('Issue Date:', issue_date),
        ('Due Date:', due_date),
        ('Currency:', 'CAD')
    ]
    for field, detail in details:
        pdf.cell(60, 8, field, 1, 0, 'L')
        pdf.cell(130, 8, detail, 1, 1, 'L')
    pdf.ln(10)

    # 3. BILLED TO
    pdf.section_title('Bill To')
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 6, client_name, 0, 1, 'L')
    pdf.set_font('Arial', '', 10)
    pdf.multi_cell(0, 5, client_address, 0, 'L')
    pdf.ln(10)

    # 4. LINE ITEMS
    pdf.section_title('Line Items')
    
    # Table for Items
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(80, 8, 'Description', 1, 0, 'L', True)
    pdf.cell(25, 8, 'Quantity', 1, 0, 'C', True)
    pdf.cell(30, 8, 'Unit Price', 1, 0, 'C', True)
    pdf.cell(35, 8, 'Total (CAD)', 1, 1, 'C', True)
    
    pdf.set_font('Arial', '', 10)
    subtotal = 0.0
    for item in items:
        desc = item['desc'][:40]
        qty = item['qty']
        price = item['price']
        total = qty * price
        subtotal += total
        
        pdf.cell(80, 8, desc, 1, 0, 'L')
        pdf.cell(25, 8, str(qty), 1, 0, 'C')
        pdf.cell(30, 8, f'CAD ${price:.2f}', 1, 0, 'C')
        pdf.cell(35, 8, f'CAD ${total:.2f}', 1, 1, 'C')
    
    hst = subtotal * tax_rate
    total_due = subtotal + hst
    
    # Subtotal, HST, and Total
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(135, 8, 'Subtotal', 1, 0, 'R')
    pdf.cell(35, 8, f'CAD ${subtotal:.2f}', 1, 1, 'C')
    
    if tax_rate > 0:
        pdf.set_font('Arial', '', 10)
        pdf.cell(135, 8, f'HST ({tax_rate*100:.0f}%)', 1, 0, 'R')
        pdf.cell(35, 8, f'CAD ${hst:.2f}', 1, 1, 'C')
    
    pdf.set_font('Arial', 'B', 11)
    pdf.set_fill_color(200, 200, 200)
    pdf.cell(135, 10, 'TOTAL DUE', 1, 0, 'R', True)
    pdf.cell(35, 10, f'CAD ${total_due:.2f}', 1, 1, 'C', True)
    pdf.ln(10)

    # 5. NOTES
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 8, 'Notes:', 0, 1, 'L')
    pdf.set_font('Arial', '', 10)
    
    notes_parts = ["Thank you for your business! We appreciate your trust in Escala Solutions."]
    if tax_rate > 0:
        notes_parts.append(f"This invoice includes HST (Harmonized Sales Tax) at {tax_rate*100:.0f}% as applicable in Ontario.")
    notes_parts.append("Please contact Igor Gomides at igorgomides.ca@gmail.com or (519) 502-8015 if you have any questions.")
    
    notes = " ".join(notes_parts)
    pdf.multi_cell(0, 6, notes, 0, 'L')

    safe_name = "".join([c for c in client_name if c.isalpha() or c.isdigit() or c==' ']).rstrip()
    date_prefix = now.strftime('%Y_%m_%d')
    filename = f"{date_prefix}_Escala-Solutions_{invoice_number}_{safe_name.replace(' ', '_')}.pdf"
    output_path = f"/tmp/{filename}"
    pdf.output(output_path)
    return output_path

if __name__ == "__main__":
    test_items = [
        {'desc': 'T-Shirt - Size L', 'qty': 2, 'price': 35.00},
        {'desc': 'T-Shirt - Size M', 'qty': 3, 'price': 35.00}
    ]
    path = create_invoice("WKSC Group", "72 Rosebank Crescent\nKitchener, Ontario\nCanada", test_items, 0.13, "Upon Receipt")
    print(f"Invoice generated at: {path}")
