# -*- coding: utf-8 -*-
from odoo import _, fields, models
from odoo.exceptions import UserError


class StockLocation(models.Model):
    _inherit = "stock.location"

    block_as_stock_destination = fields.Boolean(
        string="Block as Stock Destination",
        help=(
            "Prevent stock operations from placing products directly in this "
            "location. The location can still be used as a source location."
        ),
    )


class StockMove(models.Model):
    _inherit = "stock.move"

    def _action_done(self, cancel_backorder=False):
        blocked_moves = self.filtered(
            lambda move: move.state not in ("done", "cancel")
            and move.location_dest_id.block_as_stock_destination
            and move.location_dest_id.usage == "internal"
            and move.location_id != move.location_dest_id
            and (move.quantity > 0 or move.is_inventory)
        )
        if blocked_moves:
            locations = ", ".join(
                sorted(set(blocked_moves.mapped("location_dest_id.complete_name")))
            )
            raise UserError(_(
                "Products cannot be received directly into the following main "
                "stock location(s): %(locations)s. Select a child/bin location "
                "instead.",
                locations=locations,
            ))

        return super()._action_done(cancel_backorder=cancel_backorder)


class StockPicking(models.Model):
    _inherit = "stock.picking"

    receiver_name = fields.Char(string="Receiver Name")
    receiver_phone = fields.Char(string="Receiver Phone Number")
    receiver_legal_id = fields.Char(string="Legal ID Number")
