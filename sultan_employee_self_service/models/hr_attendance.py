from odoo import fields, models


class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    in_mode = fields.Selection(
        selection_add=[("self_service", "Self Service")],
        ondelete={"self_service": "set default"},
    )
    out_mode = fields.Selection(
        selection_add=[("self_service", "Self Service")],
        ondelete={"self_service": "set default"},
    )
