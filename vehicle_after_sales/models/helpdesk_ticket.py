from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HelpdeskTicket(models.Model):
    _inherit = "helpdesk.ticket"

    vehicle_registry_id = fields.Many2one("vehicle.after.sales.registry", string="Vehicle / VIN", index=True)
    vehicle_product_id = fields.Many2one(related="vehicle_registry_id.product_id", string="Vehicle Product", readonly=True)
    vehicle_vin = fields.Char(related="vehicle_registry_id.vin", string="VIN", readonly=True)
    vehicle_selling_company_id = fields.Many2one(related="vehicle_registry_id.selling_company_id", string="Selling Company", readonly=True)
    vehicle_sale_order_id = fields.Many2one(related="vehicle_registry_id.sale_order_id", string="Original SO", readonly=True)
    vehicle_delivery_id = fields.Many2one(related="vehicle_registry_id.delivery_id", string="Original Delivery", readonly=True)
    vehicle_warranty_end = fields.Date(related="vehicle_registry_id.warranty_end", string="Warranty End", readonly=True)
    vehicle_warranty_status = fields.Selection(related="vehicle_registry_id.warranty_status", string="Warranty Status", readonly=True)
    warranty_coverage_approved = fields.Boolean(
        string="Warranty Coverage Approved",
        help="Date validity is automatic; use this checkbox after confirming that the reported failure is covered by the warranty terms.",
    )
    vehicle_received = fields.Boolean(default=False, readonly=True, copy=False)
    vehicle_returned = fields.Boolean(default=False, readonly=True, copy=False)
    vehicle_receipt_id = fields.Many2one("stock.picking", string="Vehicle Receipt", readonly=True, copy=False)
    vehicle_return_id = fields.Many2one("stock.picking", string="Vehicle Return", readonly=True, copy=False)
    vehicle_repair_id = fields.Many2one("repair.order", string="Vehicle Repair", readonly=True, copy=False)

    @api.onchange("vehicle_registry_id")
    def _onchange_vehicle_registry_id(self):
        for ticket in self:
            if ticket.vehicle_registry_id:
                ticket.partner_id = ticket.vehicle_registry_id.customer_id
                # Helpdesk Enterprise commonly has product_id; set it when available.
                if "product_id" in ticket._fields:
                    ticket.product_id = ticket.vehicle_registry_id.product_id

    def _get_workshop_location(self):
        self.ensure_one()
        company = self.company_id
        if not company:
            raise UserError(_("The helpdesk ticket must belong to a company."))
        company_env = self.env(context=dict(
            self.env.context,
            allowed_company_ids=[company.id],
            force_company=company.id,
        ))
        Warehouse = company_env["stock.warehouse"].sudo().with_company(company)
        warehouse = Warehouse.search([("company_id", "=", company.id)], limit=1)
        if not warehouse:
            raise UserError(_("Company %s has no warehouse configured.") % company.display_name)
        Location = company_env["stock.location"].sudo().with_company(company)
        location = Location.search([
            ("company_id", "=", company.id),
            ("location_id", "=", warehouse.view_location_id.id),
            ("name", "=", "Customer Vehicles / Workshop"),
        ], limit=1)
        if not location:
            location = Location.create({
                "name": "Customer Vehicles / Workshop",
                "location_id": warehouse.view_location_id.id,
                "usage": "internal",
                "company_id": company.id,
            })
        return warehouse, location

    def _make_vehicle_picking(self, to_workshop=True):
        self.ensure_one()
        if not self.vehicle_registry_id:
            raise UserError(_("Select a Vehicle / VIN first."))
        if not self.partner_id:
            raise UserError(_("A customer is required."))

        company = self.company_id
        if not company:
            raise UserError(_("The helpdesk ticket must belong to a company."))
        company_env = self.env(context=dict(
            self.env.context,
            allowed_company_ids=[company.id],
            force_company=company.id,
        ))
        warehouse, workshop = self._get_workshop_location()
        customer_loc = company_env.ref("stock.stock_location_customers")
        product = self.vehicle_registry_id.product_id
        lot = self.vehicle_registry_id.with_env(company_env)._get_or_create_company_lot(company)

        source = customer_loc if to_workshop else workshop
        dest = workshop if to_workshop else customer_loc
        picking_type = warehouse.in_type_id if to_workshop else warehouse.out_type_id
        direction = _("Workshop Receipt") if to_workshop else _("Workshop Return")

        picking = company_env["stock.picking"].sudo().with_company(company).create({
            "partner_id": self.partner_id.id,
            "picking_type_id": picking_type.id,
            "location_id": source.id,
            "location_dest_id": dest.id,
            "origin": "%s - %s" % (self.display_name, direction),
            "company_id": company.id,
        })
        Move = company_env["stock.move"].sudo().with_company(company)
        move_description = "%s - %s" % (product.display_name, self.vehicle_registry_id.vin)
        move_vals = {
            "product_id": product.id,
            "product_uom_qty": 1.0,
            "product_uom": product.uom_id.id,
            "location_id": source.id,
            "location_dest_id": dest.id,
            "picking_id": picking.id,
            "company_id": company.id,
        }
        # ``stock.move.name`` was removed in Odoo 19.  Keep the useful VIN
        # description while remaining compatible with versions where it is
        # still the move's description field.
        if "description_picking_manual" in Move._fields:
            move_vals["description_picking_manual"] = move_description
        elif "name" in Move._fields:
            move_vals["name"] = move_description
        # Mark as customer-owned/consigned where supported by this Odoo build.
        if "restrict_partner_id" in Move._fields:
            move_vals["restrict_partner_id"] = self.partner_id.commercial_partner_id.id
        move = Move.create(move_vals)
        move._action_confirm()
        move._action_assign()

        MoveLine = company_env["stock.move.line"].sudo().with_company(company)
        line_vals = {
            "move_id": move.id,
            "picking_id": picking.id,
            "product_id": product.id,
            "product_uom_id": product.uom_id.id,
            "lot_id": lot.id,
            "location_id": source.id,
            "location_dest_id": dest.id,
            "company_id": company.id,
        }
        if "owner_id" in MoveLine._fields:
            line_vals["owner_id"] = self.partner_id.commercial_partner_id.id
        qty_field = "quantity" if "quantity" in MoveLine._fields else "qty_done"
        line_vals[qty_field] = 1.0

        # Remove empty auto-generated lines to avoid duplicate serial lines.
        empty_lines = move.move_line_ids.filtered(lambda ml: not ml.lot_id and not getattr(ml, qty_field, 0.0))
        empty_lines.unlink()
        if not move.move_line_ids:
            MoveLine.create(line_vals)
        else:
            move.move_line_ids[0].write(line_vals)

        picking.with_company(company).button_validate()
        return picking, lot, workshop

    def action_receive_vehicle(self):
        for ticket in self:
            if ticket.vehicle_received and not ticket.vehicle_returned:
                raise UserError(_("This vehicle is already received in the workshop."))
            picking, lot, workshop = ticket._make_vehicle_picking(to_workshop=True)
            ticket.write({
                "vehicle_received": True,
                "vehicle_returned": False,
                "vehicle_receipt_id": picking.id,
                "vehicle_return_id": False,
            })
            ticket.message_post(body=_("Vehicle %s received into workshop with serial %s.") % (ticket.vehicle_registry_id.vin, lot.name))
        return True

    def action_create_vehicle_repair(self):
        self.ensure_one()
        if not self.vehicle_received or self.vehicle_returned:
            raise UserError(_("Receive the vehicle into the workshop before creating the repair."))
        if self.vehicle_repair_id:
            return {
                "type": "ir.actions.act_window",
                "res_model": "repair.order",
                "view_mode": "form",
                "res_id": self.vehicle_repair_id.id,
            }

        company = self.company_id
        if not company:
            raise UserError(_("The helpdesk ticket must belong to a company."))
        _warehouse, workshop = self._get_workshop_location()
        lot = self.vehicle_registry_id._get_or_create_company_lot(company)
        Repair = self.env["repair.order"].sudo().with_company(company)
        vals = {
            "partner_id": self.partner_id.id,
            "product_id": self.vehicle_registry_id.product_id.id,
            "lot_id": lot.id,
            "company_id": company.id,
            "vehicle_registry_id": self.vehicle_registry_id.id,
            "vehicle_helpdesk_ticket_id": self.id,
        }
        # Keep compatibility with minor Odoo 19 field variations.
        if "location_id" in Repair._fields:
            vals["location_id"] = workshop.id
        if "under_warranty" in Repair._fields:
            vals["under_warranty"] = bool(
                self.vehicle_warranty_status == "valid" and self.warranty_coverage_approved
            )
        if "origin" in Repair._fields:
            vals["origin"] = self.display_name
        vals = {k: v for k, v in vals.items() if k in Repair._fields}
        repair = Repair.create(vals)
        self.vehicle_repair_id = repair.id
        self.message_post(body=_("Repair order %s created for VIN %s.") % (repair.display_name, self.vehicle_registry_id.vin))
        return {
            "type": "ir.actions.act_window",
            "res_model": "repair.order",
            "view_mode": "form",
            "res_id": repair.id,
        }

    def action_return_vehicle(self):
        for ticket in self:
            if not ticket.vehicle_received:
                raise UserError(_("The vehicle has not been received yet."))
            if ticket.vehicle_returned:
                raise UserError(_("The vehicle has already been returned to the customer."))
            if ticket.vehicle_repair_id and ticket.vehicle_repair_id.state not in ("done", "cancel"):
                raise UserError(_("Finish or cancel the repair before returning the vehicle."))
            picking, lot, _workshop = ticket._make_vehicle_picking(to_workshop=False)
            ticket.write({"vehicle_returned": True, "vehicle_return_id": picking.id})
            ticket.message_post(body=_("Vehicle %s returned to the customer.") % ticket.vehicle_registry_id.vin)
        return True

    def action_open_vehicle_receipt(self):
        self.ensure_one()
        return {"type": "ir.actions.act_window", "res_model": "stock.picking", "view_mode": "form", "res_id": self.vehicle_receipt_id.id}

    def action_open_vehicle_return(self):
        self.ensure_one()
        return {"type": "ir.actions.act_window", "res_model": "stock.picking", "view_mode": "form", "res_id": self.vehicle_return_id.id}

    def action_open_vehicle_repair(self):
        self.ensure_one()
        return {"type": "ir.actions.act_window", "res_model": "repair.order", "view_mode": "form", "res_id": self.vehicle_repair_id.id}
