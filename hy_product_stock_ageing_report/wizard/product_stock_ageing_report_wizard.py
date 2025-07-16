from odoo import fields, models


class ProductStockAgeingReportWizard(models.TransientModel):
    _name = "product.stock.ageing.report.wizard"
    _inherit = "product.stock.ageing.report.xlsx"
    _description = "Generate Product Stock Ageing Report"

    date = fields.Date(string="Date", required=True)
    location_ids = fields.Many2many(
        "stock.location",
        string="Locations",
        domain="[('usage','=','internal')]",
        required=True,
    )
    category_ids = fields.Many2many("product.category", string="Product Categories")
    xlsx_file = fields.Binary(string="Download Report")
    file_name = fields.Char(string="File Name")
    report_generated = fields.Boolean(string="Report Generated", default=False)

    def _get_report_name(self):
        """generate report file name"""
        report_name = "Product Stock Ageing Report"
        date_string = fields.Date.today()
        return f"{report_name} - {date_string}.xlsx"

    def action_generate_xlsx_report(self):
        data = {
            "date": self.date,
            "location_ids": self.location_ids.ids,
            "category_ids": self.category_ids.ids,
        }
        self.write(
            {
                "report_generated": True,
                "file_name": self._get_report_name(),
                "xlsx_file": self.generate_xlsx_report(data),
            }
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": "product.stock.ageing.report.wizard",
            "view_mode": "form",
            "res_id": self.id,
            "target": "new",
            "context": self.env.context,
        }
