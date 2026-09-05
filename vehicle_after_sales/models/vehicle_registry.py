from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class VehicleAfterSalesRegistry(models.Model):
    _name = "vehicle.after.sales.registry"
    _description = "Vehicle After-Sales Registry"
    _order = "delivery_date desc, id desc"
    _rec_name = "vin"

    active = fields.Boolean(default=True)

    def action_cancel(self):
        """Retain the VIN history while removing after-sales eligibility."""
        self.write({"active": False})
        return True

    vin = fields.Char(string="VIN / Serial Number", required=True, index=True)
    product_id = fields.Many2one("product.product", string="Vehicle Product", required=True, index=True)
    customer_id = fields.Many2one("res.partner", string="Current Customer", required=True, index=True)
    selling_company_id = fields.Many2one("res.company", string="Selling Company", required=True, index=True)
    original_lot_id = fields.Many2one("stock.lot", string="Original Serial/Lot", readonly=True)
    sale_order_id = fields.Many2one("sale.order", string="Original Sales Order", readonly=True)
    delivery_id = fields.Many2one("stock.picking", string="Original Delivery", readonly=True)
    delivery_date = fields.Datetime(string="Delivery Date", readonly=True)
    warranty_months = fields.Integer(string="Warranty Months", default=36)
    warranty_start = fields.Date(string="Warranty Start", compute="_compute_warranty_dates", store=True)
    warranty_end = fields.Date(string="Warranty End", compute="_compute_warranty_dates", store=True)
    warranty_status = fields.Selection(
        [("valid", "Valid"), ("expired", "Expired"), ("unknown", "Unknown")],
        compute="_compute_warranty_status",
        string="Warranty Status",
    )
    local_lot_ids = fields.One2many("vehicle.after.sales.local.lot", "vehicle_id", string="Company Serial Records")
    repair_ids = fields.One2many("repair.order", "vehicle_registry_id", string="Repairs")
    repair_count = fields.Integer(compute="_compute_repair_count")

    _sql_constraints = [
        ("vin_product_unique", "unique(vin, product_id)", "This VIN already exists for this vehicle product."),
    ]

    @api.depends("delivery_date", "warranty_months")
    def _compute_warranty_dates(self):
        for rec in self:
            if rec.delivery_date:
                start = fields.Date.to_date(rec.delivery_date)
                rec.warranty_start = start
                rec.warranty_end = start + relativedelta(months=rec.warranty_months or 0)
            else:
                rec.warranty_start = False
                rec.warranty_end = False

    def _compute_warranty_status(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if not rec.warranty_end:
                rec.warranty_status = "unknown"
            elif rec.warranty_start and rec.warranty_start <= today <= rec.warranty_end:
                rec.warranty_status = "valid"
            else:
                rec.warranty_status = "expired"

    def _compute_repair_count(self):
        for rec in self:
            rec.repair_count = len(rec.repair_ids)

    def _get_or_create_company_lot(self, company):
        """Return one stock.lot per company for operational stock moves.

        The master identity remains this registry record. A company-specific lot is
        created only if Odoo's company isolation requires one, and then reused forever.
        The selling company keeps the sold lot name; workshop companies use the sold
        lot name suffixed with ``_repaire`` so the two operational serials are easy to
        distinguish.
        """
        self.ensure_one()
        link = self.local_lot_ids.filtered(lambda l: l.company_id == company)[:1]
        if link and link.lot_id:
            return link.lot_id

        company_env = self.env(context=dict(
            self.env.context,
            allowed_company_ids=[company.id],
            force_company=company.id,
        ))
        Lot = company_env["stock.lot"].sudo().with_company(company)
        sold_lot_name = self.original_lot_id.name or self.vin
        is_selling_company = company == self.selling_company_id
        lot_name = sold_lot_name if is_selling_company else "%s_repaire" % sold_lot_name

        # Prefer the exact sold lot for Company A. For another company, only reuse
        # that company's repair lot and never attach Company A's original lot.
        if is_selling_company and self.original_lot_id:
            lot = self.original_lot_id
        else:
            domain = [("name", "=", lot_name), ("product_id", "=", self.product_id.id)]
            if "company_id" in Lot._fields:
                domain.append(("company_id", "=", company.id))
            lot = Lot.search(domain, limit=1)
        if not lot:
            vals = {"name": lot_name, "product_id": self.product_id.id}
            if "company_id" in Lot._fields:
                vals["company_id"] = company.id
            lot = Lot.create(vals)
        company_env["vehicle.after.sales.local.lot"].sudo().create({
            "vehicle_id": self.id,
            "company_id": company.id,
            "lot_id": lot.id,
        })
        return lot

    def action_view_repairs(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Vehicle Repairs"),
            "res_model": "repair.order",
            "view_mode": "list,form",
            "domain": [("vehicle_registry_id", "=", self.id)],
            "context": {"default_vehicle_registry_id": self.id},
        }


class VehicleAfterSalesLocalLot(models.Model):
    _name = "vehicle.after.sales.local.lot"
    _description = "Vehicle Company Serial Mapping"
    _rec_name = "lot_id"

    vehicle_id = fields.Many2one("vehicle.after.sales.registry", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one("res.company", required=True, index=True)
    lot_id = fields.Many2one("stock.lot", required=True, ondelete="restrict")

    _sql_constraints = [
        ("vehicle_company_unique", "unique(vehicle_id, company_id)", "A company serial mapping already exists for this VIN."),
    ]
