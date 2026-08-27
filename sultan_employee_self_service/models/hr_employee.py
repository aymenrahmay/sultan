import secrets

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    self_service_login = fields.Char(
        string="Self-Service Login",
        copy=False,
        index=True,
        groups="hr.group_hr_user",
        help="Secret code used by the employee to open the self-service page.",
    )
    self_service_enabled = fields.Boolean(
        string="Self-Service Enabled",
        default=True,
        groups="hr.group_hr_user",
    )

    _self_service_login_unique = models.Constraint(
        "UNIQUE(self_service_login)",
        "The self-service login must be unique.",
    )

    @api.constrains("self_service_login")
    def _check_self_service_login(self):
        for employee in self:
            if employee.self_service_login and len(employee.self_service_login.strip()) < 4:
                raise ValidationError(_("The self-service login must contain at least 8 characters."))

    def action_generate_self_service_login(self):
        for employee in self:
            employee.self_service_login = secrets.token_urlsafe(12)
        return True
