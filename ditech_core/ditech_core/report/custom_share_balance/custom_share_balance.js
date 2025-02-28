// -*- coding: utf-8 -*-
// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Custom Share Balance"] = {
	filters: [
		// {
		// 	fieldname: "date",
		// 	label: __("Date"),
		// 	fieldtype: "Date",
		// 	default: frappe.datetime.get_today(),
		// 	reqd: 1,
		// },
		{
			fieldname: "shareholder",
			label: __("Shareholder"),
			fieldtype: "MultiSelectList",
			get_data: function(txt){
				return frappe.db.get_link_options("Shareholder", txt);
			}
		},
		{
			fieldname: "group_by_shareholder",
			label: __("Group Shareholder"),
			fieldtype: "Check",
			default: 0
		},
	],
	onload: function(report) {
		const views_menu = report.page.add_custom_button_group(__('Report'));
		report.page.add_custom_menu_item(views_menu, __("Share Ledger"), function() {
			var filters = report.get_values();
			// frappe.set_route('query-report', 'CST Customer', {company: filters.company});
			frappe.set_route('query-report', 'Custom Share Ledger');
		});
	}
};
