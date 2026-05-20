# -*- coding: utf-8 -*-
from odoo import fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    receiver_name = fields.Char(string="Receiver Name")
    receiver_phone = fields.Char(string="Receiver Phone Number")
    receiver_legal_id = fields.Char(string="Legal ID Number")
