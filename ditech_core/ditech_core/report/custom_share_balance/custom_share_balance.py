# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _


def execute(filters=None):
	if not filters:
		filters = {}

	# if not filters.get("date"):
	# 	frappe.throw(_("Please select date"))

	columns = get_columns(filters)

	data = []

	shareholders = filters.get('shareholder')

	if not shareholders:
		shareholders = frappe.get_all("Shareholder",pluck='name')

	# frappe.throw(f"{shareholders}")
	share_type, no_of_shares, rate, amount = 1, 2, 3, 4

	for s in shareholders:
		total_amount = 0
		total_share  = 0
		rate		 = 0
		share_balance = []

		all_shares = get_all_shares(s)
		for share_entry in all_shares:
			share_balance.append(frappe._dict(
				indent = 1 if filters.get('group_by_shareholder') else 0,
				shareholder = (
					"" if filters.get('group_by_shareholder') 
					else f"""{s}:{frappe.db.get_value("Shareholder",s,["title"])}"""
				),
				share_type = share_entry.share_type,
				no_of_shares = share_entry.no_of_shares,
				average_rate = share_entry.rate,
				amount = share_entry.amount)
			)
			
			total_amount += share_entry.amount
			total_share  += share_entry.no_of_shares
			rate		 += share_entry.rate

			# data.append(row)
		if filters.get('group_by_shareholder'):
			data.append(frappe._dict(
				indent = 0,
				shareholder = f"""{s}:{frappe.db.get_value("Shareholder",s,["title"])}""",
				share_type = '',
				no_of_shares = total_share,
				average_rate = rate/len(all_shares) if all_shares else 0,
				amount = total_amount)
			)

		data.extend(share_balance)

	# frappe.throw(f"data:{data}")
	return columns, data


def get_columns(filters):
	columns = [
		{
			"label": "Shareholder",
			"fieldname": "shareholder",
			"fieldtype": "Link",
			"options": "Shareholder",
			"width": 250
		},
		{
			"label": "Share Type",
			"fieldname": "share_type",
			"fieldtype": "Data",
			"width": 150
		},
		{
			"label": "No of Shares",
			"fieldname": "no_of_shares",
			"fieldtype": "Number",
			"width": 90
		},
		{
			"label": "Average Rate",
			"fieldname": "average_rate",
			"fieldtype": "Currency",
			"width": 90
		},
		{
			"label": "Amount",
			"fieldname": "amount",
			"fieldtype": "Currency",
			"width": 150
		}
	]
	return columns


def get_all_shares(shareholder):
	share_balance = frappe.get_doc("Shareholder", shareholder).share_balance
	# frappe.throw(f"share balance:{share_balance[0].__dict__}")
	return share_balance
