from odoo import fields, models


class HrLeaveType(models.Model):
    _inherit = "hr.leave.type"

    self_service_visible = fields.Boolean(
        string="Visible on Self-Service",
        default=False,
        help="Employees can see the balance and submit self-service requests for this time-off type.",
    )
