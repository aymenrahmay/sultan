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

import pandas as pd


def sorted_zip_longest(first_list_dict, second_list_dict, key):
    first_list_dict = iter(sorted(first_list_dict, key=lambda x: x[key]))
    second_list_dict = iter(sorted(second_list_dict, key=lambda x: x[key]))
    first_iter = next(first_list_dict, None)
    second_iter = next(second_list_dict, None)

    fillvalue = {}

    while (first_iter is not None) or (second_iter is not None):
        if first_iter is None:
            yield fillvalue, second_iter
            second_iter = next(second_list_dict, None)
        elif second_iter is None:
            yield first_iter, fillvalue
            first_iter = next(first_list_dict, None)
        elif first_iter.get(key) == second_iter.get(key):
            yield first_iter, second_iter
            first_iter = next(first_list_dict, None)
            second_iter = next(second_list_dict, None)
        elif first_iter.get(key) < second_iter.get(key):
            yield first_iter, fillvalue
            first_iter = next(first_list_dict, None)
        else:
            yield fillvalue, second_iter
            second_iter = next(second_list_dict, None)


def get_dataframe(zeroplus_data):
    dataframe = pd.DataFrame(zeroplus_data).fillna(0)
    if "zerotothirty" not in dataframe:
        dataframe["zerotothirty"] = 0
    if "thirtyonetosixty" not in dataframe:
        dataframe["thirtyonetosixty"] = 0
    if "sixtyonetoninty" not in dataframe:
        dataframe["sixtyonetoninty"] = 0
    if "nintyonetoonetwenty" not in dataframe:
        dataframe["nintyonetoonetwenty"] = 0
    if "onetwentyonetotwofourty" not in dataframe:
        dataframe["onetwentyonetotwofourty"] = 0
    if "twofourtytothreesixty" not in dataframe:
        dataframe["twofourtytothreesixty"] = 0
    if "threesixtyplus" not in dataframe:
        dataframe["threesixtyplus"] = 0
    if dataframe.empty:
        return False
    dataframe = dataframe.loc[
        :,
        [
            "id",
            "name",
            "uom",
            "zerotothirty",
            "thirtyonetosixty",
            "sixtyonetoninty",
            "nintyonetoonetwenty",
            "onetwentyonetotwofourty",
            "twofourtytothreesixty",
            "threesixtyplus",
        ],
    ]
    return dataframe


def get_stock_age_qty(
    qty,
    qty_0_30,
    qty_31_60,
    qty_61_90,
    qty_91_120,
    qty_121_240,
    qty_241_360,
    qty_360_plus,
):
    if qty <= qty_0_30:
        qty_0_30 = qty
        qty_31_60 = 0
        qty_61_90 = 0
        qty_91_120 = 0
        qty_121_240 = 0
        qty_241_360 = 0
        qty_360_plus = 0
    elif qty <= qty_0_30 + qty_31_60:
        qty_31_60 = qty - qty_0_30
        qty_61_90 = 0
        qty_91_120 = 0
        qty_121_240 = 0
        qty_241_360 = 0
        qty_360_plus = 0
    elif qty <= qty_0_30 + qty_31_60 + qty_61_90:
        qty_61_90 = qty - qty_0_30 - qty_31_60
        qty_91_120 = 0
        qty_121_240 = 0
        qty_241_360 = 0
        qty_360_plus = 0
    elif qty <= qty_0_30 + qty_31_60 + qty_61_90 + qty_91_120:
        qty_91_120 = qty - qty_0_30 - qty_31_60 - qty_61_90
        qty_121_240 = 0
        qty_241_360 = 0
        qty_360_plus = 0
    elif qty <= qty_0_30 + qty_31_60 + qty_61_90 + qty_91_120 + qty_121_240:
        qty_121_240 = qty - qty_0_30 - qty_31_60 - qty_61_90 - qty_91_120
        qty_241_360 = 0
        qty_360_plus = 0
    elif qty <= qty_0_30 + qty_31_60 + qty_61_90 + qty_91_120 + qty_121_240 + qty_241_360:
        qty_241_360 = qty - qty_0_30 - qty_31_60 - qty_61_90 - qty_91_120 - qty_121_240
        qty_360_plus = 0
    else:
        qty_360_plus = qty - qty_0_30 - qty_31_60 - qty_61_90 - qty_91_120 - qty_121_240 - qty_241_360
    return (
        qty_0_30,
        qty_31_60,
        qty_61_90,
        qty_91_120,
        qty_121_240,
        qty_241_360,
        qty_360_plus,
    )
