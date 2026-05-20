# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import api,models, fields

class AccountInvoiceLine(models.Model):
    """Inherited Model account.move.line for fields and customized functionality"""
    _inherit = 'account.move.line'

    line_tax_Amount = fields.Float("Total Tax",
                                   compute='get_product_line_wise_tax_amount')
    taxable_amount = fields.Float("Taxable Amount",compute="get_computable_tax")
    @api.depends('tax_ids', 'price_subtotal')
    def get_product_line_wise_tax_amount(self):
        """Compute tax amount for each line"""
        self.line_tax_Amount = 0.0
        if self:
            for rec in self:
                if rec.price_subtotal:
                    if rec.tax_ids:
                        price = rec.price_unit * (
                            1 - (rec.discount or 0.0) / 100.0)
                        taxes = rec.tax_ids.compute_all(
                            price,
                            rec.move_id.currency_id,
                            rec.quantity,
                            product=rec.product_id)
                        line_tax = sum(
                            t.get('amount', 0.0)
                            for t in taxes.get('taxes', [])),
                        rec.line_tax_Amount = line_tax[0]
                    else:
                        rec.line_tax_Amount = 0.0
    @api.depends('price_unit','quantity')
    def get_computable_tax(self):
        """Compute taxable amount for each line"""
        for rec in self:
            rec.taxable_amount = 0.0
            if rec.price_unit and rec.quantity:
                rec.taxable_amount = rec.price_unit * rec.quantity


