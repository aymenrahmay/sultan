from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_vehicle_after_sales = fields.Boolean(
        string="Vehicle / VIN After-Sales",
        help="Enable VIN warranty registration and cross-company workshop handling for this product.",
    )
    vehicle_warranty_months = fields.Integer(
        string="Warranty (Months)",
        default=24,
        help="Default warranty duration starting from the customer delivery date.",
    )
