# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.utils import (
	getdate
)
from pypika import Order # type: ignore


def execute(filters=None):
	if not filters:
		filters = {}

	if not filters.get("date"):
		frappe.throw(_("Please select date"))

	columns = get_columns(filters)

	date = filters.get("date")

	data = []
	shareholders = filters.get('shareholder')

	if not shareholders:
		shareholders = frappe.get_all("Shareholder",pluck='name')
	
	transfers = get_all_transfers(date, shareholders)
	for transfer in transfers:
		if transfer.transfer_type == "Transfer":
			if transfer.from_shareholder == filters.get("shareholder"):
				transfer.transfer_type += f" to {transfer.to_shareholder}"
			else:
				transfer.transfer_type += f" from {transfer.from_shareholder}"

		from_shareholder = transfer.from_shareholder
		to_shareholder   = transfer.to_shareholder
		if from_shareholder:
			from_shareholder = f"""{from_shareholder}:{frappe.db.get_value("Shareholder",from_shareholder,["title"])}"""

		if to_shareholder:
			to_shareholder   = f"""{to_shareholder}:{frappe.db.get_value("Shareholder",to_shareholder,["title"])}"""
			
		row = [
			from_shareholder,
			transfer.date,
			transfer.transfer_type,
			transfer.share_type,
			to_shareholder,
			transfer.no_of_shares,
			transfer.rate,
			transfer.amount,
			transfer.company,
			transfer.name,
		]

		data.append(row)

	return columns, data


def get_columns(filters):
	columns = [
		_("Shareholder") + ":Link/Shareholder:220",
		_("Date") + ":Date:150",
		_("Transfer Type") + "::140",
		_("Share Type") + "::150",
		_("To Shareholder") + ":Link/Shareholder:220",
		_("No of Shares") + "::80",
		_("Rate") + ":Currency:80",
		_("Amount") + ":Currency:150",
		_("Company") + "::150",
		_("Share Transfer") + ":Link/Share Transfer:220",
	]
	return columns


def get_all_transfers(date, shareholder):
	condition = " "
	SHARETRANSFER = frappe.qb.DocType("Share Transfer")
	q = (
		frappe.qb.from_(SHARETRANSFER)
		.select('*')
		.where( SHARETRANSFER.date <= getdate(date) )
		.where( 
			SHARETRANSFER.from_shareholder.isin(shareholder) | 
			SHARETRANSFER.to_shareholder.isin(shareholder) 
		)
		.where( SHARETRANSFER.docstatus == 1 )
		.orderby('date', order=Order.desc)
	)

	data = q.run(as_dict=1)

	return data

	# frappe.throw(f"data: {data}")

	# # if company:
	# # 	condition = 'AND company = %(company)s '
	# return frappe.db.sql(
	# 	f"""SELECT * FROM `tabShare Transfer`
	# 	WHERE ((DATE(date) <= %(date)s AND from_shareholder IN %(shareholder)s {condition})
	# 	OR (DATE(date) <= %(date)s AND to_shareholder IN %(shareholder)s {condition}))
	# 	AND docstatus = 1
	# 	ORDER BY date""",
	# 	{"date": date, "shareholder": shareholder},
	# 	as_dict=1,
	# )
