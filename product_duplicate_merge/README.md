# Product Duplicate Merge - Odoo 19

Detects product variants whose names match after trimming/collapsing whitespace while preserving case.

## Workflow
1. Inventory > Configuration > Product Data Cleaning > Detect Exact-Name Duplicates
2. Review proposed groups and choose the master product.
3. Automatic checks block risky merges.
4. Merge migrates unreserved, untracked internal on-hand quantities using Odoo inventory APIs, copies selected future-facing master data, and archives duplicate products.

## Important safeguards
Blocked when any of these are detected:
- different UoM
- lot/serial tracking
- different product category
- different storable type
- different companies
- different standard cost
- reserved internal stock
- open stock moves

Historical stock moves are deliberately NOT rewritten.

## Strong recommendation
Install and validate first on a restored copy/qualification database. Review accounting valuation after sample merges before production use.
