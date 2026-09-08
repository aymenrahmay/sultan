def migrate(cr, version):
    """Populate the existing column after converting it to a stored related field."""
    cr.execute("""
        UPDATE vehicle_after_sales_registry AS registry
           SET delivery_address_id = sale.partner_shipping_id
          FROM sale_order AS sale
         WHERE registry.sale_order_id = sale.id
           AND registry.delivery_address_id IS DISTINCT FROM sale.partner_shipping_id
    """)
