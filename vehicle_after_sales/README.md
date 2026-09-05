# Multi-Company Vehicle After Sales — Odoo 19 Enterprise

## Purpose
Company A sells and delivers serialized vehicles. Company B is the workshop.
The customer may visit Company B many times during or after warranty.

## Business flow
1. On the vehicle product, enable **Vehicle / VIN After-Sales** and set warranty months.
2. Company A sells/delivers normally with serial/VIN tracking.
3. On validation of the outbound delivery, the module creates/updates one master **Vehicle / VIN Registry** record.
4. Company B creates a Helpdesk ticket and selects the vehicle/VIN.
5. Click **1. Receive Vehicle**. A customer -> workshop operation is created and validated automatically.
6. Click **2. Create / Open Repair**. A standard Repair Order is created using the Company B operational serial and workshop location.
7. Complete the repair normally. If warranty date is valid AND **Warranty Coverage Approved** is checked, the Repair is flagged under warranty where the Odoo field is available.
8. Click **3. Return Vehicle** to validate workshop -> customer movement.

## VIN design
When a customer returns a sold car, open its registry and click **Cancel Registry**.
The record is archived: it disappears from active VIN selections and cannot be
assigned to new Helpdesk tickets or used for new workshop receipts or repairs.
Past tickets and repairs remain accessible, and an existing workshop visit can
still return the vehicle. Use the **Cancelled** filter to view cancelled registries.
Cancellation does not create an inventory return or credit note; process those
separately. A new validated sales delivery reactivates the same VIN for its new
customer. Reprocessing the cancelled original delivery does not reactivate it.

The registry is the single business identity for a VIN.
Odoo stock lots can be company-isolated. Company A keeps the original sold lot. When Company B receives the vehicle, the module creates ONE company-specific operational lot using the sold lot name plus `_repaire` and reuses it on every future workshop visit. It never creates a new serial for each repair.

## Customer ownership
The receipt/return code uses stock owner/consignment fields when present in the installed Odoo build, so the physical vehicle can be present in the workshop without being treated as company-owned stock where Odoo supports this mechanism.

## Required apps
- Sales
- Inventory
- Repair
- Helpdesk (Enterprise)

## Notes before production
Test on a staging database with your accounting/stock valuation configuration. Vehicle valuation and consignment behavior should be validated with your accounting rules before production rollout.
