# controllers/main.py
from odoo import http
from odoo.http import request

from odoo.addons.hr_attendance.controllers.main import HrAttendance


class HrAttendanceAllCompanies(HrAttendance):

    def _get_all_company_ids(self):
        return request.env["res.company"].sudo().search([]).ids

    @http.route()
    def employee_info(self, employee_id, token=None, **kwargs):
        employee = request.env["hr.employee"].sudo().with_context(
            allowed_company_ids=self._get_all_company_ids()
        ).browse(employee_id)

        if employee.exists():
            return self._get_employee_info_response(employee)

        return {}

    @http.route()
    def attendance_employee_data(self, token=None, **kwargs):
        request.update_env(
            user=request.env.ref("base.public_user").id,
            context=dict(
                request.env.context,
                allowed_company_ids=self._get_all_company_ids(),
            ),
        )
        return super().attendance_employee_data(token=token, **kwargs)