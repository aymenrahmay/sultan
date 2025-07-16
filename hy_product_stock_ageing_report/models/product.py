######################################################################################
#
#    Hynsys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Hynsys Technologies(<https://www.hynsys.com>).
#    Author: Hynsys Technologies(<https://www.hynsys.com>)
#
#    This program is under the terms of the Odoo Proprietary License v1.0 (OPL-1)
#    It is forbidden to publish, distribute, sublicense, or sell copies of the Software
#    or modified copies of the Software.
#
#    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
#    IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
#    DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
#    ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
#    DEALINGS IN THE SOFTWARE.
#
######################################################################################

from odoo import fields, models
from odoo.tools.float_utils import float_round
from odoo.exceptions import ValidationError


class ProductProduct(models.Model):
    _inherit = "product.product"

    def compute_quantities_stock_ageing(self):
        product_qty_available = self._compute_quantities_stock_ageing_dict(
            self._context.get("lot_id"),
            self._context.get("owner_id"),
            self._context.get("package_id"),
            self._context.get("from_date"),
            self._context.get("to_date"),
        )
        return product_qty_available

    def _compute_quantities_stock_ageing_dict(self, lot_id, owner_id, package_id, from_date=False, to_date=False):
        (
            domain_quant_loc,
            domain_move_in_loc,
            domain_move_out_loc,
        ) = self._get_domain_locations()
        domain_quant = [("product_id", "in", self.ids)] + domain_quant_loc
        dates_in_the_past = False
        # only to_date as to_date will correspond to qty_available
        to_date = fields.Datetime.to_datetime(to_date)
        if to_date and to_date < fields.Datetime.now():
            dates_in_the_past = True

        domain_move_in = [("product_id", "in", self.ids)] + domain_move_in_loc
        domain_move_out = [("product_id", "in", self.ids)] + domain_move_out_loc
        if lot_id is not None:
            domain_quant += [("lot_id", "=", lot_id)]
        if owner_id is not None:
            domain_quant += [("owner_id", "=", owner_id)]
            domain_move_in += [("restrict_partner_id", "=", owner_id)]
            domain_move_out += [("restrict_partner_id", "=", owner_id)]
        if package_id is not None:
            domain_quant += [("package_id", "=", package_id)]
        if dates_in_the_past:
            domain_move_in_done = list(domain_move_in)
            domain_move_out_done = list(domain_move_out)
        if from_date:
            date_date_expected_domain_from = [("date", ">=", from_date)]
            domain_move_in += date_date_expected_domain_from
            domain_move_out += date_date_expected_domain_from
        if to_date:
            date_date_expected_domain_to = [("date", "<=", to_date)]
            domain_move_in += date_date_expected_domain_to
            domain_move_out += date_date_expected_domain_to

        Move = self.env["stock.move"].with_context(active_test=False)
        Quant = self.env["stock.quant"].with_context(active_test=False)

        # quants_res = {item["product_id"][0]: (item["quantity"], item["reserved_quantity"])
        #     for item in Quant.read_group(
        #         domain_quant,
        #         ["product_id", "quantity", "reserved_quantity"],
        #         ["product_id"],
        #         orderby="id",
        #     )
        # }

        quants_res = {
            item["product_id"][0]: (item["quantity"], item["reserved_quantity"])
            for item in Quant.read_group(
                domain_quant,
                ["product_id", "quantity", "reserved_quantity"],
                ["product_id"],  # Grouping by product_id only
                # orderby="id",  # Remove this line (invalid for read_group)
            )
        }
        if dates_in_the_past:
            # Calculate the moves that were done before now to calculate back in time
            # (as most questions will be recent ones)
            domain_move_in_done = [
                ("state", "=", "done"),
                ("date", ">", to_date),
            ] + domain_move_in_done
            domain_move_out_done = [
                ("state", "=", "done"),
                ("date", ">", to_date),
            ] + domain_move_out_done
            # moves_in_res_past = {
            #     item["product_id"][0]: item["product_qty"]
            #     for item in Move.read_group(
            #         domain_move_in_done,
            #         ["product_id", "product_qty"],
            #         ["product_id"],
            #         orderby="id",
            #     )
            # }
            # moves_out_res_past = {
            #     item["product_id"][0]: item["product_qty"]
            #     for item in Move.read_group(
            #         domain_move_out_done,
            #         ["product_id", "product_qty"],
            #         ["product_id"],
            #         orderby="id",
            #     )
            # }
            moves_in_res_past = {
                item["product_id"][0]: item["product_qty"]
                for item in Move.read_group(
                    domain_move_in_done,
                    ["product_id", "product_qty"],
                    ["product_id"],  # Grouping by product_id only
                    # orderby="id",  # Remove this (invalid in read_group)
                )
            }

            moves_out_res_past = {
                item["product_id"][0]: item["product_qty"]
                for item in Move.read_group(
                    domain_move_out_done,
                    ["product_id", "product_qty"],
                    ["product_id"],  # Grouping by product_id only
                    # orderby="id",  # Remove this (invalid in read_group)
                )
            }
        res = dict()
        for product in self.with_context(prefetch_fields=False):
            product_id = product.id
            if not product_id:
                res[product_id] = 0.0
                continue
            rounding = product.uom_id.rounding
            res[product_id] = {}
            if dates_in_the_past:
                qty_available = (
                    quants_res.get(product_id, [0.0])[0]
                    - moves_in_res_past.get(product_id, 0.0)
                    + moves_out_res_past.get(product_id, 0.0)
                )
            else:
                qty_available = quants_res.get(product_id, [0.0])[0]
            res[product_id] = float_round(qty_available, precision_rounding=rounding)

        return res
