# -*- coding: utf-8 -*-
from odoo import fields, models


class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    partner_id = fields.Many2one(required=True)
    fleet_vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle')
    vin_sn = fields.Char(related='fleet_vehicle_id.vin_sn', string='Chassis Number')
    odometer = fields.Float(related='fleet_vehicle_id.odometer', string='Last Odometer')
    opening_ticket_km = fields.Float(string='KM at Ticket Opening')
    fuel_type = fields.Selection(related='fleet_vehicle_id.fuel_type', string='Fuel Type')
    model_year = fields.Selection(related='fleet_vehicle_id.model_year', string='Model year')
    vehicle_type = fields.Selection(related='fleet_vehicle_id.vehicle_type', string='Vehicle type')
