{
    "name": "Multi-Company Vehicle After Sales",
    "version": "19.0.1.0.1",
    "category": "Services/Helpdesk",
    "summary": "Cross-company vehicle warranty, workshop reception and repair traceability by VIN",
    "license": "LGPL-3",
    "author": "OpenAI",
    "depends": ["sale_stock", "stock", "repair", "helpdesk"],
    "data": [
        "security/ir.model.access.csv",
        "views/product_views.xml",
        "views/vehicle_registry_views.xml",
        "views/helpdesk_ticket_views.xml",
        "views/repair_order_views.xml",
    ],
    "installable": True,
    "application": True,
    "post_init_hook": "post_init_hook",
}
