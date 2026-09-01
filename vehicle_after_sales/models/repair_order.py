from odoo import fields, models


class RepairOrder(models.Model):
    _inherit = "repair.order"

    vehicle_registry_id = fields.Many2one(
        "vehicle.after.sales.registry",
        string="Vehicle / VIN",
        index=True,
        help="Master vehicle identity linked to the original selling company and warranty.",
    )
    vehicle_helpdesk_ticket_id = fields.Many2one("helpdesk.ticket", string="After-Sales Ticket", index=True)
    original_sale_order_id = fields.Many2one(related="vehicle_registry_id.sale_order_id", string="Original Sale", readonly=True)
    original_delivery_id = fields.Many2one(related="vehicle_registry_id.delivery_id", string="Original Delivery", readonly=True)
    warranty_end = fields.Date(related="vehicle_registry_id.warranty_end", string="Warranty End", readonly=True)
