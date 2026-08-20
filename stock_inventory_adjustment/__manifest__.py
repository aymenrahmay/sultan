{
    "name": "Stock Inventory Adjustment",
    "version": "19.0.1.8.0",
    "category": "Warehouse",
    "website": "https://odootips.com",
    "summary": """
        Update stock via Inventory Adjustment Screen, inventory adjustment, stock inventory adjustment, inventory count, stock count,
        stocktaking, physical inventory,update quantity on hand,counted quantity,inventory by location,inventory by warehouse,
        inventory by category,inventory import,import stock inventory, import inventory adjustment, import inventory from Excel,
        import inventory from CSV,bulk inventory import,mass inventory update,opening stock import
    """,
    "author": "QoriTech",
    "license": "LGPL-3",
    "depends": [
        "base",
        "stock"
    ],
    "external_dependencies": {"python": ["pandas", "openpyxl"]},
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/qt_stock_inventory_views.xml",
        "report/report.xml",
        "report/inventory_report_template.xml",
    ],

    "images": ["static/description/banner_grid.png"],
    "live_test_url": "https://youtu.be/eDgSOnI94E4",
    "installable": True,
    "auto_install": False,
    "price": 20,
    "currency": "USD",

}
