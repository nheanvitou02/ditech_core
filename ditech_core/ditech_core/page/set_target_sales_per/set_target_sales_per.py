import frappe
import json
import re
from frappe.utils import now

doctype_target_doc = "Target Doc"
doctype_sales_person_target = "Sales Person Target"
doctype_monthly_distribution = "Monthly Distribution"
doctype_monthly_distribution_percentage = "Monthly Distribution Percentage"

MONTHS_ORDER = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]

###############################################################################
# This function API use to get sales person target
# Request:
#
# Response:
#
# Taks:
#
# History
# 27-02-2024  Tiv    Created
###############################################################################

@frappe.whitelist()
def get_target_team(sales_person, fiscal_year):
    order_map = {"Lead": 1,"Opportunity": 2,"Quotation": 3,"Sales Order": 4,"Sales Invoice": 5}
    if sales_person and fiscal_year:
        sales_person_target = frappe.get_all(doctype_sales_person_target, fields=['*'], filters={'sales_person': sales_person})
        
        if sales_person_target:
            filters_value = {
                'parenttype': 'Sales Person Target',
                'parent': sales_person_target[0].name,
                'fiscal_year': fiscal_year
            }
            
            # FETCH ITEM GROUPS
            item_group = frappe.get_all(
                doctype_target_doc,
                fields=['name', 'item_group', 'fiscal_year', 'target_qty', 'target__amount', 'target_distribution','parent'],
                filters=filters_value
            )
            
            # Sort item_group based on the defined order_map
            item_group.sort(key=lambda x: order_map.get(x.get('item_group').upper(), 6))  # Default to 6 if not found
            item_group.sort(key=lambda x: order_map.get(x.get('item_group'), 6))  # Default to 6 if not found
            get_monthly_distribution(item_group)
            frappe.local.response["http_status_code"] = 200
            return {"success": 1, "data": item_group}
        
        return {"success": 0, "data": []}
    else:
        frappe.local.response["http_status_code"] = 417
        return {"success": 0, "data": []}
def get_monthly_distribution(item_group):
    for i in item_group:
        target_distribution = i.get('target_distribution')
        if target_distribution:
            monthly_distribution = frappe.get_doc(doctype_monthly_distribution, target_distribution).percentages
            
            # CONVERT EACH OBJECT TO A DICTIONARY
            monthly_distribution = [d.as_dict() for d in monthly_distribution]
            i['monthly_distribution'] = monthly_distribution

            for j in i.get("monthly_distribution"):
                calculate_qty = round((j.get("percentage_allocation") / 100) * i.get("target_qty") or 0, 2)
                calculate_amount = round((j.get("percentage_allocation_amount") / 100) * i.get("target__amount") or 0, 2)
                
                j['target_qty'] = calculate_qty
                j['target__amount'] = calculate_amount
    return item_group

# ############################# END FUNCTION ##################################

###############################################################################
# This function API use to set sales person target
# Request:
#
# Response:
#
# Taks:
#
# History
# 27-02-2024  Tiv    Created
###############################################################################

@frappe.whitelist()
def set_sales_person_target(data):
    data = json.loads(data)
    collection_process_insert(data)


def collection_process_insert(data):
    calculate_percentages_qty_amount(data)
    insert_monthly_distribution_percentage(data)
    unique_data = get_unique_sales_person_targets(data)
    insert_sales_person_target(unique_data)
    insert_target_team(unique_data)

def get_unique_sales_person_targets(data):
    data_unique = []
    seen = set()
    for entry in data:
        del entry["month"]
        del entry["target_qty"]
        del entry["target_amount"]
        del entry["percentage_allocation"]
        del entry["percentage_allocation_amount"]
        key = (entry["target_group"], entry["sales_person"], entry["fiscal_year"])
        if key not in seen:
            seen.add(key)
            data_unique.append(entry)
    return data_unique

def insert_sales_person_target(data):
    try:
        for entry in data:   
            sales_person = entry["sales_person"]
            fiscal_year = entry["fiscal_year"]
            if not frappe.db.get_value(
                doctype_sales_person_target,
                {"sales_person": sales_person, "fiscal_year": fiscal_year},
                "name"
            ):
                sales_person_target = frappe.get_doc({
                    "doctype": doctype_sales_person_target,
                    "sales_person": sales_person,
                    "fiscal_year": fiscal_year
                }).insert()
    except Exception as e:
        frappe.log_error(title="Error", message=str(e))
def calculate_percentages_qty_amount(data):
    for entry in data:
        entry.update({
            "percentage_allocation": entry["target_qty"] and (entry["target_qty"] / entry["total_qty"]) * 100 or 0,
            "percentage_allocation_amount": entry["target_amount"] and (entry["target_amount"] / entry["total_amount"]) * 100 or 0,
        })
    return data

def insert_monthly_distribution_percentage(data):
    try:
        for entry in data:
            monthly_dist_name = entry["sales_person"] + " " + entry["target_group"] + " " + entry["fiscal_year"]
            month = entry["month"]

            # CREATE OR UPDATE PERCENTAGE DISTRIBUTION
            idx = MONTHS_ORDER.index(month) + 1 
            if not frappe.db.exists(doctype_monthly_distribution_percentage, {"parent": monthly_dist_name, "month": month}):
                doc = frappe.new_doc(doctype_monthly_distribution_percentage)
                doc.parent = monthly_dist_name
                doc.parenttype = "Monthly Distribution"
                doc.parentfield = "percentages"
                doc.month = month
                doc.idx = idx
            else:
                doc = frappe.get_doc(doctype_monthly_distribution_percentage, {"parent": monthly_dist_name, "month": month})
                doc.idx = idx

            doc.percentage_allocation = entry["percentage_allocation"]
            doc.percentage_allocation_amount = entry["percentage_allocation_amount"]
            doc.save()

            # CALL FUNCTION AUTO INSERT MONTHLY DISTRIBUTE
            insert_monthly_distribution(entry,monthly_dist_name)
    except Exception as e:
        frappe.log_error(title="Error", message=str(e))

def insert_monthly_distribution(entry,monthly_dist_name):
    try:
        if not frappe.db.exists(doctype_monthly_distribution, monthly_dist_name):
            frappe.db.sql("""
                INSERT INTO `tabMonthly Distribution` (name, distribution_id, owner, creation, modified)
                VALUES (%(name)s, %(name)s, %(owner)s, %(creation)s, %(modified)s)
                ON DUPLICATE KEY UPDATE distribution_id = %(name)s
            """, {
                "name": monthly_dist_name,
                "owner": frappe.session.user,
                "creation":  now(),
                "modified":  now(),
            })
            frappe.db.commit() 
            entry["target_distribution"] = monthly_dist_name
    except Exception as e:
        frappe.log_error(title="Error", message=str(e))
def get_existing_target(sales_person_target, target_group, fiscal_year):
    """Check if the target_group and fiscal_year exist in target_team and return the entry if found."""
    for entry in sales_person_target.get("target_team", []):
        if entry.item_group == target_group and entry.fiscal_year == fiscal_year:
            return entry
    return None

def update_or_append_target(sales_person_target, data, target_distribution):
    """Update existing target or append a new one if it does not exist, with alerts."""
    try:
        existing_entry = get_existing_target(sales_person_target, data.get("target_group"), data.get("fiscal_year"))

        if existing_entry:
            # Update existing entry
            existing_entry.target_qty = data.get("total_qty")
            existing_entry.target__amount = data.get("total_amount")
            frappe.msgprint("Existing Target Updated", alert=True, indicator='orange')
        else:
            # Append new entry
            sales_person_target.append("target_team", {
                "item_group": data.get("target_group"), 
                "fiscal_year": data.get("fiscal_year"), 
                "target_qty": data.get("total_qty"), 
                "target__amount": data.get("total_amount"), 
                "target_distribution": target_distribution,
            })
            frappe.msgprint("New Target Created", alert=True, indicator='green')

    except Exception as e:
        frappe.log_error(title="Error", message=str(e))

def insert_target_team(unique_data):
    """Main function to insert target data for sales persons."""
    for data in unique_data:
        target_distribution = f'{data.get("sales_person")} {data.get("target_group")} {data.get("fiscal_year")}'
        parent_name = f'Sales Person {data.get("sales_person")} {data.get("fiscal_year")}'
        
        try:
            if frappe.db.exists(doctype_sales_person_target, {"name": parent_name}):
                sales_person_target = frappe.get_doc(doctype_sales_person_target, parent_name)
            else:
                sales_person_target = frappe.new_doc(doctype_sales_person_target, {
                    "name": parent_name,
                    "sales_person": data.get("sales_person"),
                    "fiscal_year": data.get("fiscal_year"),
                })
            
            update_or_append_target(sales_person_target, data, target_distribution)
            sales_person_target.save()
            frappe.msgprint(f"Target Group Saved", alert=True, indicator='green')
        except Exception as e:
            frappe.log_error(title="Error", message=str(e))
            

# ############################# END FUNCTION ##################################

@frappe.whitelist()
def delete_target_team(target_team,fiscal_year,parent):
    if frappe.db.exists(doctype_target_doc, {"item_group": target_team ,"fiscal_year": fiscal_year,"parent": parent,}):
        target_doc = frappe.get_doc(doctype_target_doc, {"item_group": target_team ,"fiscal_year": fiscal_year,"parent": parent,})
        target_distribution = target_doc.target_distribution
        target_doc.delete()
        delete_target_team_target_distribution(target_distribution)
        frappe.msgprint("Target Group Deleted", alert=True, indicator='red')
    
def delete_target_team_target_distribution(target_distribution):
    if frappe.db.exists(doctype_monthly_distribution, target_distribution):
        monthly_distribution = frappe.get_doc(doctype_monthly_distribution, target_distribution)
        monthly_distribution.percentages = []
        monthly_distribution.delete()
        frappe.msgprint("Monthly Distribution Deleted", alert=True, indicator='red')