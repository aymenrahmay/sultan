{
    "name": "Sultan Employee Self Service",
    "version": "19.0.1.3.0",
    "category": "Human Resources",
    "summary": "Simple employee self-service for time off, attendance and personal details",
    "author": "Sultan",
    "license": "LGPL-3",
    "depends": ["website", "hr", "hr_attendance", "hr_holidays"],
    "data": [
        "views/hr_employee_views.xml",
        "views/hr_leave_type_views.xml",
        "views/self_service_templates.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "sultan_employee_self_service/static/src/scss/self_service.scss",
        ],
    },
    "installable": True,
    "application": False,
}
