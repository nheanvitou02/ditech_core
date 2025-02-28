import frappe
import json
import re
from frappe.utils import now

doctype_target_doc = "Target Doc"
doctype_sales_person_target = "Sales Person Target"
doctype_monthly_distribution = "Monthly Distribution"
doctype_monthly_distribution_percentage = "Monthly Distribution Percentage"

MONTHS_ORDER = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]

def print_as_json(data):
    json_str = json.dumps(data, indent=4,default=str)  # Convert to formatted JSON string
    colored_json = re.sub(r'\"(.*?)\"(?=\:)', r'\033[32m"\1"\033[0m', json_str)  # Colorize keys
    print(colored_json)

@frappe.whitelist()
def get_target_team(sales_person, fiscal_year):
    if sales_person and fiscal_year:
        sales_person_target = frappe.get_all(doctype_sales_person_target, fields=['*'], filters={'sales_person': sales_person})
        
        if sales_person_target:
            filters_value = {
                'parenttype': 'Sales Person Target',
                'parent': sales_person_target[0].name,
                'fiscal_year': fiscal_year
            }
            
            # Define the custom order
            order_map = {"Lead": 1,"Opportunity": 2,"Quotation": 3,"Sales Order": 4,"Sales Invoice": 5}
            
            # Fetch item groups
            item_group = frappe.get_all(
                doctype_target_doc,
                fields=['name', 'item_group', 'fiscal_year', 'target_qty', 'target__amount', 'target_distribution','parent'],
                filters=filters_value
            )
            
            # Sort item_group based on the defined order_map
            item_group.sort(key=lambda x: order_map.get(x.get('item_group'), 6))  # Default to 6 if not found
            get_monthly_distribution(item_group)
            # print_as_json(item_group)
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
            
            # Convert each object to a dictionary
            monthly_distribution = [d.as_dict() for d in monthly_distribution]

            i['monthly_distribution'] = monthly_distribution

            for j in i.get("monthly_distribution"):
                calculate_qty = round((j.get("percentage_allocation") / 100) * i.get("target_qty") or 0, 2)
                calculate_amount = round((j.get("percentage_allocation_amount") / 100) * i.get("target__amount") or 0, 2)
                
                j['target_qty'] = calculate_qty
                j['target__amount'] = calculate_amount
    return item_group

@frappe.whitelist()
def create_updated_monthly_dist(data):
    try:
        data = json.loads(data)
        monthly_dist = monthly_distribution(data)
        data = calculate_qty_amount_percentages(data)
        create_monthly_distribution_percentage(data, monthly_dist)
        set_target_sales_per(data)
        frappe.msgprint("Saved",alert=True,indicator='green')
    except Exception as e:
        frappe.log_error(f"Error in create_updated_monthly_dist: {str(e)}")  
        frappe.local.response["http_status_code"] = 417
        return frappe.msgprint(str(e),alert=True,indicator='red')

def monthly_distribution(data):
    monthly_dist = []
    seen = set()
    for entry in data:
        key = (entry["target_group"], entry["sales_person"], entry["fiscal_year"])
        if key not in seen:
            seen.add(key)
            monthly_dist.append({k: entry[k] for k in ("target_group", "sales_person", "fiscal_year",'parent')})
    return monthly_dist

def calculate_qty_amount_percentages(data):
    for entry in data:
        entry.update({
            'percentage_allocation': entry['total_qty'] and (entry['target_qty'] / entry['total_qty']) * 100 or 0,
            'percentage_allocation_amount': entry['total_amount'] and (entry['target_amount'] / entry['total_amount']) * 100 or 0,
        })
    return data

def create_monthly_distribution_percentage(data, monthly_dist):
    # print_as_json(data)

    for entry in data:
        monthly_dist_name = entry["sales_person"] + " " + entry["target_group"] + " " + entry["fiscal_year"]
        month = entry["month"]

        # Create or update percentage distribution
        idx = MONTHS_ORDER.index(month) + 1  # Add 1 for the idx
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

        create_monthly_distribution(entry,monthly_dist_name)

def create_monthly_distribution(entry,monthly_dist_name):
    # Check if the distribution already exists
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
        
    else:
        frappe.db.sql("""
            UPDATE `tabMonthly Distribution`
            SET distribution_id = %(name)s, modified = NOW(), modified_by = %(owner)s
            WHERE name = %(name)s
        """, {
            "name": monthly_dist_name,
            "owner": frappe.session.user,  
        })
        frappe.db.commit()  
        entry["target_distribution"] = monthly_dist_name
def set_target_sales_per(data):
    # print_as_json(data)
    data_unique = []
    seen = set()
    for entry in data:
        del entry["month"]
        del entry["target_qty"]
        del entry["target_amount"]
        key = (entry["target_group"], entry["sales_person"], entry["fiscal_year"])
        if key not in seen:
            seen.add(key)
            data_unique.append(entry)
    for entry in data_unique:   
        target_group = entry["target_group"]
        fiscal_year = entry["fiscal_year"]
        target_distribution = entry["target_distribution"]
        parent = entry["parent"]
        total_qty = entry["total_qty"]
        total_amount = entry["total_amount"]
        # update target doc
        doc = frappe.get_doc(doctype_target_doc, {"item_group": target_group, "fiscal_year": fiscal_year, "parent": parent})
        doc.target_qty = total_qty
        doc.target__amount = total_amount
        doc.target_distribution = target_distribution
        doc.save()
        frappe.db.commit()
        update_sales_person_target(parent)
def update_sales_person_target(name):
    frappe.db.sql("""
    UPDATE `tabSales Person Target` SET modified = NOW() WHERE name = %(name)s
    """, {
        "name": name
    })
    frappe.db.commit()


