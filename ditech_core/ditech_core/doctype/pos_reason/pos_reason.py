# Copyright (c) 2024, tech@ditech.software and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from erpnext.stock.get_item_details import get_pos_profile


class POSReason(Document):
	def validate(self):
		if not self.pos_profile:
			pos_profile = get_pos_profile(self.company) or {}
			if not pos_profile:
				frappe.throw(
					_("No POS Profile found. Please create a New POS Profile first")
				)
			self.pos_profile = pos_profile.get("name")
			self.name = f"""{self.pos_profile} - {self.reason}"""
