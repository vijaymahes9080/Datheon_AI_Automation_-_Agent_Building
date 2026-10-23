from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os

os.makedirs('data', exist_ok=True)

# 1. Valid Invoice PDF
c1 = canvas.Canvas('data/valid_sample_invoice.pdf', pagesize=letter)
c1.drawString(100, 750, 'Vendor: Acme Cloud Infrastructure Inc.')
c1.drawString(100, 730, 'Invoice Number: INV-2026-8801')
c1.drawString(100, 710, 'Date: 2026-10-20')
c1.drawString(100, 680, 'Line Items:')
c1.drawString(120, 660, 'Enterprise Cloud Cluster 1 x $1000.00 = $1000.00')
c1.drawString(100, 620, 'Subtotal: $1000.00')
c1.drawString(100, 600, 'Tax: $100.00')
c1.drawString(100, 580, 'Total: $1100.00')
c1.drawString(100, 550, 'Payment Status: UNPAID')
c1.save()

# 2. Discrepant Invoice PDF (Stated Total $2500 vs Calculated $2200)
c2 = canvas.Canvas('data/discrepant_sample_invoice.pdf', pagesize=letter)
c2.drawString(100, 750, 'Vendor: Nova Digital Agency')
c2.drawString(100, 730, 'Invoice Number: INV-2026-9902')
c2.drawString(100, 710, 'Date: 2026-10-21')
c2.drawString(100, 680, 'Line Items:')
c2.drawString(120, 660, 'Consulting Services 2 x $1000.00 = $2000.00')
c2.drawString(100, 620, 'Subtotal: $2000.00')
c2.drawString(100, 600, 'Tax: $200.00')
c2.drawString(100, 580, 'Total: $2500.00')
c2.drawString(100, 550, 'Payment Status: UNPAID')
c2.save()

print('Sample PDFs generated successfully.')
