import base64
from datetime import datetime, time
import io
import xlsxwriter

from odoo import models, _
from odoo.exceptions import UserError

from .utils import sorted_zip_longest, get_dataframe, get_stock_age_qty


class ProductStockAgeingReportXlsx(models.AbstractModel):
    _name = "product.stock.ageing.report.xlsx"
    _description = "Abstract Model for Product Stock Ageing Report"

    def generate_xlsx_report(self, data):

        location_ids = self.env["stock.location"].search([("id", "in", data["location_ids"])])
        location_names = ",".join(location_ids.mapped("name"))

        if selected_category_ids := data.get("category_ids", False):
            category_ids = self.env["product.category"].search([("id", "in", selected_category_ids)])
            category_names = ",".join(category_ids.mapped("name"))
        else:
            category_ids = self.env["product.category"].search([])
            category_names = "All Product Categories"

        location_ids = tuple(location_ids.ids)
        category_ids = tuple(category_ids.ids)

        reference_date = str(datetime.combine(data["date"], time(hour=23, minute=59, second=59)))

        row = 12

        zerotothirty_query = f"""
            select pp.id,pt.name,
            um.name as uom,
            sum(sml.quantity) as zerotothirty
            from stock_move_line sml
            join product_product pp on pp.id = sml.product_id
            join product_template pt on pt.id = pp.product_tmpl_id
            join uom_uom um on um.id = pt.uom_id
            where pt.categ_id in %s
            and pp.active != 'f'
            and sml.location_dest_id in %s
            and sml.state = 'done'
            and EXTRACT(DAY FROM ('{reference_date}'- sml.date)) <= 30
            group by pp.id,pt.name,um.name;
        """
        self.env.cr.execute(zerotothirty_query, (category_ids, location_ids))
        zerotothirty_data = self.env.cr.dictfetchall()

        thirtyonetosixty_query = f"""
            select pp.id,pt.name,
            um.name as uom,
            sum(sml.quantity) as thirtyonetosixty
            from stock_move_line sml
            join product_product pp on pp.id = sml.product_id
            join product_template pt on pt.id = pp.product_tmpl_id
            join uom_uom um on um.id = pt.uom_id
            where pt.categ_id in %s
            and pp.active != 'f'
            and sml.location_dest_id in %s
            and sml.state = 'done'
            and EXTRACT(DAY FROM ('{reference_date}'- date)) > 30
            and EXTRACT(DAY FROM ('{reference_date}'- date)) <= 60
            group by pp.id,pt.name,um.name;
        """
        self.env.cr.execute(thirtyonetosixty_query, (category_ids, location_ids))
        thirtyonetosixty_data = self.env.cr.dictfetchall()

        sixtyonetoninty_query = f"""
            select pp.id,pt.name,
            um.name as uom,
            sum(sml.quantity) as sixtyonetoninty
            from stock_move_line sml
            join product_product pp on pp.id = sml.product_id
            join product_template pt on pt.id = pp.product_tmpl_id
            join uom_uom um on um.id = pt.uom_id
            where pt.categ_id in %s
            and pp.active != 'f'
            and sml.location_dest_id in %s
            and sml.state = 'done'
            and EXTRACT(DAY FROM ('{reference_date}'- date)) > 60
            and EXTRACT(DAY FROM ('{reference_date}'- date)) <= 90
            group by pp.id,pt.name,um.name;
        """
        self.env.cr.execute(sixtyonetoninty_query, (category_ids, location_ids))
        sixtyonetoninty_data = self.env.cr.dictfetchall()

        nintyonetoonetwenty_query = f"""
            select pp.id,pt.name,
            um.name as uom,
            sum(sml.quantity) as nintyonetoonetwenty
            from stock_move_line sml
            join product_product pp on pp.id = sml.product_id
            join product_template pt on pt.id = pp.product_tmpl_id
            join uom_uom um on um.id = pt.uom_id
            where pt.categ_id in %s
            and pp.active != 'f'
            and sml.location_dest_id in %s
            and sml.state = 'done'
            and EXTRACT(DAY FROM ('{reference_date}'- date)) > 90
            and EXTRACT(DAY FROM ('{reference_date}'- date)) <= 120
            group by pp.id,pt.name,um.name;
        """
        self.env.cr.execute(nintyonetoonetwenty_query, (category_ids, location_ids))
        nintyonetoonetwenty_data = self.env.cr.dictfetchall()

        onetwentyonetotwofourty_query = f"""
            select pp.id,pt.name,
            um.name as uom,
            sum(sml.quantity) as onetwentyonetotwofourty
            from stock_move_line sml
            join product_product pp on pp.id = sml.product_id
            join product_template pt on pt.id = pp.product_tmpl_id
            join uom_uom um on um.id = pt.uom_id
            where pt.categ_id in %s
            and pp.active != 'f'
            and sml.location_dest_id in %s
            and sml.state = 'done'
            and EXTRACT(DAY FROM ('{reference_date}'- date)) > 120
            and EXTRACT(DAY FROM ('{reference_date}'- date)) <= 240
            group by pp.id,pt.name,um.name;
        """
        self.env.cr.execute(onetwentyonetotwofourty_query, (category_ids, location_ids))
        onetwentyonetotwofourty_data = self.env.cr.dictfetchall()

        twofourtytothreesixty_query = f"""
            select pp.id,pt.name,
            um.name as uom,
            sum(sml.quantity) as twofourtytothreesixty
            from stock_move_line sml
            join product_product pp on pp.id = sml.product_id
            join product_template pt on pt.id = pp.product_tmpl_id
            join uom_uom um on um.id = pt.uom_id
            where pt.categ_id in %s
            and pp.active != 'f'
            and sml.location_dest_id in %s
            and sml.state = 'done'
            and EXTRACT(DAY FROM ('{reference_date}'- date)) > 240
            and EXTRACT(DAY FROM ('{reference_date}'- date)) <= 360
            group by pp.id,pt.name,um.name;
        """
        self.env.cr.execute(twofourtytothreesixty_query, (category_ids, location_ids))
        twofourtytothreesixty_data = self.env.cr.dictfetchall()

        threesixtyplus_query = f"""
            select pp.id,pt.name,
            um.name as uom,
            sum(sml.quantity) as threesixtyplus
            from stock_move_line sml
            join product_product pp on pp.id = sml.product_id
            join product_template pt on pt.id = pp.product_tmpl_id
            join uom_uom um on um.id = pt.uom_id
            where pt.categ_id in %s
            and pp.active != 'f'
            and sml.location_dest_id in %s
            and sml.state = 'done'
            and EXTRACT(DAY FROM ('{reference_date}'- date)) > 360
            group by pp.id,pt.name,um.name;
        """
        self.env.cr.execute(threesixtyplus_query, (category_ids, location_ids))
        threesixtyplus_data = self.env.cr.dictfetchall()

        # Let's start combining two list of dicts
        zerotosixty_data = [
            {**u, **v} for u, v in sorted_zip_longest(zerotothirty_data, thirtyonetosixty_data, key="id")
        ]

        zerotoninty_data = [{**u, **v} for u, v in sorted_zip_longest(zerotosixty_data, sixtyonetoninty_data, key="id")]

        zerotoonetwenty_data = [
            {**u, **v} for u, v in sorted_zip_longest(zerotoninty_data, nintyonetoonetwenty_data, key="id")
        ]

        zerototwofourty_data = [
            {**u, **v} for u, v in sorted_zip_longest(zerotoonetwenty_data, onetwentyonetotwofourty_data, key="id")
        ]

        zerotothreesixty_data = [
            {**u, **v} for u, v in sorted_zip_longest(zerototwofourty_data, twofourtytothreesixty_data, key="id")
        ]

        zeroplus_data = [
            {**u, **v} for u, v in sorted_zip_longest(zerotothreesixty_data, threesixtyplus_data, key="id")
        ]

        dataframe = get_dataframe(zeroplus_data)
        if dataframe is False:
            raise UserError(_("No data found for your selection!"))

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        worksheet = workbook.add_worksheet("Product Stock Ageing Report")
        format1_header = workbook.add_format(
            {
                "bold": True,
                "align": "center",
                "valign": "vcenter",
                "border": 1,
                "bg_color": "#d9d9d9",
            }
        )
        format4_title = workbook.add_format(
            {
                "bold": True,
                "align": "center",
                "font_size": 24,
                "border": 1,
                "bg_color": "#d9d9d9",
            }
        )
        format5_align_left = workbook.add_format({"align": "left"})
        format6_content = workbook.add_format({"border": 1, "bold": True})
        format7_center = workbook.add_format({"align": "center"})
        format8_content_right = workbook.add_format({"align": "right", "num_format": "#0.00"})
        worksheet.set_row(0, 30)
        worksheet.set_row(7, 30)

        worksheet.set_column("A:A", 60)
        worksheet.set_column("B:B", 20)
        worksheet.set_column("C:C", 20)
        worksheet.set_column("D:D", 20)
        worksheet.set_column("E:E", 20)
        worksheet.set_column("F:F", 20)
        worksheet.set_column("G:G", 20)
        worksheet.set_column("H:H", 20)
        worksheet.set_column("I:I", 20)
        worksheet.set_column("J:J", 20)
        worksheet.merge_range("A1:J1", "Stock Ageing Report", format4_title)

        company = self.env.company
        company_name = company.name
        company_address = (
            company.partner_id.street
            if company.partner_id.street
            else "" + " " + company.partner_id.street2
            if company.partner_id.street2
            else ""
        )
        company_phone = company.partner_id.phone
        company_email = company.partner_id.email

        worksheet.merge_range("A2:B2", "Company Name", format6_content)
        worksheet.merge_range("C2:D2", company_name, format6_content)
        worksheet.merge_range("A3:B3", "Address", format6_content)
        worksheet.merge_range("C3:D3", company_address, format6_content)
        worksheet.merge_range("A4:B4", "Phone", format6_content)
        worksheet.merge_range("C4:D4", company_phone, format6_content)
        worksheet.merge_range("A5:B5", "Email", format6_content)
        worksheet.merge_range("C5:D5", company_email, format6_content)

        worksheet.merge_range("A6:J6", "")
        worksheet.write("A7", "Product Categories", format6_content)
        worksheet.merge_range("B7:J7", category_names, format6_content)
        worksheet.write("A8", "Locations", format6_content)
        worksheet.merge_range("B8:J8", location_names, format6_content)
        worksheet.write("A9", "Date", format6_content)
        lang_code = self.env.context.get("lang") or self.env.lang or "en_US"
        lang = self.env["res.lang"].search([("code", "=", lang_code)])
        worksheet.merge_range("B9:J9", datetime.strftime(data["date"], lang.date_format), format6_content)
        worksheet.merge_range("A10:J10", "")

        worksheet.write("A11", "Product", format1_header)
        worksheet.write("B11", "Unit of Measure", format1_header)
        worksheet.write("C11", "0-30", format1_header)
        worksheet.write("D11", "31-60", format1_header)
        worksheet.write("E11", "61-90", format1_header)
        worksheet.write("F11", "91-120", format1_header)
        worksheet.write("G11", "121-240", format1_header)
        worksheet.write("H11", "241-360", format1_header)
        worksheet.write("I11", "360+", format1_header)
        worksheet.write("J11", "Total", format1_header)

        product_ids = self.env["product.product"].search([("id", "in", tuple(dataframe["id"].tolist()))])
        product_qty_available = product_ids.with_context(
            {"location": list(location_ids)}, to_date=reference_date
        ).compute_quantities_stock_ageing()

        for dataframe_row in dataframe.values:
            qty = round(product_qty_available[dataframe_row[0]], 3)
            if qty > 0:
                qty_0_30 = round(dataframe_row[3], 3)
                qty_31_60 = round(dataframe_row[4], 3)
                qty_61_90 = round(dataframe_row[5], 3)
                qty_91_120 = round(dataframe_row[6], 3)
                qty_121_240 = round(dataframe_row[7], 3)
                qty_241_360 = round(dataframe_row[8], 3)
                qty_360_plus = round(dataframe_row[9], 3)

                (
                    qty_0_30,
                    qty_31_60,
                    qty_61_90,
                    qty_91_120,
                    qty_121_240,
                    qty_241_360,
                    qty_360_plus,
                ) = get_stock_age_qty(
                    qty,
                    qty_0_30,
                    qty_31_60,
                    qty_61_90,
                    qty_91_120,
                    qty_121_240,
                    qty_241_360,
                    qty_360_plus,
                )
            else:
                qty_0_30 = 0
                qty_31_60 = 0
                qty_61_90 = 0
                qty_91_120 = 0
                qty_121_240 = 0
                qty_241_360 = 0
                qty_360_plus = 0

            total_quantity = sum(
                [
                    qty_0_30,
                    qty_31_60,
                    qty_61_90,
                    qty_91_120,
                    qty_121_240,
                    qty_241_360,
                    qty_360_plus,
                ]
            )

            worksheet.write("A%s" % row, dataframe_row[1].get(lang_code), format5_align_left)
            worksheet.write("B%s" % row, dataframe_row[2].get(lang_code), format7_center)
            worksheet.write("C%s" % row, qty_0_30, format8_content_right)
            worksheet.write("D%s" % row, qty_31_60, format8_content_right)
            worksheet.write("E%s" % row, qty_61_90, format8_content_right)
            worksheet.write("F%s" % row, qty_91_120, format8_content_right)
            worksheet.write("G%s" % row, qty_121_240, format8_content_right)
            worksheet.write("H%s" % row, qty_241_360, format8_content_right)
            worksheet.write("I%s" % row, qty_360_plus, format8_content_right)
            worksheet.write("J%s" % row, total_quantity, format8_content_right)

            row += 1

        workbook.close()
        excel_file = base64.b64encode(output.getvalue())
        output.close()
        return excel_file
