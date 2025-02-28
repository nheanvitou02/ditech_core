# Copyright (c) 2024, tech@ditech.software and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import get_url
from frappe.website.website_generator import WebsiteGenerator
from ditech_core.ditech_core.qr_code import get_qrcode
from erpnext import get_default_company


class MenuQRCode(WebsiteGenerator):
    def autoname(self):
        self.name = (
            self.qr_name
            + " - "
            + frappe.db.get_value("Company", get_default_company(), "abbr")
        )

    def before_save(self):
        url = self.long_url
        self.key = self.name.lower().replace(" ", "")
        url = frappe.utils.get_url() + "/menu?key=" + self.key
        self.long_url = url
        url_short = "".join([self.name])
        qr_code = get_url(url_short)
        self.qr_code = get_qrcode(qr_code, self.logo)
        self.published = True
        self.route = url_short
        self.short_url = self.long_url.split("menu")[0] + self.name
