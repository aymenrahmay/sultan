import base64
import io
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

try:
    import pandas as pd
except ImportError:
    pd = None


class QtStockInventory(models.Model):
    _name = "qt.stock.inventory"
    _description = "Inventory Adjustment"
    _order = "date desc, id desc"

    name = fields.Char(string="Reference", required=True, default="New")
    date = fields.Datetime(string="Date", default=fields.Datetime.now, required=True)
    inventory_date = fields.Date(string="Counting Date", default=fields.Date.context_today)
    state = fields.Selection([("draft", "Draft"),("in_progress", "In Progress"),("done", "Validated"),("cancel", "Cancelled")], default="draft", readonly=True, copy=False, index=True, string="State")
    location_id = fields.Many2one(comodel_name="stock.location", string="Location", required=True, domain="[('usage', '=', 'internal')]")
    company_id = fields.Many2one(comodel_name="res.company", string="Company", default=lambda self: self.env.company, required=True)
    inventory_type = fields.Selection([("all", "All Products"),("partial", "Selected Products"),("template", "Product Templates"),("category", "Product Category"),("lot", "Lot/Serial"),("manual", "Manual Selection"), ("import", "Import from Excel")], default="all", string="Inventory Type", required=True)
    product_template_ids = fields.Many2many(comodel_name="product.template", string="Product Templates")
    product_ids = fields.Many2many(comodel_name="product.product", string="Products")
    categ_id = fields.Many2one(comodel_name="product.category", string="Category")
    lot_id = fields.Many2one(comodel_name="stock.lot", string="Lot/Serial")
    include_exhausted = fields.Boolean(string="Include Exhausted Products", default=False)
    prefill_counted = fields.Boolean(string="Prefill Counted Quantity", default=True)
    import_file = fields.Binary(string="Excel File")
    import_filename = fields.Char(string="File Name")
    line_ids = fields.One2many(comodel_name="qt.stock.inventory.line", inverse_name="inventory_id", string="Lines")
    move_ids = fields.One2many(comodel_name="stock.move", inverse_name="qt_inventory_id", string="Moves", readonly=True)
    line_count = fields.Integer(compute="_compute_counts", string="# Lines")
    shortage_count = fields.Integer(compute="_compute_counts", string="# Shortages")
    surplus_count = fields.Integer(compute="_compute_counts", string="# Surpluses")
    shortage_ids = fields.One2many("qt.stock.inventory.line", "inventory_id", compute="_compute_shortage_surplus", string="Shortages")
    surplus_ids = fields.One2many("qt.stock.inventory.line", "inventory_id", compute="_compute_shortage_surplus", string="Surpluses")

    @api.depends("line_ids", "line_ids.difference_qty")
    def _compute_counts(self):
        for inv in self:
            inv.line_count = len(inv.line_ids)
            inv.shortage_count = len(inv.line_ids.filtered(lambda l: l.difference_qty < 0))
            inv.surplus_count = len(inv.line_ids.filtered(lambda l: l.difference_qty > 0))

    @api.depends("line_ids.difference_qty")
    def _compute_shortage_surplus(self):
        for inv in self:
            inv.shortage_ids = inv.line_ids.filtered(lambda l: l.difference_qty < 0)
            inv.surplus_ids = inv.line_ids.filtered(lambda l: l.difference_qty > 0)

    @api.onchange("inventory_type")
    def _onchange_inventory_type(self):
        self.product_ids = False
        self.product_template_ids = False
        self.categ_id = False
        self.lot_id = False
        self.import_file = False

    def action_start(self):
        """Start inventory and generate lines."""
        Inventory = self.env[self._name]
        #if Inventory.search_count([('state', '=', 'in_progress'), ('id', 'not in', self.ids), ('location_id', '=', self.location_id.id)]):
            #raise UserError(self.env._("An inventory is already in progress for the selected location. Complete it before starting another."))
        for inv in self:
            if inv.state != "draft":
                raise UserError(self.env._("Only draft inventories can be started."))         
            if inv.inventory_type == "import" and inv.import_file:
                inv._import_from_excel()
            elif inv.inventory_type == "manual":
                inv._update_theoretical_qty()
            else:
                inv._generate_lines()
            
            inv.state = "in_progress"
    
    def _update_theoretical_qty(self):
        """Update theoretical quantity for manual lines."""
        self.ensure_one()
        for line in self.line_ids:
            quant = self.env["stock.quant"].search([
                ("product_id", "=", line.product_id.id),
                ("location_id", "=", line.location_id.id),
                ("lot_id", "=", line.lot_id.id if line.lot_id else False),
            ], limit=1)
            line.theoretical_qty = quant.quantity if quant else 0.0

    def _generate_lines(self):
        """Generate lines from quants based on inventory type."""
        self.ensure_one()
        self.line_ids.unlink()
        
        domain = [("location_id", "child_of", self.location_id.id)]
        
        if not self.include_exhausted:
            domain.append(("quantity", "!=", 0))
        
        if self.inventory_type == "partial" and self.product_ids:
            domain.append(("product_id", "in", self.product_ids.ids))
        elif self.inventory_type == "category" and self.categ_id:
            domain.append(("product_id.categ_id", "child_of", self.categ_id.id))
        elif self.inventory_type == "lot" and self.lot_id:
            domain.append(("lot_id", "=", self.lot_id.id))
        elif self.inventory_type == "template" and self.product_template_ids:
            # Get all product.product from selected templates
            product_ids = self.env["product.product"].search([
                ("product_tmpl_id", "in", self.product_template_ids.ids)
            ]).ids
            domain.append(("product_id", "in", product_ids))
        
        quants = self.env["stock.quant"].search(domain)
        
        vals_list = []
        for quant in quants:
            if not quant.product_id.is_storable:
                continue
            vals_list.append({
                "inventory_id": self.id,
                "product_id": quant.product_id.id,
                "location_id": quant.location_id.id,
                "lot_id": quant.lot_id.id,
                "package_id": quant.package_id.id,
                "owner_id": quant.owner_id.id,
                "theoretical_qty": quant.quantity,
                "product_qty": quant.quantity if self.prefill_counted else 0,
            })
        
        if self.include_exhausted and self.inventory_type in ("all", "partial", "category", "template"):
            product_domain = [("is_storable", "=", True)]
            if self.inventory_type == "partial" and self.product_ids:
                product_domain.append(("id", "in", self.product_ids.ids))
            elif self.inventory_type == "category" and self.categ_id:
                product_domain.append(("categ_id", "child_of", self.categ_id.id))
            elif self.inventory_type == "template" and self.product_template_ids:
                product_domain.append(("product_tmpl_id", "in", self.product_template_ids.ids))
            
            products = self.env["product.product"].search(product_domain)
            existing_products = {(v["product_id"], v.get("lot_id", False)) for v in vals_list}
            
            for product in products:
                if (product.id, False) not in existing_products:
                    vals_list.append({
                        "inventory_id": self.id,
                        "product_id": product.id,
                        "location_id": self.location_id.id,
                        "theoretical_qty": 0,
                        "product_qty": 0,
                    })
        
        if vals_list:
            self.env["qt.stock.inventory.line"].create(vals_list)

    def _import_from_excel(self):
        """Import lines from Excel file grouping by product+location+lot."""
        self.ensure_one()
        if not pd:
            raise UserError(self.env._("pandas library not installed."))
        
        self.line_ids.unlink()
        
        file_content = base64.b64decode(self.import_file)
        
        try:
            if self.import_filename.endswith(".csv"):
                df = pd.read_csv(io.BytesIO(file_content))
            else:
                df = pd.read_excel(io.BytesIO(file_content))
        except Exception as e:
            raise UserError(self.env._("Error reading file: %s") % str(e))
        
        df.columns = [c.upper().strip() for c in df.columns]
        
        if "CODE" not in df.columns or "QTY" not in df.columns:
            raise UserError(self.env._("The file must contain CODE and QTY columns."))
        
        grouped_data = {}
        for _, row in df.iterrows():
            code = str(row["CODE"]).strip()
            qty = float(row.get("QTY", 0) or 0)
            lot_name = str(row.get("LOT", "")).strip() if "LOT" in df.columns else ""
            
            product = self.env["product.product"].search([
                "|", ("default_code", "=", code), ("barcode", "=", code)
            ], limit=1)
            
            if not product:
                continue
            
            lot = False
            if lot_name and product.tracking != "none":
                lot = self.env["stock.lot"].search([
                    ("name", "=", lot_name),
                    ("product_id", "=", product.id),
                ], limit=1)
            
            key = (product.id, self.location_id.id, lot.id if lot else False)
            if key in grouped_data:
                grouped_data[key]["qty"] += qty
            else:
                grouped_data[key] = {
                    "product_id": product.id,
                    "location_id": self.location_id.id,
                    "lot_id": lot.id if lot else False,
                    "qty": qty,
                }
        
        vals_list = []
        for key, data in grouped_data.items():
            quant = self.env["stock.quant"].search([
                ("product_id", "=", data["product_id"]),
                ("location_id", "=", data["location_id"]),
                ("lot_id", "=", data["lot_id"]),
            ], limit=1)
            
            vals_list.append({
                "inventory_id": self.id,
                "product_id": data["product_id"],
                "location_id": data["location_id"],
                "lot_id": data["lot_id"],
                "theoretical_qty": quant.quantity if quant else 0,
                "product_qty": data["qty"],
            })
        
        if vals_list:
            self.env["qt.stock.inventory.line"].create(vals_list)

    def action_validate(self):
        """Validate inventory and create moves for differences."""
        for inv in self:
            if inv.state != "in_progress":
                raise UserError(self.env._("Only in-progress inventories can be validated."))
            
            lines_with_diff = inv.line_ids.filtered(lambda l: l.difference_qty != 0)
            if lines_with_diff:
                inv._create_moves(lines_with_diff)
            
            inv.state = "done"

    def _create_moves(self, lines):
        """Create stock moves for differences."""
        self.ensure_one()
        move_vals = []
        
        for line in lines:
            diff = line.difference_qty
            product = line.product_id.with_company(self.company_id)
            inv_location = product.property_stock_inventory
            
            if not inv_location:
                inv_location = self.env["stock.location"].search([
                    ("usage", "=", "inventory"),
                    "|", ("company_id", "=", self.company_id.id),
                    ("company_id", "=", False),
                ], limit=1)
            
            if not inv_location:
                raise UserError(self.env._("Inventory adjustment location not found."))
            
            if diff > 0:
                src, dst = inv_location, line.location_id
            else:
                src, dst = line.location_id, inv_location
                diff = abs(diff)
            
            move_vals.append({
                "qt_inventory_id": self.id,
                "product_id": line.product_id.id,
                "product_uom_qty": diff,
                "product_uom": line.product_id.uom_id.id,
                "location_id": src.id,
                "location_dest_id": dst.id,
                "company_id": self.company_id.id,
                "is_inventory": True,
                "inventory_name": self.name,
                "state": "confirmed",
                "picked": True,
                "move_line_ids": [(0, 0, {
                    "product_id": line.product_id.id,
                    "product_uom_id": line.product_id.uom_id.id,
                    "quantity": diff,
                    "location_id": src.id,
                    "location_dest_id": dst.id,
                    "lot_id": line.lot_id.id,
                    "package_id": line.package_id.id if src != inv_location else False,
                    "result_package_id": line.package_id.id if dst != inv_location else False,
                    "owner_id": line.owner_id.id,
                    "company_id": self.company_id.id,
                })],
            })
        
        moves = self.env["stock.move"].create(move_vals)
        moves._action_done()

    def action_cancel(self):
        """Cancel inventory."""
        for inv in self:
            if inv.state == "done":
                raise UserError(self.env._("Cannot cancel a validated inventory."))
            inv.state = "cancel"

    def action_draft(self):
        """Return to draft."""
        for inv in self:
            if inv.state not in ("cancel", "in_progress"):
                raise UserError(self.env._("Cannot return to draft."))
            inv.line_ids.unlink()
            inv.state = "draft"

    def action_view_lines(self):
        """Open lines view."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Inventory Lines"),
            "res_model": "qt.stock.inventory.line",
            "view_mode": "list",
            "domain": [("inventory_id", "=", self.id)],
            "context": {"default_inventory_id": self.id},
        }

    def action_view_shortages(self):
        """View shortages."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Shortages"),
            "res_model": "qt.stock.inventory.line",
            "view_mode": "list",
            "domain": [("inventory_id", "=", self.id), ("difference_qty", "<", 0)],
        }

    def action_view_surpluses(self):
        """View surpluses."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Surpluses"),
            "res_model": "qt.stock.inventory.line",
            "view_mode": "list",
            "domain": [("inventory_id", "=", self.id), ("difference_qty", ">", 0)],
        }

    def write(self, vals):
        if 'state' not in vals and any(r.state in ('done', 'cancel') for r in self):
            raise UserError(self.env._("You cannot modify inventories when they are Validated or Cancelled."))
        return super().write(vals)

    def unlink(self):
        for inv in self:
            if inv.state != "draft":
                raise UserError(self.env._("You can only delete inventories in Draft state."))
        return super().unlink()


class StockMove(models.Model):
    _inherit = "stock.move"

    qt_inventory_id = fields.Many2one(
        "qt.stock.inventory", "Inventory Adjustment", index=True
    )
