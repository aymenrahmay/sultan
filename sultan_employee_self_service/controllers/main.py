import hmac
from datetime import timedelta

from odoo import _, fields, http
from odoo.exceptions import UserError, ValidationError
from odoo.http import request


class EmployeeSelfService(http.Controller):
    SESSION_EMPLOYEE_KEY = "sultan_self_service_employee_id"
    SESSION_LOGIN_KEY = "sultan_self_service_login"

    def _employee(self):
        employee_id = request.session.get(self.SESSION_EMPLOYEE_KEY)
        session_login = request.session.get(self.SESSION_LOGIN_KEY, "")
        if not employee_id or not session_login:
            return request.env["hr.employee"]
        employee = request.env["hr.employee"].sudo().browse(int(employee_id)).exists()
        if (
            not employee
            or not employee.active
            or not employee.self_service_enabled
            or not employee.self_service_login
            or not hmac.compare_digest(employee.self_service_login, session_login)
        ):
            self._clear_session()
            return request.env["hr.employee"]
        return employee

    def _clear_session(self):
        request.session.pop(self.SESSION_EMPLOYEE_KEY, None)
        request.session.pop(self.SESSION_LOGIN_KEY, None)

    def _require_employee(self):
        employee = self._employee()
        if not employee:
            return employee, request.redirect("/employee/self-service")
        return employee, None

    def _base_values(self, employee, **extra):
        return {"employee": employee, **extra}

    def _leave_types_and_balances(self, employee):
        leave_types = request.env["hr.leave.type"].sudo().with_company(employee.company_id).search([
            ("self_service_visible", "=", True),
            "|", ("company_id", "=", False), ("company_id", "=", employee.company_id.id)
        ], order="sequence, id")
        allocation_data = leave_types.get_allocation_data(employee).get(employee, [])
        balance_by_type = {item[3]: item[1] for item in allocation_data}
        result = []
        for leave_type in leave_types:
            data = balance_by_type.get(leave_type.id, {})
            if leave_type.requires_allocation and not data.get("max_leaves"):
                continue
            result.append({
                "record": leave_type,
                "remaining": data.get("virtual_remaining_leaves") if data else None,
                "unit": leave_type.request_unit,
            })
        return result

    @http.route("/employee/self-service", type="http", auth="public", website=True, methods=["GET", "POST"], sitemap=False)
    def login(self, **post):
        employee = self._employee()
        if employee:
            return request.redirect("/employee/self-service/dashboard")
        error = False
        if request.httprequest.method == "POST":
            login = (post.get("self_service_login") or "").strip()
            employee = request.env["hr.employee"].sudo().search([
                ("self_service_login", "=", login),
                ("self_service_enabled", "=", True),
                ("active", "=", True),
            ], limit=1)
            if employee:
                request.session[self.SESSION_EMPLOYEE_KEY] = employee.id
                request.session[self.SESSION_LOGIN_KEY] = employee.self_service_login
                return request.redirect("/employee/self-service/dashboard")
            error = _("The code is not valid. Please check it and try again.")
        return request.render("sultan_employee_self_service.login", {"error": error})

    @http.route("/employee/self-service/logout", type="http", auth="public", website=True, sitemap=False)
    def logout(self):
        self._clear_session()
        return request.redirect("/employee/self-service")

    @http.route("/employee/self-service/dashboard", type="http", auth="public", website=True, sitemap=False)
    def dashboard(self, message=None, error=None):
        employee, response = self._require_employee()
        if response:
            return response
        open_attendance = request.env["hr.attendance"].sudo().search([
            ("employee_id", "=", employee.id), ("check_out", "=", False)
        ], order="check_in desc", limit=1)
        return request.render("sultan_employee_self_service.dashboard", self._base_values(
            employee,
            open_attendance=open_attendance,
            balances=self._leave_types_and_balances(employee),
            message=message,
            error=error,
        ))

    @http.route("/employee/self-service/attendance/toggle", type="http", auth="public", website=True, methods=["POST"], csrf=True, sitemap=False)
    def attendance_toggle(self, **post):
        employee, response = self._require_employee()
        if response:
            return response
        employee.sudo()._attendance_action_change({
            "mode": "self_service",
            "ip_address": request.httprequest.remote_addr,
            "browser": request.httprequest.user_agent.browser,
        })
        status = _("Checked in successfully.") if employee.attendance_state == "checked_in" else _("Checked out successfully.")
        return request.redirect("/employee/self-service/dashboard?message=%s" % status)

    @http.route("/employee/self-service/leaves", type="http", auth="public", website=True, sitemap=False)
    def leaves(self, message=None, error=None):
        employee, response = self._require_employee()
        if response:
            return response
        leaves = request.env["hr.leave"].sudo().search([
            ("employee_id", "=", employee.id)
        ], order="request_date_from desc, id desc", limit=50)
        return request.render("sultan_employee_self_service.leaves", self._base_values(
            employee,
            balances=self._leave_types_and_balances(employee),
            leaves=leaves,
            message=message,
            error=error,
            today=fields.Date.today(),
        ))

    @http.route("/employee/self-service/leaves/create", type="http", auth="public", website=True, methods=["POST"], csrf=True, sitemap=False)
    def leave_create(self, **post):
        employee, response = self._require_employee()
        if response:
            return response
        try:
            date_from = fields.Date.to_date(post.get("date_from"))
            date_to = fields.Date.to_date(post.get("date_to"))
            leave_type = request.env["hr.leave.type"].sudo().browse(int(post.get("leave_type_id", 0))).exists()
            allowed_ids = {item["record"].id for item in self._leave_types_and_balances(employee)}
            if not leave_type or leave_type.id not in allowed_ids:
                raise ValidationError(_("Please select an available time-off type."))
            if not date_from or not date_to or date_from > date_to:
                raise ValidationError(_("Please enter a valid date range."))
            request.env["hr.leave"].sudo().with_company(employee.company_id).create({
                "employee_id": employee.id,
                "holiday_status_id": leave_type.id,
                "request_date_from": date_from,
                "request_date_to": date_to,
                "private_name": (post.get("description") or "").strip() or _("Self-service request"),
            })
        except (ValueError, UserError, ValidationError) as exc:
            return self.leaves(error=str(exc))
        return request.redirect("/employee/self-service/leaves?message=%s" % _("Your request was submitted."))

    @http.route("/employee/self-service/profile", type="http", auth="public", website=True, methods=["GET", "POST"], csrf=True, sitemap=False)
    def profile(self, **post):
        employee, response = self._require_employee()
        if response:
            return response
        message = False
        if request.httprequest.method == "POST":
            def clean(name):
                return (post.get(name) or "").strip() or False

            def date_value(name):
                value = clean(name)
                return fields.Date.to_date(value) if value else False

            def positive_integer(name):
                value = clean(name)
                if not value:
                    return 0
                return max(0, int(value))

            countries = request.env["res.country"].sudo()
            country = countries.browse(int(post.get("country_id") or 0)).exists()
            birth_country = countries.browse(int(post.get("country_of_birth") or 0)).exists()
            private_country = countries.browse(int(post.get("private_country_id") or 0)).exists()
            private_state = request.env["res.country.state"].sudo().browse(int(post.get("private_state_id") or 0)).exists()
            if private_state and private_country and private_state.country_id != private_country:
                private_state = request.env["res.country.state"]

            sex = clean("sex")
            if sex not in ("male", "female", "other"):
                sex = False
            marital = clean("marital")
            if marital not in ("single", "married", "cohabitant", "widower", "divorced"):
                marital = "single"
            certificate = clean("certificate")
            if certificate not in ("graduate", "bachelor", "master", "doctor", "other"):
                certificate = False

            employee.sudo().write({
                "legal_name": clean("legal_name"),
                "private_email": (post.get("private_email") or "").strip() or False,
                "private_phone": (post.get("private_phone") or "").strip() or False,
                "birthday": date_value("birthday"),
                "birthday_public_display": post.get("birthday_public_display") == "on",
                "place_of_birth": clean("place_of_birth"),
                "country_of_birth": birth_country.id or False,
                "sex": sex,
                "country_id": country.id or False,
                "identification_id": clean("identification_id"),
                "ssnid": clean("ssnid"),
                "passport_id": clean("passport_id"),
                "passport_expiration_date": date_value("passport_expiration_date"),
                "visa_no": clean("visa_no"),
                "visa_expire": date_value("visa_expire"),
                "permit_no": clean("permit_no"),
                "work_permit_expiration_date": date_value("work_permit_expiration_date"),
                "emergency_contact": clean("emergency_contact"),
                "emergency_phone": clean("emergency_phone"),
                "private_street": clean("private_street"),
                "private_street2": clean("private_street2"),
                "private_city": clean("private_city"),
                "private_zip": clean("private_zip"),
                "private_country_id": private_country.id or False,
                "private_state_id": private_state.id or False,
                "distance_home_work": positive_integer("distance_home_work"),
                "distance_home_work_unit": clean("distance_home_work_unit") if clean("distance_home_work_unit") in ("kilometers", "miles") else "kilometers",
                "marital": marital,
                "spouse_complete_name": clean("spouse_complete_name"),
                "spouse_birthdate": date_value("spouse_birthdate"),
                "children": positive_integer("children"),
                "certificate": certificate,
                "study_field": clean("study_field"),
                "study_school": clean("study_school"),
            })
            message = _("Your information was updated.")
        return request.render("sultan_employee_self_service.profile", self._base_values(
            employee,
            message=message,
            countries=request.env["res.country"].sudo().search([], order="name"),
            states=request.env["res.country.state"].sudo().search([], order="name"),
        ))
