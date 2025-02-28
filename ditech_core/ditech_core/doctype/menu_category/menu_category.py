# Copyright (c) 2024, tech@ditech.software and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class MenuCategory(Document):
	def autoname(self):
		self.name = self.category_name