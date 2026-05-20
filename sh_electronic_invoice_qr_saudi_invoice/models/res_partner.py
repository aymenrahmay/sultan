# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import models, fields

class ResPartner(models.Model):
    """Inherited Model res.partner for adding needed fields"""
    _inherit = 'res.partner'

    sh_street = fields.Char()
    sh_street2 = fields.Char()
    sh_zip = fields.Char(change_default=True)
    sh_city = fields.Char()
    sh_state_id = fields.Char()
    sh_country_id = fields.Char()
    additional_no = fields.Char("Additional No")
    other_seller_id = fields.Char("Other Seller Id")
