# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
{
    "name": "Electronic invoice KSA - Invoice, Credit Note, Bill, Refund",
    'author': 'Softhealer Technologies',
    'website': 'https://www.softhealer.com',
    "support": "support@softhealer.com",
    'version': '0.0.1',
    'category': "Accounting",
    'summary': "Electronic invoice KSA Saudi Electronic invoice Receipt Saudi VAT E-Invoice Saudi VAT E-Invoice for POS Electronic Invoice with QR code arabic translations ZATCA QR Code Invoice Arabic header arabic name Saudi VAT Invoice Saudi E-Invoice all pos in one retail ksa retail saudi retail KSA saudi retail electronic saudi ksa saudi ksa electronic odoo Saudi Invoice QR Code Invoice based on TLV Base64 string QR Code Saudi Electronic Invoice with Base64 TLV QRCode",
    'description': """This module allows you to print a Saudi electronic invoice with a QR code in the sale, purchase, invoice, credit note With Base64 TLV QR Code. You can display the data of VAT with tax details in the sale, purchase, invoice, credit note With Base64 TLV QR Code. You can print receipts in regional and global languages, such as Arabic and English As per Saudi Arabia Zakat's regulations to apply specific terms to the electronic invoice by 4th of Dec 2021.""",
    "depends" : ["account","base","sale_management","purchase"],
    "application" : True,
    "data" : [
            'data/sh_electronic_invoice_qr_saudi_invoice_paperformat.xml',
            'views/res_company_views.xml',
            'views/res_partner_views.xml',
            'views/account_move_views.xml',
            'report/invoice_external_layout_templates.xml',
            'report/invoice_report_templates.xml',
            'report/account_simplified_report_templates.xml',
            'report/account_move_report_action.xml',
            ],
    "external_dependencies": {
        "python": ["qrcode"],
    },

    "images": ["static/description/background.png", ],
    "license": "OPL-1",
    "auto_install":False,
    "installable" : True,
    "price": 21,
    "currency": "EUR"
}
