
# Copyright (c) 2025, pong and contributors
# For license information, please see license.txt

import frappe
import calendar
from datetime import datetime

def execute(filters=None):
    # Define columns for the report
    columns = [
        {"label": "Sales Person", "fieldname": "parent", "fieldtype": "Link", "options": "Sales Person", "width": 150},
        {"label": "Target Group", "fieldname": "item_group", "fieldtype": "Data", "width": 150},
        {"label": "Fiscal Year", "fieldname": "fiscal_year", "fieldtype": "Data", "width": 150},
        {"label": "Target Quantity", "fieldname": "target_qty", "fieldtype": "Float", "width": 150},
        {"label": "Target Amount", "fieldname": "target__amount", "fieldtype": "Currency", "width": 150},
        {"label": "Actual Target", "fieldname": "actual_target", "fieldtype": "Int", "width": 150},
        {"label": "Sale Percentage(Qty)", "fieldname": "sale_percent", "fieldtype": "Percent", "width": 150},
        {"label": "Grand Total", "fieldname": "grand_total", "fieldtype": "Int", "width": 150},
        {"label": "Sale Percentage(Amount)", "fieldname": "sale_percent_amount", "fieldtype": "Percent", "width": 150},
        {"label": "Target Distribution", "fieldname": "target_distribution", "fieldtype": "Data", "width": 150},
        {"label": "Months", "fieldname": "months", "fieldtype": "Data", "width": 150},
    ]
    
    data = []
    item_groups = []
    target_qty = []
    actual_targets = []
    
    # Parse filters
    target_doc_filters = {}
    if filters.get('parent'):
        target_doc_filters["parent"] =["in", filters['parent']] 
        sale_name = filters['parent']
    else:
        sale_name = "All Sales Person"

    if filters.get('item_group') and filters['item_group'] != "All":
        target_doc_filters["item_group"] = ["in", filters['item_group']]

    period = filters.get('period', 'Year')  # Default period to Year if not specified

    filter_select = filters.get("filter_select")    # select filter to see chart based on qty and amount
    
    # select filter year and default to current year
    fiscal_years = filters.get("fiscal_year") or [str(datetime.now().year)]
    if fiscal_years:
        target_doc_filters["fiscal_year"] = ["in", fiscal_years]    
    
    # Fetch Target Docs
    target_docs = frappe.get_all("Target Doc", filters=target_doc_filters, fields=["*"])
    for doc in target_docs:
        fiscal_year = frappe.get_doc("Fiscal Year", doc.fiscal_year)
        start_date = fiscal_year.year_start_date.strftime('%Y-%m-%d')
        end_date = fiscal_year.year_end_date.strftime('%Y-%m-%d')
        doc["start_date"] = start_date
        doc["end_date"] = end_date

        actual_target = 0

        # Get actual target count related to sales person
        creation_item_group = frappe.get_all(
            doc.item_group,
            fields=["name", "sales_person", "DATE(creation) as creation"],
            filters={
                "sales_person": doc.parent,
                "docstatus": 1 if doc.item_group in ("Quotation", "Sales Invoice", "Sales Order") else 0
            }
        )

        # Check if creation dates are within the fiscal year period
        for creations in creation_item_group:
            creation_date = creations.creation.strftime('%Y-%m-%d')
            if start_date <= creation_date <= end_date:
                actual_target = len(creation_item_group)

        # Fetch monthly distribution
        monthly_distribution = frappe.get_all(
            "Monthly Distribution Percentage",
            filters=[{"parent": doc.target_distribution}],
            fields=["parent", "month", "percentage_allocation"]
        )
        if period == "Year":
            target_amount = [doc.target__amount] 
            filters = {"sales_person": doc.parent}
            grand_total = 0
            sales_percentage_amount=0
            if doc.item_group in ["Quotation", "Sales Invoice", "Sales Order"]:
                filters["docstatus"] = 1

                # Fetch creation data
                creation_item_group = frappe.get_all(
                    doc.item_group,
                    fields=["name", "sales_person", "DATE(creation) as creation", "grand_total"],
                    filters=filters
                )

                # Filter by fiscal year date range
                creation_item_group = [
                    item for item in creation_item_group
                    if start_date <= item["creation"].strftime('%Y-%m-%d') <= end_date
                ]

                # Calculate grand_total
                grand_total = sum([item["grand_total"] for item in creation_item_group if item["grand_total"]])

                # Calculate sales percentage based on amount
                sales_percentage_amount = round((grand_total / target_amount[0] * 100), 3) if target_amount and target_amount[0] != 0 else 0

            # Calculate yearly target and sale percentage
            sale_percent = round((actual_target / doc.target_qty * 100), 3) if doc.target_qty else 0
            data.append({
                "parent": doc.parent,
                "item_group": doc.item_group,
                "fiscal_year": doc.fiscal_year,
                "target_qty": doc.target_qty,
                "target__amount": doc.target__amount,
                "actual_target": actual_target,
                "sale_percent": sale_percent ,
                "grand_total": grand_total ,
                "sale_percent_amount": sales_percentage_amount,
                "target_distribution": doc.target_distribution,
                "months": "Yearly Target" 
            })
            item_groups.append(f"{doc.fiscal_year}({doc.parent})")
            target_qty.append(doc.target_qty)
            actual_targets.append(actual_target)

        if period == "Semester":
            month_order = {month: index for index, month in enumerate(calendar.month_name) if month}
            monthly_distribution.sort(key=lambda x: month_order[x["month"]])

            creation_month = [int(creation.creation.strftime('%m')) for creation in creation_item_group]

            semester_months = [monthly_distribution[i:i+6] for i in range(0, 12, 6)]
            sale_percent = []
            semester_month_label = []
            target_amount = [doc.target__amount / 2] * 2
            actual_targets_semester = [0] * 2
            grand_totals_semester = [0] * 2

            filters = {"sales_person": doc.parent}
            if doc.item_group in ["Quotation", "Sales Invoice", "Sales Order"]:
                filters["docstatus"] = 1
                creation_item_group = frappe.get_all(
                    doc.item_group,
                    fields=["name", "sales_person", "DATE(creation) as creation", "grand_total"],
                    filters=filters
                )
                creation_item_group = [
                    item for item in creation_item_group
                    if start_date <= item["creation"].strftime('%Y-%m-%d') <= end_date
                ]

            for idx, months in enumerate(semester_months):
                percentage_allocation = sum(month.percentage_allocation for month in months)
                semester_month_label.append(f"{months[0].month} - {months[-1].month}")
                target_qty_semester = (doc.target_qty / 2)
                sale_percent.append(((target_qty_semester) * percentage_allocation) / 100)

                for creation in creation_item_group:
                    creation_month = creation.creation.month
                    creation_date = creation.creation.strftime('%Y-%m-%d')
                    if (idx * 6) < creation_month <= ((idx + 1) * 6) and start_date <= creation_date <= end_date:
                        actual_targets_semester[idx] += 1
                        if hasattr(creation, 'grand_total') and creation.grand_total:
                            grand_totals_semester[idx] += creation.grand_total

            for i in range(2):
                if sale_percent[i] > 0:
                    sale_percent[i] = round((actual_targets_semester[i] / target_qty_semester) * 100, 3)

            sale_percentage_amount = [
                round((grand_totals_semester[i] / target_amount[i] * 100), 3) if i < len(target_amount) and target_amount[i] else 0
                for i in range(2)
            ]

            for idx, months in enumerate(semester_months):
                data.append({
                    "parent": doc.parent,
                    "item_group": doc.item_group,
                    "fiscal_year": doc.fiscal_year,
                    "target_qty": target_qty_semester,
                    "target__amount": target_amount[idx],
                    "actual_target": actual_targets_semester[idx],
                    "sale_percent": sale_percent[idx],
                    "grand_total": grand_totals_semester[idx],
                    "sale_percent_amount": sale_percentage_amount[idx],
                    "target_distribution": doc.target_distribution,
                    "months": semester_month_label[idx],
                    "indent": 1,
                })

                item_groups.append(f"{semester_month_label[idx]}({doc.parent})")
                target_qty.append(target_qty_semester)
                actual_targets.append(actual_targets_semester[idx])

        elif period == "Quarter":
            month_order = {month: index for index, month in enumerate(calendar.month_name) if month}
            monthly_distribution.sort(key=lambda x: month_order[x["month"]])


            quarterly_months = [monthly_distribution[i:i+3] for i in range(0, 12, 3)]
            target_amount = [doc.target__amount / 4] * 4
            target_qty_quarter = [doc.target_qty / 4] * 4
            quarterly_month_label = []
            actual_targets_quarterly = [0] * 4
            sale_percent = []
            grand_totals_quarter = [0] * 4

            filters = {"sales_person": doc.parent}
            if doc.item_group in ["Quotation", "Sales Invoice", "Sales Order"]:
                filters["docstatus"] = 1
                creation_item_group = frappe.get_all(
                    doc.item_group,
                    fields=["name", "sales_person", "DATE(creation) as creation", "grand_total"],
                    filters=filters
                )
                creation_item_group = [
                    item for item in creation_item_group
                    if start_date <= item["creation"].strftime('%Y-%m-%d') <= end_date
                ]

            for idx, months in enumerate(quarterly_months):
                percentage_allocation = sum(month["percentage_allocation"] for month in months)
                quarterly_month_label.append(f"{months[0]['month']} - {months[-1]['month']}")

                for creation in creation_item_group:
                    creation_month = creation.creation.month
                    creation_date = creation.creation.strftime('%Y-%m-%d')
                    if (idx * 3) < creation_month <= ((idx + 1) * 3) and start_date <= creation_date <= end_date:
                        actual_targets_quarterly[idx] += 1
                        if hasattr(creation, 'grand_total') and creation.grand_total:
                            grand_totals_quarter[idx] += creation.grand_total

                sale_percent.append(round((actual_targets_quarterly[idx] / target_qty_quarter[idx]) * 100, 3))

            sale_percentage_amount = [
                round((grand_totals_quarter[i] / target_amount[i] * 100), 3) if i < len(target_amount) and target_amount[i] else 0
                for i in range(4)
            ]

            for idx, months in enumerate(quarterly_months):
                data.append({
                    "parent": doc.parent,
                    "item_group": doc.item_group,
                    "fiscal_year": doc.fiscal_year,
                    "target_qty": target_qty_quarter[idx],
                    "target__amount": target_amount[idx],
                    "actual_target": actual_targets_quarterly[idx],
                    "sale_percent": sale_percent[idx],
                    "grand_total": grand_totals_quarter[idx],
                    "sale_percent_amount": sale_percentage_amount[idx],
                    "target_distribution": doc.target_distribution,
                    "months": quarterly_month_label[idx],
                    "indent": 1,
                })

                item_groups.append(f"{quarterly_month_label[idx]}({doc.parent})")
                target_qty.append(target_qty_quarter[idx])
                actual_targets.append(actual_targets_quarterly[idx])

        elif period == "Monthly":
            month_order = {month: index for index, month in enumerate(calendar.month_name) if month}
            monthly_distribution.sort(key=lambda x: month_order[x["month"]])

            chart_bar_label = []
            target_amount = [round(doc.target__amount / 12, 3)] * 12
            target_qty_monthly = [doc.target_qty / 12] * 12
            sale_percent = [0] * 12
            grand_totals_monthly = [0] * 12

            filters = {"sales_person": doc.parent}
            if doc.item_group in ["Quotation", "Sales Invoice", "Sales Order"]:
                filters["docstatus"] = 1
                creation_item_group = frappe.get_all(
                    doc.item_group,
                    fields=["name", "sales_person", "DATE(creation) as creation", "grand_total"],
                    filters=filters
                )
                creation_item_group = [
                    item for item in creation_item_group
                    if start_date <= item["creation"].strftime('%Y-%m-%d') <= end_date
                ]

            for months_distribution in monthly_distribution:
                month_index = month_order[months_distribution["month"]] - 1
                percentage_allocation = months_distribution["percentage_allocation"]
                percentage_month = (doc.target_qty * percentage_allocation) / 100
                chart_bar_label.append(months_distribution["month"])

            actual_targets_monthly = [0] * 12
            for creation in creation_item_group:
                creation_month = creation.creation.month - 1
                if start_date <= creation.creation.strftime('%Y-%m-%d') <= end_date:
                    actual_targets_monthly[creation_month] += 1
                    if hasattr(creation, 'grand_total') and creation.grand_total:
                        grand_totals_monthly[creation_month] += creation.grand_total

            for i in range(12):
                if target_qty_monthly[i] > 0:
                    sale_percent[i] = round((actual_targets_monthly[i] / target_qty_monthly[i]) * 100, 3)

            sales_percentage_amount = [
                round((grand_totals_monthly[i] / target_amount[i] * 100), 3) if i < len(target_amount) and target_amount[i] else 0
                for i in range(12)
            ]

            for i, month in enumerate(calendar.month_name[1:]):
                data.append({
                    "parent": doc.parent,
                    "item_group": doc.item_group,
                    "fiscal_year": doc.fiscal_year,
                    "target_qty": target_qty_monthly[i],
                    "target__amount": target_amount[i],
                    "actual_target": actual_targets_monthly[i],
                    "sale_percent": sale_percent[i],
                    "grand_total": grand_totals_monthly[i],
                    "sale_percent_amount": sales_percentage_amount [i],
                    "target_distribution": doc.target_distribution,
                    "months": month,
                    "indent": 1,
                })

                item_groups.append(f"{month}({doc.parent})")
                target_qty.append(target_qty_monthly[i])
                actual_targets.append(actual_targets_monthly[i])

    # Define chart configuration
    if filter_select == "Qty":
        chart = {
            "type": "bar",  
            "colors": ["#3498db", "#2ecc71"],  
            "data": {
                "labels": item_groups,  
                "datasets": [
                    {
                        "name": "Targets Qty",
                        "values": target_qty,
                    },
                    {
                        "name": "Actual Qty",
                        "values": [data_item["actual_target"] for data_item in data],
                    },
                    {
                        "name": "Sale Percent(Qty)",
                        "values": [data_item["sale_percent"] for data_item in data],
                    }
                ],
            },
            "title": sale_name,  
        }
    else:
        chart = {
            "type": "bar",  
            "colors": ["#3498db", "#2ecc71"],  
            "data": {
                "labels": item_groups,  
                "datasets": [
                    {
                        "name": "Targets Amount",
                        "values": [data_item["target__amount"] for data_item in data],
                    },
                    {
                        "name": "Actual Amount",
                        "values": [data_item["grand_total"] for data_item in data],
                    },
                    {
                        "name": "Sale Percent(Amount)",
                        "values": [data_item["sale_percent_amount"] for data_item in data],
                    }
                ],
            },
            "title": sale_name,  
        }

    # Return columns, data, and chart
    return columns, data, None, chart
