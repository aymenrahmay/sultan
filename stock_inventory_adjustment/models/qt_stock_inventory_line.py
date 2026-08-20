from odoo import api, fields, models
from odoo.exceptions import UserError


class QtStockInventoryLine(models.Model):
    _name = "qt.stock.inventory.line"
    _description = "Inventory Adjustment Line"

    inventory_id = fields.Many2one(comodel_name="qt.stock.inventory", string="Inventory", required=True, ondelete="cascade")
    product_id = fields.Many2one(comodel_name="product.product", string="Product", required=True, domain="[('is_storable', '=', True)]")
    location_id = fields.Many2one(comodel_name="stock.location", string="Location", required=True, domain="[('usage', '=', 'internal')]")
    lot_id = fields.Many2one(comodel_name="stock.lot", string="Lot/Serial", domain="[('product_id', '=', product_id)]")
    package_id = fields.Many2one(comodel_name="stock.package", string="Package")
    owner_id = fields.Many2one(comodel_name="res.partner", string="Owner")
    theoretical_qty = fields.Float(string="Theoretical Qty", digits="Product Unit of Measure")
    product_qty = fields.Float(string="Counted Qty", digits="Product Unit of Measure")
    difference_qty = fields.Float(string="Difference", compute="_compute_difference", store=True, digits="Product Unit of Measure")
    state = fields.Selection(related="inventory_id.state", store=True)
    company_id = fields.Many2one(related="inventory_id.company_id", store=True)
    inventory_date = fields.Date(related="inventory_id.inventory_date", string="Counting Date", store=True, index=True)
    categ_id = fields.Many2one(comodel_name="product.category", related="product_id.categ_id", string="Category", store=True)

    @api.depends("theoretical_qty", "product_qty")
    def _compute_difference(self):
        for line in self:
            line.difference_qty = line.product_qty - line.theoretical_qty

    @api.onchange("product_id", "location_id", "lot_id", "package_id", "owner_id")
    def _onchange_product(self):
        """Update theoretical quantity when changing product/location."""
        if not self.product_id or not self.location_id:
            self.theoretical_qty = 0
            return
        
        domain = [
            ("product_id", "=", self.product_id.id),
            ("location_id", "=", self.location_id.id),
        ]
        if self.lot_id:
            domain.append(("lot_id", "=", self.lot_id.id))
        else:
            domain.append(("lot_id", "=", False))
        if self.package_id:
            domain.append(("package_id", "=", self.package_id.id))
        else:
            domain.append(("package_id", "=", False))
        if self.owner_id:
            domain.append(("owner_id", "=", self.owner_id.id))
        else:
            domain.append(("owner_id", "=", False))
        
        quant = self.env["stock.quant"].search(domain, limit=1)
        self.theoretical_qty = quant.quantity if quant else 0.0

    def action_refresh(self):
        """Refresh theoretical quantity."""
        for line in self:
            line._onchange_product()

    def action_reset_qty(self):
        """Reset counted quantity to theoretical."""
        for line in self:
            line.product_qty = line.theoretical_qty

    def write(self, vals):
        if 'state' not in vals and any(r.state in ('done', 'cancel') for r in self):
            raise UserError(self.env._("You cannot modify lines when the inventory is Validated or Cancelled."))
        return super().write(vals)
