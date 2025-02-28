import frappe
import calendar
import json
import math
import calendar
from datetime import datetime
from typing import Optional,List, Dict, Any
from datetime import datetime
from frappe.utils import unique, getdate, nowtime, nowdate


# Define DocType names
doctype_fiscal_year = 'Fiscal Year'
doctype_sale_person = 'Sales Person'
doctype_target_doc = 'Target Doc'
doctype_monthly_distribution = 'Monthly Distribution'
doctype_monthly_distribution_percentage = 'Monthly Distribution Percentage'

@frappe.whitelist()
def get_total_target_group_fiscal_year():
    target_group = frappe.get_all(doctype_sale_person, 
                                  fields=["name", "creation"],
                                  filters={"parent": doctype_target_doc})
    return {"target_group": target_group}

@frappe.whitelist(allow_guest=True)
def get_total_target_doc():
    sales_persons = frappe.get_all(doctype_sale_person, fields=["name"])
    item_groups = []
    counts = {}
    order = ["Lead", "Opportunity", "Quotation", "Sales Order", "Sales Invoice"]
    
    for sales_person in sales_persons:
        filters = {"parent": sales_person.name}
        target_docs = frappe.get_all(doctype_target_doc, fields=["item_group"], filters=filters)
        item_groups.extend([target_doc.item_group for target_doc in target_docs])
    
    for item_group in unique(item_groups):
        filters = {}
        if item_group in ["Quotation", "Sales Invoice", "Sales Order"]:
            filters["docstatus"] = 1
        counts[item_group] = frappe.db.count(item_group, filters=filters)
    
    # Order counts by the specified order
    ordered_counts = {k: counts[k] for k in order if k in counts}
    
    # Add dynamic "page_uql" key, replace space with "-" and add "?docstatus=1" if applicable
    page_uql = {
        item_group.lower().replace(" ", "-"): f"app/{item_group.lower().replace(' ', '-')}" + ("?docstatus=1" if item_group in ["Quotation", "Sales Order", "Sales Invoice"] else "")
        for item_group in unique(item_groups)
    }
    
    return {"message": ordered_counts, "item_group": unique(item_groups), "page_uql": page_uql}

@frappe.whitelist(allow_guest=True)
def get_sales_person():
    return {"sales_person": frappe.get_all(doctype_sale_person, fields=["name"])}

@frappe.whitelist(allow_guest=True)
def get_target_sales_person(filter_is_qty: int, filter_group_name: str = "", filter_view: Optional[str] = None, filter_fiscal_year: int = datetime.now().year) -> None:
    try:
        if filter_group_name !="":
            return get_sales_person_group(filter_is_qty,filter_group_name, filter_view, filter_fiscal_year)
        elif filter_group_name == "":   
            combine_data = []
            sales_persons = frappe.get_all(doctype_sale_person, fields=["name"], order_by="creation desc")
            order = ["Lead", "Opportunity", "Quotation", "Sales Order", "Sales Invoice"]

            for sales_person in sales_persons:
                filters = {"parent": sales_person.name}
                if filter_fiscal_year:
                    filters["fiscal_year"] = filter_fiscal_year

                target_docs = frappe.get_all(
                    doctype_target_doc, 
                    fields=["name", "item_group", "fiscal_year", "target_qty", "target__amount", "target_distribution", "parent"], 
                    filters=filters
                )
                
                # Filter out "Lead" and "Opportunity" if filter_is_qty is 0
                if filter_is_qty == 0:
                    target_docs = [doc for doc in target_docs if doc["item_group"] not in ["Lead", "Opportunity"]]

                for target_doc in target_docs:
                    process_target_doc(target_doc, filter_view)

                # Order target_docs by the specified order
                target_docs.sort(key=lambda x: order.index(x["item_group"]) if x["item_group"] in order else len(order))

                combine_data.append({"sales_person": sales_person.name, "target_docs": target_docs})
            status_success = frappe.local.response["http_status_code"] = 200   
            return {"status": status_success, "success": 1,"combine_data": combine_data}
    except Exception as e:
        frappe.throw(title=("Error"),exc=e,msg= str(e))

def process_target_doc(target_doc, filter_view):
    target_qty = target_doc.target_qty
    fiscal_year = frappe.get_doc(doctype_fiscal_year, target_doc.fiscal_year)
    start_date = fiscal_year.year_start_date.strftime('%Y-%m-%d')
    end_date = fiscal_year.year_end_date.strftime('%Y-%m-%d')
    target_doc["start_date"] = start_date
    target_doc["end_date"] = end_date

    filters = {"sales_person": target_doc.parent}
    grand_total = 0
    if target_doc.item_group in ["Quotation", "Sales Invoice", "Sales Order"]:
        filters["docstatus"] = 1
        creation_item_group = frappe.get_all(
            target_doc.item_group,
            fields=["name", "sales_person", "DATE(creation) as creation", "grand_total"],
            filters=filters
        )
        grand_total = sum([i.grand_total for i in creation_item_group if i.grand_total and start_date <= i.creation.strftime('%Y-%m-%d') <= end_date])
    else:
        creation_item_group = frappe.get_all(
            target_doc.item_group,
            fields=["name", "sales_person", "DATE(creation) as creation"],
            filters=filters
        )

    actual_target = calculate_actual_target(creation_item_group, start_date, end_date)

    monthly_distribution_percentage = frappe.get_all(
        doctype_monthly_distribution_percentage,
        fields=["month", "percentage_allocation", "percentage_allocation_amount", "parent"],
        filters={"parent": target_doc.target_distribution}
    )

    unique_percentage = unique([md["percentage_allocation"] for md in monthly_distribution_percentage])
    target_doc["is_same_percentage"] = 1 if len(unique_percentage) == 1 else 0
    target_doc["monthly_distribution_percentage"] = monthly_distribution_percentage
    target_doc["chart_data"] = {}
    target_doc["chart_data"]["actual_target"] = [actual_target]
    target_doc["chart_data"]["chart_bar_label"] = [target_doc.fiscal_year]
    target_doc["chart_data"]["target_amount"] = [round(target_doc.target__amount, 3)]
    target_doc["chart_data"]["actual_amount"] = [grand_total]
    target_doc["chart_data"]["percentage_amount"] = [round((grand_total / target_doc.target__amount) * 100, 3) if target_doc.target__amount else 0]

    if filter_view == "Year":
        sale_percent = round((actual_target / target_qty * 100), 3) if target_qty > 0 else 0
        target_doc["chart_data"]["percentage_qty"] = [sale_percent]
        target_doc["chart_data"]["target_qty"] = [target_qty]
    elif filter_view == "Semester":
        process_semester_view(target_doc, target_qty, creation_item_group, start_date, end_date, monthly_distribution_percentage)
    elif filter_view == "Quarterly":
        process_quarterly_view(target_doc, target_qty, creation_item_group, start_date, end_date, monthly_distribution_percentage)
    elif filter_view == "Monthly":
        process_monthly_view(target_doc, target_qty, creation_item_group, start_date, end_date, monthly_distribution_percentage)


def calculate_actual_target(creation_item_group, start_date, end_date):
    actual_target = 0
    for creation in creation_item_group:
        creation_date = creation.creation.strftime('%Y-%m-%d')
        if start_date <= creation_date <= end_date:
            actual_target += 1
    return actual_target
def process_semester_view(target_doc, target_qty, creation_item_group, start_date, end_date, monthly_distribution_percentage):
    sale_percent = []
    semester_month_label = []
    actual_targets_semester = [0] * 2
    grand_totals_semester = [0] * 2
    percentage_grand_totals_semester = [0] * 2
    month_order = {month: index for index, month in enumerate(calendar.month_name) if month}
    monthly_distribution_percentage.sort(key=lambda x: month_order[x.month])
    semester_months = [monthly_distribution_percentage[i:i+6] for i in range(0, 12, 6)]

    for idx, months in enumerate(semester_months):
        percentage_allocation = sum(month.percentage_allocation for month in months)
        percentage_allocation_amount = sum(month.percentage_allocation_amount for month in months)
        semester_month_label.append(f"{months[0].month} - {months[-1].month}")
        
        # Calculate target quantity for the semester based on the percentage allocation
        target_qty_semester = (target_qty * percentage_allocation) / 100 if percentage_allocation != 0 else 0
        sale_percent.append(target_qty_semester)

        for creation in creation_item_group:
            creation_month = creation.creation.month
            creation_date = creation.creation.strftime('%Y-%m-%d')
            if (idx * 6) < creation_month <= ((idx + 1) * 6) and start_date <= creation_date <= end_date:
                actual_targets_semester[idx] += 1
                if hasattr(creation, 'grand_total') and creation.grand_total:
                    grand_totals_semester[idx] += creation.grand_total

    for i in range(2):
        # Safeguard against division by zero for sale_percent calculation
        if sale_percent[i] > 0:
            sale_percent[i] = round((actual_targets_semester[i] / sale_percent[i]) * 100, 3) if sale_percent[i] != 0 else 0

        # Safeguard against division by zero for percentage_grand_totals_semester calculation
        if target_doc.target__amount > 0:
            allocation_amount = sum(month.percentage_allocation_amount for month in semester_months[i])
            if allocation_amount != 0:
                percentage_grand_totals_semester[i] = round(
                    (grand_totals_semester[i] / (target_doc.target__amount * allocation_amount / 100)) * 100, 3
                )
            else:
                percentage_grand_totals_semester[i] = 0
        else:
            percentage_grand_totals_semester[i] = 0

    # Safeguard against division by zero for target_qty and target_amount calculations
    target_doc["chart_data"]["percentage_qty"] = sale_percent
    target_doc["chart_data"]["chart_bar_label"] = semester_month_label
    target_doc["chart_data"]["actual_target"] = actual_targets_semester
    target_doc["chart_data"]["target_qty"] = [
        round((target_qty * sum(month.percentage_allocation for month in semester_months[i])) / 100, 3) if sum(month.percentage_allocation for month in semester_months[i]) != 0 else 0
        for i in range(2)
    ]
    target_doc["chart_data"]["target_amount"] = [
        round((target_doc.target__amount) * (sum(month.percentage_allocation_amount for month in semester_months[i]) / 100), 3)
        if sum(month.percentage_allocation_amount for month in semester_months[i]) != 0 else 0
        for i in range(2)
    ]
    target_doc["chart_data"]["actual_amount"] = grand_totals_semester
    target_doc["chart_data"]["percentage_amount"] = percentage_grand_totals_semester



def process_quarterly_view(target_doc, target_qty, creation_item_group, start_date, end_date, monthly_distribution_percentage):
    quarterly_month_data = [0] * 4
    quarterly_month_label = []
    actual_targets_quarterly = [0] * 4
    grand_totals_quarterly = [0] * 4
    percentage_grand_totals_quarterly = [0] * 4
    sale_percent = []
    
    month_order = {month: index for index, month in enumerate(calendar.month_name) if month}
    monthly_distribution_percentage.sort(key=lambda x: month_order[x.month])
    
    # Split the monthly data into quarters (3 months each)
    quarterly_months = [monthly_distribution_percentage[i:i+3] for i in range(0, 12, 3)]

    for idx, months in enumerate(quarterly_months):
        # Sum the percentage allocation for the quarter
        percentage_allocation = sum(month.percentage_allocation for month in months)
        percentage_allocation_amount = sum(month.percentage_allocation_amount for month in months)
        quarterly_month_label.append(f"{months[0].month} - {months[-1].month}")

        # Calculate target quantity for the quarter based on the percentage allocation
        quarterly_month_data[idx] = round((target_qty * percentage_allocation) / 100, 3) if percentage_allocation != 0 else 0

        for creation in creation_item_group:
            creation_month = creation.creation.month
            creation_date = creation.creation.strftime('%Y-%m-%d')
            if (idx * 3) < creation_month <= ((idx + 1) * 3) and start_date <= creation_date <= end_date:
                actual_targets_quarterly[idx] += 1
                if hasattr(creation, 'grand_total') and creation.grand_total:
                    grand_totals_quarterly[idx] += creation.grand_total

        # Safeguard against division by zero for sale_percent calculation
        sale_percent.append(
            round(0 if quarterly_month_data[idx] == 0 else (actual_targets_quarterly[idx] / quarterly_month_data[idx]) * 100, 3)
        )

        if target_doc.target__amount:
            # Safeguard against division by zero for percentage_grand_totals_quarterly calculation
            if target_doc.target__amount * percentage_allocation_amount != 0:
                percentage_grand_totals_quarterly[idx] = round(
                    (grand_totals_quarterly[idx] / (target_doc.target__amount * percentage_allocation_amount / 100)) * 100, 3
                )
            else:
                percentage_grand_totals_quarterly[idx] = 0

    target_doc["chart_data"]["chart_bar_label"] = quarterly_month_label
    target_doc["chart_data"]["target_qty"] = quarterly_month_data
    target_doc["chart_data"]["actual_target"] = actual_targets_quarterly
    target_doc["chart_data"]["percentage_qty"] = sale_percent
    target_doc["chart_data"]["target_amount"] = [
        round(target_doc.target__amount * sum(month.percentage_allocation_amount for month in quarterly_months[i]) / 100, 3) if sum(month.percentage_allocation_amount for month in quarterly_months[i]) != 0 else 0
        for i in range(4)
    ]
    target_doc["chart_data"]["actual_amount"] = grand_totals_quarterly
    target_doc["chart_data"]["percentage_amount"] = percentage_grand_totals_quarterly


def process_monthly_view(target_doc, target_qty, creation_item_group, start_date, end_date, monthly_distribution_percentage):
    chart_bar_label = []
    chart_bar_data = [0] * 12
    sale_percent = [0] * 12
    grand_totals_monthly = [0] * 12
    percentage_grand_totals_monthly = [0] * 12
    month_order = {month: index for index, month in enumerate(calendar.month_name) if month}
    monthly_distribution_percentage.sort(key=lambda x: month_order[x.month])

    for months_distribution in monthly_distribution_percentage:
        month_index = month_order[months_distribution.month] - 1  # Get the index of the month (0-11)
        
        # Correct target_qty calculation based on percentage_allocation
        if hasattr(months_distribution, 'percentage_allocation'):
            chart_bar_data[month_index] = round((target_qty * months_distribution.percentage_allocation) / 100, 3) if months_distribution.percentage_allocation != 0 else 0
        chart_bar_label.append(months_distribution.month)
    
    actual_targets_monthly = [0] * 12
    for creation in creation_item_group:
        creation_month = creation.creation.month - 1
        if start_date <= creation.creation.strftime('%Y-%m-%d') <= end_date:
            actual_targets_monthly[creation_month] += 1
            if hasattr(creation, 'grand_total') and creation.grand_total:
                grand_totals_monthly[creation_month] += creation.grand_total

    for i in range(12):
        if chart_bar_data[i] > 0:  # Avoid division by zero
            sale_percent[i] = round((actual_targets_monthly[i] / chart_bar_data[i]) * 100, 3) if chart_bar_data[i] != 0 else 0
        if target_doc.target__amount and monthly_distribution_percentage[i].percentage_allocation_amount != 0:
            # Safeguard against division by zero
            if target_doc.target__amount * monthly_distribution_percentage[i].percentage_allocation_amount != 0:
                percentage_grand_totals_monthly[i] = round(
                    (grand_totals_monthly[i] / (target_doc.target__amount * monthly_distribution_percentage[i].percentage_allocation_amount / 100)) * 100, 3
                )
            else:
                percentage_grand_totals_monthly[i] = 0

    target_doc["chart_data"]["chart_bar_label"] = chart_bar_label
    target_doc["chart_data"]["target_qty"] = chart_bar_data
    target_doc["chart_data"]["actual_target"] = actual_targets_monthly
    target_doc["chart_data"]["percentage_qty"] = sale_percent
    target_doc["chart_data"]["target_amount"] = [
        round(target_doc.target__amount * months_distribution.percentage_allocation_amount / 100, 3) if months_distribution.percentage_allocation_amount != 0 else 0
        for months_distribution in monthly_distribution_percentage
    ]
    target_doc["chart_data"]["actual_amount"] = grand_totals_monthly
    target_doc["chart_data"]["percentage_amount"] = percentage_grand_totals_monthly

@frappe.whitelist(allow_guest=True)
def get_sales_person_group(filter_is_qty: int,filter_group_name:str, filter_view: str, filter_fiscal_year: int) -> Dict[str, Any]:
    try:
        sales_person_groups: Dict[str, List[Dict[str, Any]]] = {}
        combined_data: List[Dict[str, Any]] = []
        sales_persons = frappe.get_all("Sales Person", fields=["name", "parent_sales_person", "is_group"])

        # Group sales persons by their parent
        for sales_person in sales_persons:
            parent = sales_person.parent_sales_person
            if parent:
                sales_person_groups.setdefault(parent, []).append(
                    {"name": sales_person.name, "parent_sales_person": parent, "is_group": sales_person.is_group}
                )

        # Process each group of sales persons
        for parent, group in sales_person_groups.items():
            children_data = process_group_children(filter_is_qty, group, filter_view, filter_fiscal_year)

            # Summarize targets for the group
            summarized_target_data = summarize_group_targets(children_data, filter_view)
            # Process the final view of the summarized data
            process_final_view(summarized_target_data, filter_view)

            # Append the processed data for the parent group
            combined_data.append({
                "parent_sales_person": parent,
                "children": children_data,
                "summed_target_docs": summarized_target_data
            })
        # Filter the combined data based on filter_group_name
        combined_data = [item for item in combined_data if item.get("parent_sales_person") == filter_group_name or filter_group_name == "All Groups"]
        frappe.local.response["http_status_code"] = 200
        return {"status": 200, "success": 1, "combine_data": combined_data}
    except Exception as e:
        frappe.throw(title=("Error"),exc=e,msg= str(e))


# Process children within a sales person group
def process_group_children(filter_is_qty, group, filter_view, filter_fiscal_year):
    children_data = []
    for sales_person in group:
        target_docs = fetch_target_docs(sales_person["name"], filter_fiscal_year)
        sorted_target_docs = sort_target_docs(filter_is_qty, target_docs)
        children_data.append({"sales_person": sales_person, "target_docs": sorted_target_docs})
    return children_data

# Fetch target documents based on filter conditions
def fetch_target_docs(sales_person_name, filter_fiscal_year):
    return frappe.get_all(
        doctype_target_doc,
        fields=["item_group", "fiscal_year", "target_qty", "target__amount", "target_distribution", "parent"],
        filters={"parent": sales_person_name, "fiscal_year": filter_fiscal_year}
    )

# Sort target documents by predefined order
def sort_target_docs(filter_is_qty, target_docs):
    if filter_is_qty == 0:
        target_docs = [doc for doc in target_docs if doc["item_group"] not in ["Lead", "Opportunity"]]
    order = ["Lead", "Opportunity", "Quotation", "Sales Order", "Sales Invoice"]
    target_docs.sort(key=lambda x: order.index(x["item_group"]) if x["item_group"] in order else len(order))
    return target_docs

# Initialize the item group data structure
def initialize_item_group_data(target_doc, child):
    return {
        "parent_sales_person": child["sales_person"]["parent_sales_person"],
        "child_sales_person": [],
        "target_qty": 0,
        "target__amount": 0,
        "actual_target": 0,
        "actual_amount": 0,
        "percentage_qty": 0,
        "amount_percent": 0,
        "fiscal_year": target_doc["fiscal_year"],
        "chart_data": {
            "chart_label": [],
            "target_qty":[],
            "actual_qty": [],
            "target_amount":[],
            "actual_amount": []
        }
    }

# Summarize target data for all children in a group
def summarize_group_targets(children, filter_view):
    summarized_data: Dict[str, Dict[str, Any]] = {}
    for child in children:
        for target_doc in child["target_docs"]:
            item_group = target_doc["item_group"]
            item_group_data = frappe.get_all(
                item_group,
                fields=["*", "DATE(creation) as creation"],
                filters={"sales_person": child["sales_person"]["name"]}
            )

            # Calculate total quantity and amount for the item group
            item_group_total_qty = len(item_group_data)
            item_group_total_amount = sum(doc.get("target__amount", 0) for doc in item_group_data)

            if item_group not in summarized_data:
                summarized_data[item_group] = initialize_item_group_data(target_doc, child)

            # Update the summarized data with the item group's details
            summarized_data[item_group]["target_qty"] += target_doc["target_qty"]
            summarized_data[item_group]["target__amount"] += target_doc["target__amount"]
            summarized_data[item_group]["actual_target"] += item_group_total_qty
            summarized_data[item_group]["actual_amount"] += item_group_total_amount
            summarized_data[item_group]["child_sales_person"].append(child["sales_person"]["name"])
            
    # Get target team parent quantity and amount
    get_target_team_parent_qty_amount(summarized_data)

    # Calculate sale percentages for quantity and amount
    calculate_sale_percentages(summarized_data, filter_view)

    return summarized_data

# Get target team parent quantity and amount if has
def get_target_team_parent_qty_amount(summarized_data):
    for item_group in summarized_data:
        target_docs = frappe.get_all(
            doctype_target_doc, 
            fields=["target_qty", "target__amount", "parent"], 
            filters={"item_group": item_group, "parent": summarized_data[item_group]["parent_sales_person"]}
        )
        if target_docs:
            for target_doc in target_docs:
                if target_doc["parent"] == summarized_data[item_group]["parent_sales_person"]:
                    summarized_data[item_group]["target_qty_group"] = target_doc["target_qty"]  
                    summarized_data[item_group]["target_amount_group"] = target_doc["target__amount"]  

# Calculate sale percentage for each item group
def calculate_sale_percentages(summarized_data, filter_view):
    for item_group, data in summarized_data.items():
        target_qty = data.get("target_qty_group", data["target_qty"])
        target_amount = data.get("target_amount_group", data["target__amount"])

        data["percentage_qty"] = round((data["actual_target"] / target_qty) * 100, 3) if target_qty > 0 else 0
        data["amount_percent"] = round((data["actual_amount"] / target_amount) * 100, 3) if target_amount > 0 else 0

        # Set chart labels based on filter view
        set_chart_labels(data, filter_view)

# Set chart labels based on filter view
def set_chart_labels(data, filter_view):
    data["chart_data"]["chart_label"] = {
        "Year": [data["fiscal_year"]],
        "Semester": ["Jan-Jun", "Jul-Dec"],
        "Quarterly": ["Jan-Mar", "Apr-Jun", "Jul-Sep", "Oct-Dec"],
        "Monthly": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    }.get(filter_view, [])

def process_final_view(summarized_data, filter_view):
    group_functions = {
        "Year": process_year_view_group,
        "Semester": process_semester_view_group,
        "Quarterly": process_quarterly_view_group,
        "Monthly": process_monthly_view_group
    }
    group_functions.get(filter_view, lambda x: None)(summarized_data)

# Group data by year
def process_year_view_group(summarized_data):
    group_by_period(summarized_data, 1, lambda month: 0, 'Year')

def process_semester_view_group(summarized_data):
    group_by_period(summarized_data, 2, lambda month: 0 if month <= 6 else 1, 'Semester')

def process_quarterly_view_group(summarized_data):
    group_by_period(summarized_data, 4, lambda month: (month - 1) // 3, 'Quarter')

def process_monthly_view_group(summarized_data):
    group_by_period(summarized_data, 12, lambda month: month - 1, 'Month')

# Function to initialize chart data lists
def initialize_chart_data(data, num_periods):
    data["chart_data"].update(
        {
            "target_qty": [0] * num_periods,
            "actual_qty": [0] * num_periods,
            "percentage_qty": [0] * num_periods,
            "target_amount": [0] * num_periods,
            "actual_amount": [0] * num_periods,
            "percentage_amount": [0] * num_periods,
        }
    )
def distribute_targets(data, num_periods, target_qty, target_amount):
    # Distribute the targets based on the number of periods
    if num_periods == 1:  # Yearly: Assign directly
        data["chart_data"]["target_qty"][0] = round(target_qty, 3)
        data["chart_data"]["target_amount"][0] = round(target_amount, 3)
    else:  # Semester, Quarterly, Monthly: Distribute evenly
        for i in range(num_periods):
            data["chart_data"]["target_qty"][i] = round(target_qty / num_periods, 3)
            data["chart_data"]["target_amount"][i] = round(target_amount / num_periods, 3)
        
# Main function: Group by period
def group_by_period(summarized_data, num_periods, get_period_index, period_type):
    for item_group, data in summarized_data.items():
        target_qty = data.get("target_qty_group", data.get("target_qty", 0))  # Default to 0 if both are missing
        target_amount = data.get("target_amount_group", data.get("target__amount", 0))  # Default to 0 if both are missing
        # Initialize chart data lists
        initialize_chart_data(data, num_periods)

        # Populate target_qty and target_amount
        distribute_targets(data, num_periods, target_qty, target_amount)

        # Process other fields (actual_qty, grand_total)
        for sales_person in data.get("child_sales_person", []):
            target_docs = frappe.get_all(doctype_target_doc, fields=["item_group", "fiscal_year"], filters={"parent": sales_person})
            doctypes = frappe.get_all(item_group, fields=["*"], filters={"sales_person": sales_person})
            for doctype in doctypes:
                creation_date = doctype.creation.strftime('%Y-%m-%d')
                period_index = get_period_index(doctype.creation.month)
                is_in_fiscal_year = check_fiscal_year_group(target_docs, creation_date)

                # Check for specific item groups
                if is_in_fiscal_year and (doctype.docstatus == 1 if item_group in ("Quotation", "Sales Invoice", "Sales Order") else True):
                    data["chart_data"]["actual_qty"][period_index] += 1
                    if item_group in ("Quotation", "Sales Invoice", "Sales Order"):
                        data["chart_data"]["actual_amount"][period_index] += doctype.grand_total  # Sum grand_total

        # Calculate percentages
        calculate_percentages(data, num_periods)

# General function to group data by periods (Semester, Quarterly, Monthly)
def calculate_percentages(data, num_periods):
    for i in range(num_periods):
        # Calculate percentage_target (actual_qty / target_qty * 100)
        target_qty_value = round(data["chart_data"]["target_qty"][i], 3)
        actual_qty_value = round(data["chart_data"]["actual_qty"][i], 3)
        if target_qty_value > 0:
            data["chart_data"]["percentage_qty"][i] = round((actual_qty_value / target_qty_value) * 100, 3)
        else:
            data["chart_data"]["percentage_qty"][i] = 0  # Handle case where target_qty is 0

        # Calculate percentage_amount (actual_amount / target_amount * 100)
        target_amount_value = round(data["chart_data"]["target_amount"][i], 3)
        actual_amount_value = round(data["chart_data"]["actual_amount"][i], 3)
        if target_amount_value > 0:
            data["chart_data"]["percentage_amount"][i] = round((actual_amount_value / target_amount_value) * 100, 3)
        else:
            data["chart_data"]["percentage_amount"][i] = 0  # Handle case where target_amount is 0

# Check fiscal year group based on creation_date
def check_fiscal_year_group(target_docs, creation_date):
    for doc in target_docs:
        fiscal_year = frappe.get_doc(doctype_fiscal_year, doc.get('fiscal_year'))
        start_date = fiscal_year.year_start_date.strftime('%Y-%m-%d')
        end_date = fiscal_year.year_end_date.strftime('%Y-%m-%d')
        return start_date <= creation_date <= end_date

import json
import re
def print_as_json(data):
    json_str = json.dumps(data, indent=4)  # Convert to formatted JSON string
    colored_json = re.sub(r'\"(.*?)\"(?=\:)', r'\033[32m"\1"\033[0m', json_str)  # Colorize keys
    print(colored_json)
