from fpdf import FPDF
from datetime import datetime
import os
import re

class InvoicePDF(FPDF):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_margins(15, 15, 15)
        
    def header(self):
        # Draw Logo: "escala solutions" (top-left)
        self.set_font('Arial', 'B', 22)
        # "escala" in orange-red
        self.set_text_color(231, 76, 60)
        self.cell(26, 12, 'escala', 0, 0, 'L')
        # "solutions" in dark blue/grey
        self.set_text_color(44, 62, 80)
        self.cell(40, 12, 'solutions', 0, 0, 'L')
        
        # Right info (top-right)
        self.set_x(-120)
        self.set_font('Arial', 'B', 12)
        self.set_text_color(44, 62, 80)
        self.cell(105, 5, 'ESCALA SOLUTIONS', 0, 1, 'R')
        
        self.set_x(-120)
        self.set_font('Arial', '', 9)
        self.set_text_color(100, 100, 100)
        self.cell(105, 4, 'Kitchener, ON | igorgomides.ca@gmail.com | (519) 240-5450', 0, 1, 'R')
        
        self.ln(10)
        
        # Divider Line
        self.set_draw_color(220, 220, 220)
        self.set_line_width(0.5)
        self.line(15, 33, 195, 33)

def get_wrapped_lines(pdf, text, max_width):
    paragraphs = str(text).split('\n')
    all_lines = []
    for para in paragraphs:
        if not para.strip():
            all_lines.append("")
            continue
        words = para.split(' ')
        current_line = ""
        for word in words:
            test_line = current_line + " " + word if current_line else word
            if pdf.get_string_width(test_line) <= max_width:
                current_line = test_line
            else:
                all_lines.append(current_line)
                current_line = word
        if current_line:
            all_lines.append(current_line)
    return all_lines

def create_invoice(client_name: str, client_address: str, items: list, tax_rate: float, due_date: str, down_payments: float = 0.0):
    pdf = InvoicePDF()
    pdf.add_page()
    
    # TITLE & DETAILS / BILL TO (two column layout)
    pdf.set_y(40)
    
    # Title: "INVOICE"
    pdf.set_font('Arial', 'B', 24)
    pdf.set_text_color(44, 62, 80)
    pdf.cell(0, 12, 'INVOICE', 0, 1, 'L')
    pdf.ln(5)
    
    now = datetime.now()
    invoice_number = f'INV-{now.strftime("%Y%m%d-%H%M")}'
    issue_date = now.strftime('%B %d, %Y')
    
    col1_x = 15
    col2_x = 110
    y_start = pdf.get_y()
    
    # Left Column: Invoice Details
    pdf.set_xy(col1_x, y_start)
    pdf.set_font('Arial', 'B', 11)
    pdf.set_text_color(44, 62, 80)
    pdf.cell(80, 6, 'Invoice Details', 0, 1, 'L')
    
    pdf.set_font('Arial', '', 10)
    pdf.set_text_color(50, 50, 50)
    pdf.set_x(col1_x)
    pdf.cell(80, 5, f'Invoice#: {invoice_number}', 0, 1, 'L')
    pdf.set_x(col1_x)
    pdf.cell(80, 5, f'Date: {issue_date}', 0, 1, 'L')
    pdf.set_x(col1_x)
    pdf.cell(80, 5, f'Due Date: {due_date}', 0, 1, 'L')
    y_col1_end = pdf.get_y()
    
    # Right Column: Invoice To
    pdf.set_xy(col2_x, y_start)
    pdf.set_font('Arial', 'B', 11)
    pdf.set_text_color(44, 62, 80)
    pdf.cell(85, 6, 'Invoice To', 0, 1, 'L')
    
    pdf.set_font('Arial', 'B', 10)
    pdf.set_text_color(50, 50, 50)
    pdf.set_x(col2_x)
    pdf.cell(85, 5, client_name, 0, 1, 'L')
    
    pdf.set_font('Arial', '', 10)
    pdf.set_x(col2_x)
    pdf.cell(85, 5, 'Property Address:', 0, 1, 'L')
    pdf.set_x(col2_x)
    pdf.multi_cell(85, 4.5, client_address, 0, 'L')
    y_col2_end = pdf.get_y()
    
    pdf.set_y(max(y_col1_end, y_col2_end) + 8)
    
    # LINE ITEMS
    pdf.set_font('Arial', 'B', 11)
    pdf.set_text_color(44, 62, 80)
    pdf.cell(0, 8, 'Line Items', 0, 1, 'L')
    pdf.ln(2)
    
    # Table Header
    pdf.set_fill_color(217, 217, 217)
    pdf.set_text_color(50, 50, 50)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(110, 8, '  Description', 1, 0, 'L', True)
    pdf.cell(15, 8, 'Qty', 1, 0, 'C', True)
    pdf.cell(25, 8, 'Rate', 1, 0, 'C', True)
    pdf.cell(30, 8, 'Amount (CAD)', 1, 1, 'C', True)
    
    # Table Body
    pdf.set_font('Arial', '', 9.5)
    pdf.set_text_color(60, 60, 60)
    subtotal = 0.0
    
    for item in items:
        desc = item['desc']
        qty = item['qty']
        price = item['price']
        total = qty * price
        subtotal += total
        
        # Wrap description
        wrapped_lines = get_wrapped_lines(pdf, desc, 105)
        num_lines = max(len(wrapped_lines), 1)
        row_height = num_lines * 5.5 + 4
        
        start_x = pdf.get_x()
        start_y = pdf.get_y()
        
        # Draw borders
        pdf.rect(start_x, start_y, 110, row_height)
        pdf.rect(start_x + 110, start_y, 15, row_height)
        pdf.rect(start_x + 125, start_y, 25, row_height)
        pdf.rect(start_x + 150, start_y, 30, row_height)
        
        # Description text
        pdf.set_xy(start_x + 2.5, start_y + 2)
        pdf.multi_cell(105, 5.5, "\n".join(wrapped_lines), 0, 'L')
        
        # Qty, Rate, Amount
        pdf.set_xy(start_x + 110, start_y)
        pdf.cell(15, row_height, str(qty), 0, 0, 'C')
        pdf.cell(25, row_height, f'${price:,.2f}', 0, 0, 'C')
        pdf.cell(30, row_height, f'${total:,.2f}', 0, 1, 'C')
        
        if pdf.get_y() > 260:
            pdf.add_page()
            
    # Subtotal & HST
    hst = subtotal * tax_rate
    total_due = subtotal + hst
    
    pdf.ln(5)
    pdf.set_x(120)
    pdf.set_font('Arial', '', 10)
    pdf.cell(40, 6, 'Subtotal:', 0, 0, 'R')
    pdf.cell(30, 6, f'${subtotal:,.2f}', 0, 1, 'R')
    
    if tax_rate > 0:
        pdf.set_x(120)
        pdf.cell(40, 6, f'HST ({tax_rate*100:.0f}%):', 0, 0, 'R')
        pdf.cell(30, 6, f'${hst:,.2f}', 0, 1, 'R')
        
    pdf.ln(2)
    
    # Total Due Banner
    banner_width = 80
    banner_height = 10
    banner_x = 115
    banner_y = pdf.get_y()
    
    pdf.set_fill_color(75, 120, 169)
    pdf.rect(banner_x, banner_y, banner_width, banner_height, 'F')
    
    pdf.set_xy(banner_x, banner_y)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(45, banner_height, 'Total Due:', 0, 0, 'R')
    pdf.cell(30, banner_height, f'${total_due:,.2f} CAD', 0, 1, 'R')
    pdf.set_text_color(50, 50, 50)
    pdf.ln(10)
    
    # PAYMENT TERMS
    pdf.set_font('Arial', 'B', 11)
    pdf.set_text_color(44, 62, 80)
    pdf.cell(0, 8, 'Payment Terms', 0, 1, 'L')
    pdf.ln(2)
    
    pdf.set_font('Arial', '', 9.5)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(0, 5, 'Payment Schedule:', 0, 1, 'L')
    
    balance_due = total_due - down_payments
    
    pdf.cell(10, 5, '', 0, 0)
    pdf.cell(0, 5, f'- Advance Payment: ${down_payments:,.2f} (due before start of work)', 0, 1, 'L')
    pdf.cell(10, 5, '', 0, 0)
    pdf.cell(0, 5, f'- Final Payment: ${balance_due:,.2f} (due upon completion)', 0, 1, 'L')
    pdf.cell(10, 5, '', 0, 0)
    pdf.cell(0, 5, f'- Total Amount: ${total_due:,.2f} CAD', 0, 1, 'L')
    
    pdf.ln(3)
    pdf.set_font('Arial', 'B', 9.5)
    pdf.cell(32, 5, 'Payment Method:', 0, 0, 'L')
    pdf.set_font('Arial', '', 9.5)
    pdf.cell(0, 5, 'Interac E-transfer to igorgomides.ca@gmail.com', 0, 1, 'L')
    
    pdf.ln(5)
    pdf.set_font('Arial', '', 9)
    pdf.set_text_color(100, 100, 100)
    thank_you_text = (
        "Thank you for your business! If you have any questions regarding this invoice, "
        "please contact Escala Solutions at (519) 240-5450 or igorgomides.ca@gmail.com."
    )
    pdf.multi_cell(0, 5.5, thank_you_text, 0, 'L')
    
    filename = f"invoice_Painting_Service_{invoice_number}.pdf"
    output_path = f"/tmp/{filename}"
    pdf.output(output_path)
    return output_path
