# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import api,models, fields


class BaseDocumentLayout(models.TransientModel):
    """Inherited Model base.document for extra fields"""
    _inherit = 'base.document.layout'

    street = fields.Char(related="company_id.street")
    street2=fields.Char(related='company_id.street2')
    city=fields.Char(related='company_id.city')
    zip=fields.Char(related='company_id.zip')
    sh_name = fields.Char(related='company_id.sh_name')
    sh_street = fields.Char(related='company_id.sh_street')
    sh_street2 = fields.Char(related='company_id.sh_street2')
    sh_zip = fields.Char(related='company_id.sh_zip')
    sh_city = fields.Char(related='company_id.sh_city')
    sh_state_id = fields.Char(related='company_id.sh_state_id')
    sh_country_id = fields.Char(related='company_id.sh_country_id')
    additional_no = fields.Char(related='company_id.additional_no')
    other_seller_id = fields.Char(related='company_id.other_seller_id')
    company_registry = fields.Char(related='company_id.company_registry')
