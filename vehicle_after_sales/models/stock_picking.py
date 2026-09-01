from odoo import models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def button_validate(self):
        res = super().button_validate()
        self._vehicle_after_sales_register_deliveries()
        return res

    def _vehicle_after_sales_register_deliveries(self):
        Registry = self.env["vehicle.after.sales.registry"].sudo()
        for picking in self:
            if picking.state != "done" or not picking.partner_id:
                continue
            # Only deliveries from company internal stock to a customer location.
            if picking.location_id.usage != "internal" or picking.location_dest_id.usage != "customer":
                continue
            sale = getattr(picking, "sale_id", False)
            for ml in picking.move_line_ids:
                product = ml.product_id
                if not product.product_tmpl_id.is_vehicle_after_sales:
                    continue
                lot = ml.lot_id
                if not lot:
                    continue
                qty = ml.quantity if "quantity" in ml._fields else ml.qty_done
                if qty <= 0:
                    continue
                vals = {
                    "vin": lot.name,
                    "product_id": product.id,
                    "customer_id": picking.partner_id.commercial_partner_id.id,
                    "selling_company_id": picking.company_id.id,
                    "original_lot_id": lot.id,
                    "sale_order_id": sale.id if sale else False,
                    "delivery_id": picking.id,
                    "delivery_date": picking.date_done or picking.scheduled_date,
                    "warranty_months": product.product_tmpl_id.vehicle_warranty_months or 0,
                }
                registry = Registry.search([("vin", "=", lot.name), ("product_id", "=", product.id)], limit=1)
                if registry:
                    registry.write(vals)
                else:
                    registry = Registry.create(vals)
                # Record Company A's native lot as its mapping as well.
                Mapping = self.env["vehicle.after.sales.local.lot"].sudo()
                if not Mapping.search_count([("vehicle_id", "=", registry.id), ("company_id", "=", picking.company_id.id)]):
                    Mapping.create({
                        "vehicle_id": registry.id,
                        "company_id": picking.company_id.id,
                        "lot_id": lot.id,
                    })
