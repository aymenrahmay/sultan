from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare


class ProductDuplicateMerge(models.Model):
    _name = 'product.duplicate.merge'
    _description = 'Product Duplicate Merge Proposal'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    # Risk is computed live and cannot be used in SQL ordering.
    _order = 'name, id'

    name = fields.Char(required=True, index=True, tracking=True)
    normalized_name = fields.Char(index=True, readonly=True)
    product_ids = fields.Many2many(
        'product.product',
        'product_duplicate_merge_product_rel',
        'merge_id', 'product_id',
        string='Duplicate Products',
        readonly=True,
    )
    product_count = fields.Integer(compute='_compute_metrics', store=False)
    master_product_id = fields.Many2one(
        'product.product', string='Master Product', tracking=True,
        domain="[('id', 'in', product_ids)]",
    )
    duplicate_product_ids = fields.Many2many(
        'product.product', compute='_compute_duplicate_products',
        string='Products to Merge', store=False,
    )
    total_qty = fields.Float(compute='_compute_metrics', digits='Product Unit of Measure')
    reserved_qty = fields.Float(compute='_compute_metrics', digits='Product Unit of Measure')
    state = fields.Selection([
        ('detected', 'Detected'),
        ('reviewed', 'Reviewed'),
        ('merged', 'Merged'),
        ('ignored', 'Ignored'),
    ], default='detected', required=True, tracking=True, index=True)
    risk_level = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('blocked', 'Blocked'),
    ], compute='_compute_risk', store=False)
    risk_message = fields.Text(compute='_compute_risk', store=False)
    company_ids = fields.Many2many('res.company', compute='_compute_metrics', string='Companies')
    merged_at = fields.Datetime(readonly=True)
    merged_by = fields.Many2one('res.users', readonly=True)

    @staticmethod
    def _normalize_name(name):
        # "Exact" matching with harmless whitespace normalization only.
        # Case remains significant: ABC != abc.
        return ' '.join((name or '').strip().split())

    @api.depends('product_ids', 'master_product_id')
    def _compute_duplicate_products(self):
        for rec in self:
            rec.duplicate_product_ids = rec.product_ids - rec.master_product_id

    @api.depends('product_ids')
    def _compute_metrics(self):
        Quant = self.env['stock.quant']
        for rec in self:
            rec.product_count = len(rec.product_ids)
            rec.company_ids = rec.product_ids.mapped('company_id')
            if not rec.product_ids:
                rec.total_qty = 0.0
                rec.reserved_qty = 0.0
                continue
            quants = Quant.search([
                ('product_id', 'in', rec.product_ids.ids),
                ('location_id.usage', '=', 'internal'),
            ])
            rec.total_qty = sum(quants.mapped('quantity'))
            rec.reserved_qty = sum(quants.mapped('reserved_quantity'))

    @api.depends('product_ids', 'master_product_id')
    def _compute_risk(self):
        Quant = self.env['stock.quant']
        for rec in self:
            issues = []
            blockers = []
            products = rec.product_ids
            master = rec.master_product_id

            if len(products) < 2:
                blockers.append(_('Less than two products in the group.'))
            if not master:
                issues.append(_('Select a master product.'))

            if len(products.mapped('uom_id')) > 1:
                blockers.append(_('Different units of measure.'))
            if len(set(products.mapped('tracking'))) > 1:
                blockers.append(_('Different tracking methods (none/lot/serial).'))
            if any(p.tracking != 'none' for p in products):
                blockers.append(_('Lot/serial tracked products require manual review.'))
            if len(products.mapped('categ_id')) > 1:
                blockers.append(_('Different product categories / valuation configuration.'))
            if len(set(products.mapped('is_storable'))) > 1:
                blockers.append(_('Different product storage types.'))

            companies = products.mapped('company_id').filtered(lambda c: c)
            if len(companies) > 1:
                blockers.append(_('Products belong to different companies.'))

            if master and products.filtered(lambda p: p.is_storable):
                # Cost differences can generate unintended accounting valuation differences.
                precision = self.env['decimal.precision'].precision_get('Product Price') or 2
                for p in products - master:
                    if float_compare(p.standard_price, master.standard_price, precision_digits=precision) != 0:
                        blockers.append(_('Different product costs detected.'))
                        break

            quants = Quant.search([
                ('product_id', 'in', products.ids),
                ('location_id.usage', '=', 'internal'),
                ('reserved_quantity', '!=', 0),
            ]) if products else Quant
            if quants:
                blockers.append(_('Reserved stock exists. Unreserve/cancel reservations before merging.'))

            # Open stock moves are intentionally blocked: they would still reference duplicate IDs.
            open_moves = self.env['stock.move'].search_count([
                ('product_id', 'in', products.ids),
                ('state', 'not in', ['done', 'cancel']),
            ]) if products else 0
            if open_moves:
                blockers.append(_('%s open stock movement(s) still reference these products.') % open_moves)

            if blockers:
                rec.risk_level = 'blocked'
                rec.risk_message = '\n'.join('• %s' % x for x in blockers + issues)
            elif issues:
                rec.risk_level = 'medium'
                rec.risk_message = '\n'.join('• %s' % x for x in issues)
            else:
                rec.risk_level = 'low'
                rec.risk_message = _('No blocking issue detected by the automatic checks.')

    @api.model
    def action_detect_duplicates(self):
        """Detect active + archived product variants with exact normalized names."""
        Product = self.env['product.product'].with_context(active_test=False)
        products = Product.search([('name', '!=', False)])
        buckets = defaultdict(lambda: self.env['product.product'])
        display_name = {}
        for product in products:
            key = self._normalize_name(product.name)
            if not key:
                continue
            buckets[key] |= product
            display_name.setdefault(key, product.name.strip())

        existing = {
            x.normalized_name: x
            for x in self.search([('state', 'in', ['detected', 'reviewed'])])
        }
        created_or_updated = self.browse()
        for key, group in buckets.items():
            if len(group) < 2:
                continue
            proposal = existing.get(key)
            vals = {
                'name': display_name[key],
                'normalized_name': key,
                'product_ids': [(6, 0, group.ids)],
            }
            if proposal:
                proposal.write(vals)
            else:
                # Master proposal: stocked first, then default_code, then oldest ID.
                ranked = sorted(
                    group,
                    key=lambda p: (
                        -(p.qty_available or 0.0),
                        0 if p.default_code else 1,
                        p.id,
                    ),
                )
                vals['master_product_id'] = ranked[0].id
                proposal = self.create(vals)
            created_or_updated |= proposal

        return {
            'type': 'ir.actions.act_window',
            'name': _('Duplicate Products'),
            'res_model': self._name,
            'view_mode': 'list,form',
            'domain': [('id', 'in', created_or_updated.ids)],
            'context': {'search_default_detected': 1},
        }

    def action_mark_reviewed(self):
        self.write({'state': 'reviewed'})

    def action_ignore(self):
        self.write({'state': 'ignored'})

    def _check_can_merge(self):
        self.ensure_one()
        if not self.master_product_id:
            raise ValidationError(_('Select the master product first.'))
        if self.master_product_id not in self.product_ids:
            raise ValidationError(_('The master product must belong to the duplicate group.'))
        # Force computation now.
        if self.risk_level == 'blocked':
            raise UserError(_('Merge blocked:\n%s') % (self.risk_message or ''))
        if len(self.product_ids) < 2:
            raise UserError(_('Nothing to merge.'))

    def _migrate_internal_stock(self, source, target):
        """Move on-hand stock identity source -> target, preserving quant dimensions.

        Uses Odoo inventory adjustment APIs instead of SQL. Only internal locations,
        unreserved and untracked stock are accepted by the pre-checks.
        """
        Quant = self.env['stock.quant'].sudo()
        source_quants = Quant.search([
            ('product_id', '=', source.id),
            ('location_id.usage', '=', 'internal'),
            ('quantity', '!=', 0),
        ])
        for sq in source_quants:
            if sq.reserved_quantity:
                raise UserError(_('Reserved stock found for %s.') % source.display_name)
            if sq.lot_id:
                raise UserError(_('Lot/serial stock found for %s.') % source.display_name)

            qty = sq.quantity
            target_quant = Quant.search([
                ('product_id', '=', target.id),
                ('location_id', '=', sq.location_id.id),
                ('lot_id', '=', sq.lot_id.id or False),
                ('package_id', '=', sq.package_id.id or False),
                ('owner_id', '=', sq.owner_id.id or False),
                ('company_id', '=', sq.company_id.id),
            ], limit=1)
            if not target_quant:
                target_quant = Quant.with_context(inventory_mode=True).create({
                    'product_id': target.id,
                    'location_id': sq.location_id.id,
                    'lot_id': sq.lot_id.id or False,
                    'package_id': sq.package_id.id or False,
                    'owner_id': sq.owner_id.id or False,
                    'company_id': sq.company_id.id,
                    'inventory_quantity': qty,
                })
                target_quant.action_apply_inventory()
            else:
                target_quant.inventory_quantity = target_quant.quantity + qty
                target_quant.action_apply_inventory()

            sq.inventory_quantity = 0.0
            sq.action_apply_inventory()

    def _migrate_master_data(self, source, target):
        """Move safe future-facing references. Historical done moves are left untouched."""
        # Reordering rules can safely be pointed to the master after open stock moves are cleared.
        self.env['stock.warehouse.orderpoint'].sudo().search([
            ('product_id', '=', source.id),
        ]).write({'product_id': target.id})

        # Supplier pricelist belongs to template.
        suppliers = self.env['product.supplierinfo'].sudo().search([
            ('product_tmpl_id', '=', source.product_tmpl_id.id),
        ])
        # Avoid uniqueness/business conflicts by only copying missing supplier rows.
        for supplier in suppliers:
            exists = self.env['product.supplierinfo'].sudo().search_count([
                ('product_tmpl_id', '=', target.product_tmpl_id.id),
                ('partner_id', '=', supplier.partner_id.id),
                ('min_qty', '=', supplier.min_qty),
            ])
            if not exists:
                supplier.copy({'product_tmpl_id': target.product_tmpl_id.id})

    def action_merge(self):
        for rec in self:
            rec._check_can_merge()
            master = rec.master_product_id.sudo()
            duplicates = (rec.product_ids - master).sudo()

            for source in duplicates:
                rec._migrate_internal_stock(source, master)
                rec._migrate_master_data(source, master)
                # Archive source rather than deleting history.
                source.active = False
                if source.product_tmpl_id.product_variant_count == 1:
                    source.product_tmpl_id.active = False

            rec.write({
                'state': 'merged',
                'merged_at': fields.Datetime.now(),
                'merged_by': self.env.user.id,
            })
            rec.message_post(body=_('Merged into master product: %s') % master.display_name)
        return True
