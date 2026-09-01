import logging


_logger = logging.getLogger(__name__)

TARGET_SELLING_COMPANY = (
    "SULATN FOUZAN AL-FOUZAN Co. for Machinery and Equipment."
)


def post_init_hook(env):
    """Backfill vehicles currently delivered to customers for the target company."""
    company = env["res.company"].sudo().search(
        [("name", "=", TARGET_SELLING_COMPANY)], limit=1
    )
    if not company:
        _logger.warning(
            "Vehicle registry backfill skipped: company %r was not found",
            TARGET_SELLING_COMPANY,
        )
        return

    env.cr.execute(
        """
        WITH customer_lots AS (
            SELECT
                quant.lot_id,
                quant.product_id
            FROM stock_quant AS quant
            JOIN stock_location AS location ON location.id = quant.location_id
            JOIN stock_lot AS lot ON lot.id = quant.lot_id
            WHERE lot.company_id = %s
              AND location.usage = 'customer'
            GROUP BY quant.lot_id, quant.product_id
            HAVING SUM(quant.quantity) > 0
        ),
        delivery_candidates AS (
            SELECT
                move_line.lot_id,
                move_line.product_id,
                picking.id AS delivery_id,
                picking.sale_id,
                picking.origin,
                picking.partner_id AS delivery_partner_id,
                picking.date_done AS delivery_date,
                ROW_NUMBER() OVER (
                    PARTITION BY move_line.lot_id, move_line.product_id
                    ORDER BY COALESCE(picking.date_done, move_line.date) DESC,
                             move_line.id DESC
                ) AS candidate_rank
            FROM stock_move_line AS move_line
            JOIN stock_location AS source ON source.id = move_line.location_id
            JOIN stock_location AS destination
                ON destination.id = move_line.location_dest_id
            JOIN stock_picking AS picking ON picking.id = move_line.picking_id
            WHERE move_line.company_id = %s
              AND move_line.state = 'done'
              AND move_line.lot_id IS NOT NULL
              AND move_line.quantity > 0
              AND source.usage <> 'customer'
              AND destination.usage = 'customer'
        )
        SELECT
            customer_lots.lot_id,
            customer_lots.product_id,
            candidate.delivery_id,
            COALESCE(candidate.sale_id, origin_sale.id) AS sale_id,
            COALESCE(
                direct_sale.partner_id,
                origin_sale.partner_id,
                candidate.delivery_partner_id
            ) AS customer_id,
            candidate.delivery_date
        FROM customer_lots
        JOIN delivery_candidates AS candidate
          ON candidate.lot_id = customer_lots.lot_id
         AND candidate.product_id = customer_lots.product_id
         AND candidate.candidate_rank = 1
        LEFT JOIN sale_order AS direct_sale ON direct_sale.id = candidate.sale_id
        LEFT JOIN sale_order AS origin_sale
          ON candidate.sale_id IS NULL
         AND origin_sale.company_id = %s
         AND origin_sale.name = candidate.origin
        """,
        (company.id, company.id, company.id),
    )
    rows = env.cr.fetchall()

    Registry = env["vehicle.after.sales.registry"].sudo()
    Mapping = env["vehicle.after.sales.local.lot"].sudo()
    Lot = env["stock.lot"].sudo()
    Product = env["product.product"].sudo()
    Partner = env["res.partner"].sudo()
    created = updated = skipped = 0

    product_ids = {row[1] for row in rows if row[4]}
    Product.browse(product_ids).mapped("product_tmpl_id").write(
        {"is_vehicle_after_sales": True}
    )

    for lot_id, product_id, delivery_id, sale_id, customer_id, delivery_date in rows:
        if not customer_id:
            skipped += 1
            continue
        lot = Lot.browse(lot_id)
        product = Product.browse(product_id)
        customer = Partner.browse(customer_id).commercial_partner_id
        vals = {
            "vin": lot.name,
            "product_id": product.id,
            "customer_id": customer.id,
            "selling_company_id": company.id,
            "original_lot_id": lot.id,
            "sale_order_id": sale_id or False,
            "delivery_id": delivery_id,
            "delivery_date": delivery_date,
            "warranty_months": product.product_tmpl_id.vehicle_warranty_months or 0,
        }
        registry = Registry.search(
            [("vin", "=", lot.name), ("product_id", "=", product.id)], limit=1
        )
        if registry:
            registry.write(vals)
            updated += 1
        else:
            registry = Registry.create(vals)
            created += 1
        if not Mapping.search_count(
            [("vehicle_id", "=", registry.id), ("company_id", "=", company.id)]
        ):
            Mapping.create(
                {
                    "vehicle_id": registry.id,
                    "company_id": company.id,
                    "lot_id": lot.id,
                }
            )

    _logger.info(
        "Vehicle registry backfill complete for %s: created=%d updated=%d skipped=%d",
        company.display_name,
        created,
        updated,
        skipped,
    )
