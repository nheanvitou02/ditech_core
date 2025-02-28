# Copyright (c) 2024, tech@ditech.software and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from erpnext.stock.get_item_details import get_pos_profile
from frappe.utils import get_url
from frappe.website.website_generator import WebsiteGenerator
from ditech_core.ditech_core.qr_code import get_qrcode

class POSTable(WebsiteGenerator):
	def validate(self):
		if not self.pos_profile:
			pos_profile = get_pos_profile(self.company) or {}
			if not pos_profile:
				frappe.throw(
					_("No POS Profile found. Please create a New POS Profile first")
				)
			self.pos_profile = pos_profile.get("name")
			self.name = f"""{self.pos_profile} - {self.label}"""

	def before_save(self):
		url = self.url
		if self.menu_qr_code:
			url += "&pro=" + self.pos_profile
			url += "&tb=" + self.name
			self.url = url
			url_short = "".join([self.name])
			qr_code = get_url(url_short)
			self.qr_code = get_qrcode(qr_code, self.logo)
			self.published = True
			self.route = url_short
		else:
			self.qr_code = ""
			self.route = ""
			self.published = 0
