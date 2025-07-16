######################################################################################
#
#    Hynsys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Hynsys Technologies(<https://www.hynsys.com>).
#    Author: Hynsys Technologies(<https://www.hynsys.com>)
#
#    This program is under the terms of the Odoo Proprietary License v1.0 (OPL-1)
#    It is forbidden to publish, distribute, sublicense, or sell copies of the Software
#    or modified copies of the Software.
#
#    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
#    IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
#    DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
#    ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
#    DEALINGS IN THE SOFTWARE.
#
######################################################################################
{
    "name": "Product Stock Ageing Report",
    "summary": """
        Generate Product Stock Ageing Report in Excel
    """,
    "description": """
        Generate Product Stock Ageing Report in Excel with the following filters:
        1. Product Category
        2. Location

        This module is useful for the inventory managers who are working on the
        stock ageing of the products.
    """,
    "version": "18.0.1.0.0",
    "category": "Inventory",
    "author": "Hynsys Technologies",
    "license": "OPL-1",
    "depends": ["stock"],
    "price": "5",
    "currency": "USD",
    "support": "hynsystechnologies@gmail.com",
    "images": ["static/description/images/product_stock_ageing_report.png"],
    "website": "https://www.hynsys.com",
    "data": [
        "security/ir.model.access.csv",
        "wizard/product_stock_ageing_report_wizard_views.xml",
    ],
    "external_dependencies": {"python": ["xlsxwriter", "pandas"]},
}
