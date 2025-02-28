# Copyright (c) 2024, tech@ditech.software and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from ditech_core import constants as CONST
from frappe.model.naming import make_autoname
from frappe.utils import (
	getdate, today
)

class BatchPaymentRequest(Document):

	###########################################################################
	# autoname: create naming for document
	###########################################################################
	def autoname(self):
		# validate payment request type
		self.validate_request_type()

		if self.payment_request_type in [CONST.PAYMENT_REQUEST_TYPE_INWARD]:
			self.name = make_autoname(f""".YYYY.MM.-INW-.######.""")
		elif self.payment_request_type in [CONST.PAYMENT_REQUEST_TYPE_OUTWARD]:
			self.name = make_autoname(f""".YYYY.MM.-OTW-.######.""")
		else:
			frappe.throw(f"The valid payment request type is Inward or Outward.")
	# END Function autoname

	###########################################################################
	# validate: validate document
	###########################################################################
	def validate(self):
		self.validate_request_type()
		self.validate_naming()
		self.validate_request_date()
		self.validate_duplicated_items()
		
	# END Function validate

	###########################################################################
	# validate_duplicated_items: validate document
	###########################################################################
	def validate_duplicated_items(self):
		items = self.get('references')
		error_items = []
		for i in items:
			item = i.as_dict()
			exist = frappe.db.exists(
				CONST.DOCTYPE_BATCH_PAYMENT_REQUEST_REFERENCES,
				{
					"parent": ["!=",self.name],
					"parenttype": self.doctype,
					"parentfield": "references",
					"reference_doctype": item.reference_doctype,
					"reference_name": item.reference_name
				}
			)
			if exist:
				data = frappe.db.sql(f"""
					SELECT SUM(allocated_amount) as total_allocated_amount FROM `tabBatch Payment Request References`
					WHERE parent != '{self.name}' AND parenttype = '{self.doctype}'
					AND parentfield = 'references' 
					AND reference_doctype = '{item.reference_doctype}'
					AND reference_name = '{item.reference_name}'
				""", as_dict=1)

				if data and data[0] and (data[0].total_allocated_amount + item.allocated_amount) > item.total_amount:
					req_list = frappe.db.sql(f"""
						SELECT parent FROM `tabBatch Payment Request References`
						WHERE parent != '{self.name}' AND parenttype = '{self.doctype}'
						AND parentfield = 'references'
						AND reference_doctype = '{item.reference_doctype}'
						AND reference_name = '{item.reference_name}'
					""", as_dict=1)
					for r in req_list:
						error_items.append(r.parent)
					
					frappe.throw(f"The references {item.reference_name} are located in {','.join(error_items)} with total amount: {data[0].total_allocated_amount}")
			

	# END Function 

	###########################################################################
	# validate_request_date: validate document naming
	###########################################################################
	def validate_request_date(self):
		if getdate(self.require_date) < getdate(today()):
			frappe.throw(f"The require backdate does not allow at the moment.")
	# END Function validate_request_date


	###########################################################################
	# validate_naming: validate document naming
	###########################################################################
	def validate_naming(self):
		if (
			(
				self.payment_request_type in [CONST.PAYMENT_REQUEST_TYPE_INWARD] 
				and "INW" not in self.name
			) 
			or 
			(
				self.payment_request_type in [CONST.PAYMENT_REQUEST_TYPE_OUTWARD] 
				and "OTW" not in self.name
			)
		):
			frappe.throw("Document series name and payment request type not match.")
		
	# END Function validate_naming

	###########################################################################
	# on_submit: submit the document
	###########################################################################
	def on_submit(self):

		self.validate_request_type()

		# if self.payment_request_type in [CONST.PAYMENT_REQUEST_TYPE_OUTWARD]:
		# 	self.db_set("status", "Initiated")
		# else:
		# 	self.db_set("status", "Requested")
	# END Function on_submit

	###########################################################################
	# validate_request_type: validate payment_request_type
	###########################################################################
	def validate_request_type(self):
		if (
			self.payment_request_type not in [
				CONST.PAYMENT_REQUEST_TYPE_OUTWARD,
				CONST.PAYMENT_REQUEST_TYPE_INWARD
			]
		):
			frappe.throw(f"The valid payment request type is Inward or Outward.")
			
	# END Function validate_request_type


	###########################################################################
	# get_payment_references: get payment references
	###########################################################################
	@frappe.whitelist(methods="POST")
	def get_payment_references(self):
		unpaid_data = []
		result = []
		dt = None
		if self.party_type in [CONST.DOCTYPE_CUSTOMER]:
			dt = CONST.DOCTYPE_SALES_INVOICE
		else:
			dt = CONST.DOCTYPE_PURCHASE_INVOICE
		
		unpaid_data = self.get_unpaid_data(dt)
		for ud in unpaid_data:
			d = frappe.get_doc( dt, ud )
			result.append(d)

		return result
	# END Function get_payment_references

	###########################################################################
	# get_unpaid_data: get payment references
	###########################################################################
	def get_unpaid_data(self, dt):
		status = [
			CONST.STATUS_UNPAID,
			CONST.STATUS_PARTLY_PAID,
			CONST.STATUS_OVERDUE
		]
		fields = [
			""
		]
		filters = frappe._dict(docstatus = 1)
		if dt in [CONST.DOCTYPE_SALES_INVOICE]:
			status.extend([
				CONST.STATUS_UNPAID_AND_DISCOUNT,
				CONST.STATUS_PARTLY_PAID_AND_DISCOUNT,
				CONST.STATUS_OVERDUE_AND_DISCOUNT,
			])
			filters.update(frappe._dict( customer = self.party ))
		else:
			filters.update(frappe._dict( supplier = self.party ))

		filters.update(frappe._dict( status = ["in",status] ))

		# frappe.throw(f"{filters}")
		data = frappe.get_list(
			dt,
			filters
		)

		return data
	# END Function get_unpaid_data