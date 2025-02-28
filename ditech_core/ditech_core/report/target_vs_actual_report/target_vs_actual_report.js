// Copyright (c) 2025, pong and contributors
// For license information, please see license.txt

frappe.query_reports["Target Vs Actual Report"] = {
	"filters": [
	  {
			  "fieldname": "parent",
			  "label": __("Sales Persons"),
			  "fieldtype": "MultiSelectList",
			  "options": "Sales Person",
			  "get_data": function(txt) {
				  return frappe.db.get_link_options("Sales Person", txt);
			  }
		  },
		  {
			  "fieldname": "item_group",
			  "label": __("Item Group"),
			  "fieldtype": "MultiSelectList",
			  "options": [
				  // { "label": "All", "value": "All", description:"" },
				  { "label": "Lead", "value": "Lead", description:"" },
				  { "label": "Opportunity", "value": "Opportunity", description:"" },
				  { "label": "Quotation", "value": "Quotation", description:"" },
				  { "label": "Sales Order", "value": "Sales Order", description:"" },
				  { "label": "Sales Invoice", "value": "Sales Invoice", description:"" }
			  ],
			  // "default": "All",
		  },
		  {
			  "fieldname": "period",
			  "label": __("Item Period"),
			  "fieldtype": "Select", 
			  "options": [
				  "Year",
				  "Semester",
				  "Quarter",
		  "Monthly",
				  ""
			  ],
			  "default": "Year"  
		  },
		  {
			  "fieldname": "fiscal_year",
			  "label": __("Fiscal Year"),
			  // "label": __("Fiscal Year") + " (" + new Date().getFullYear() + ")",
			  "fieldtype": "MultiSelectList",
			  "options": "Fiscal Year",
			  "get_data": function(txt) {
				  return frappe.db.get_link_options("Fiscal Year", txt);
			  }
		  },
		  {
			  "fieldname": "filter_select",
			  "label": __("Sales Percentage"),
			  "fieldtype": "Select", 
			  "options": [
				  "Qty",
				  "Amount",
			  ],
			  "default": "Qty"
		  }
	]
  };
  