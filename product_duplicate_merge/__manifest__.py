{
    'name': 'Product Duplicate Merge',
    'version': '19.0.1.0.0',
    'summary': 'Detect exact-name duplicate products and safely propose/execute merges',
    'category': 'Inventory/Inventory',
    'author': 'Custom',
    'license': 'LGPL-3',
    'depends': ['product', 'stock', 'stock_account', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_duplicate_merge_views.xml',
        'views/product_duplicate_merge_menus.xml',
    ],
    'installable': True,
    'application': False,
}
