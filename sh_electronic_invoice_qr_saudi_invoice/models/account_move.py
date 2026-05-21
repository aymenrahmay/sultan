# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import api,models, fields
try:
    import qrcode
except ImportError:
    qrcode = None
import base64
import io
from num2words import num2words
from datetime import datetime

class AccountMove(models.Model):
    """Inherited Model account.move for adding fields and functionality"""
    _inherit = 'account.move'

    add_product_arabic_name = fields.Boolean("Add Product Arabic Name",default=True)
    sh_vat = fields.Char(string="Vat",related="company_id.vat")
    sh_qr_code = fields.Text(string="QR Code new", compute="generate_zatac_code")
    sh_qr_code_img = fields.Binary(string = "QR Code Image",compute = "compute_sh_qr_code_img")
    amount_move_undiscounted = fields.Float('Amount Before Discount', compute='_compute_amount_move_undiscounted', digits=0)
    amount_in_words = fields.Char( compute='amount_word', string='Amount ', readonly=True,)
    amount_in_words_ar = fields.Char( compute='amount_word', string=' Amount arabic ', readonly=True,)

    receiver_name = fields.Char(string="Receiver Name")
    receiver_phone = fields.Char(string="Receiver Phone Number")
    receiver_legal_id = fields.Char(string="Legal ID Number")


    def _get_name_invoice_report(self):
        """Calls the report template"""
        self.ensure_one()
        res =  super()._get_name_invoice_report()
        return 'account.report_invoice_document'

    @api.depends('amount_total')
    def amount_word(self):
        """Convert amount into words"""
        total_amount = self.amount_residual
        self.ensure_one()
        amount_str = str('{:2f}'.format(total_amount))
        amount_str_splt = amount_str.split('.')
        before_point_value = amount_str_splt[0]
        after_point_value = amount_str_splt[1][:2]
        before_amount_words = num2words(int(before_point_value))
        after_amount_words = num2words(int(after_point_value))
        before_amount_ar = num2words(int(before_point_value), lang="ar")
        after_amount_ar = num2words(int(after_point_value), lang="ar")
        amount = before_amount_words
        amount_ar = before_amount_ar
        amount += ' Riyal and ' + after_amount_words + ' Halalas'
        amount_ar += ' ريال و ' + after_amount_ar + ' هللة'
        self.amount_in_words = amount.title()
        self.amount_in_words_ar = amount_ar

    def _compute_amount_move_undiscounted(self):
        """Compute the total amount before discount"""
        for order in self:
            total = 0.0
            for line in order.invoice_line_ids:
                total += line.price_subtotal + line.price_unit * ((line.discount or 0.0) / 100.0) * line.quantity  # why is there a discount in a field named amount_undiscounted ??
            order.amount_move_undiscounted = total

    @api.depends('amount_total', 'amount_tax', 'invoice_date', 'company_id',
                 'sh_vat')
    def generate_zatac_code(self):
        """Generate QR code as per ZATCA guidelines"""
        def get_qr_encoding(tag, field):
            """Get the encoding of each field"""
            company_name_byte_array = field.encode('UTF-8')
            company_name_tag_encoding = tag.to_bytes(length=1, byteorder='big')
            company_name_length_encoding = len(
                company_name_byte_array).to_bytes(length=1, byteorder='big')
            return company_name_tag_encoding + company_name_length_encoding + company_name_byte_array

        for record in self:
            record.sh_qr_code = False
            if record.state == 'posted':
                qr_code_str = ''
                if record.invoice_date and record.sh_vat:
                    seller_name_enc = get_qr_encoding(
                        1, record.company_id.display_name)
                    company_vat_enc = get_qr_encoding(2, record.sh_vat)
                    now = datetime.now()
                    time = now.time()
                    combined = datetime.combine(record.invoice_date, time)
                    time_sa = fields.Datetime.context_timestamp(
                        self.with_context(tz='Asia/Riyadh'), combined)

                    timestamp_enc = get_qr_encoding(3, time_sa.isoformat())
                    invoice_total_enc = get_qr_encoding(
                        4, str(record.amount_total))
                    total_vat_enc = get_qr_encoding(5, str(record.amount_tax))

                    str_to_encode = seller_name_enc + company_vat_enc + timestamp_enc + invoice_total_enc + total_vat_enc
                    qr_code_str = base64.b64encode(str_to_encode).decode(
                        'UTF-8')
                record.sh_qr_code = qr_code_str

    @api.depends('sh_qr_code')
    def compute_sh_qr_code_img(self):
        """Generate QR code image from the QR code string"""
        for rec in self:

            rec.sh_qr_code_img = False

            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )

            qr.add_data(rec.sh_qr_code)
            qr.make(fit=True)

            img = qr.make_image()
            temp = io.BytesIO()
            img.save(temp, format="PNG")
            qr_code_image = base64.b64encode(temp.getvalue())
            rec.sh_qr_code_img = qr_code_image
