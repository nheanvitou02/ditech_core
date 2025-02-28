import frappe
from frappe.utils import unique
from erpnext import get_default_company

@frappe.whitelist()
def get_connection(**kwargs):
    doctype = kwargs.get('doctype')
    name = kwargs.get('name')
    doc = frappe.get_doc(doctype, name)
    if frappe.db.exists("Workflow", {'document_type': doctype, 'is_active': 1}):
        fields = ['name', 'workflow_state as state']
    else:
        fields = ['name', 'status as state']
    if doctype == "Material Request":
        filters = {'material_request': name}
        list_doctype = [
            {'ref_doc': 'Purchase Order', 'key': 'purchase_order', 'external': 1},
            {'ref_doc': 'Purchase Receipt', 'key': 'purchase_receipt', 'external': 1},
			{'ref_doc': 'Purchase Invoice', 'key': 'purchase_invoice', 'external': 1},
        ]
		
        get_value = frappe.get_all(doctype, fields=fields, filters={'name': name})
        data = {
			'material_request': get_value
        }

    elif doctype == "Purchase Order":
        filters = {'purchase_order': name}
        list_doctype = [
            {'ref_doc': 'Material Request', 'key': 'material_request', 'external': 0, 'key_table': ['items', 'material_request']},
            {'ref_doc': 'Purchase Receipt', 'key': 'purchase_receipt', 'external': 1},
			{'ref_doc': 'Purchase Invoice', 'key': 'purchase_invoice', 'external': 1},
        ]
		
        get_value = frappe.get_all(doctype, fields=fields, filters={'name': name})
        data = {
			'purchase_order': get_value
        }

    elif doctype == "Purchase Receipt":
        filters = {'purchase_receipt': name}
        list_doctype = [
            {'ref_doc': 'Material Request', 'key': 'material_request', 'external': 0, 'key_table': ['items', 'material_request']},
            {'ref_doc': 'Purchase Order', 'key': 'purchase_order', 'external': 0, 'key_table': ['items', 'purchase_order']},
			{'ref_doc': 'Purchase Invoice', 'key': 'purchase_invoice', 'external': 1},
        ]
		
        get_value = frappe.get_all(doctype, fields=fields, filters={'name': name})
        data = {
			'purchase_receipt': get_value
        }

    elif doctype == "Purchase Invoice":
        filters = {'reference_name': name}
        list_doctype = [
            {'ref_doc': 'Purchase Order', 'key': 'purchase_order', 'external': 0, 'key_table': ['items', 'purchase_order']},
			{'ref_doc': 'Purchase Receipt', 'key': 'purchase_receipt', 'external': 0, 'key_table': ['items', 'purchase_receipt']},
        ]

        mr = []
        for ref in doc.items:
            if frappe.db.exists("Purchase Receipt Item", {'name': ref.pr_detail}):
                get_mr = frappe.db.get_value("Purchase Receipt Item", {'name': ref.pr_detail}, ['material_request'])
                mr.append(get_mr)

        material_request = unique(mr)
        
        data_mr = []
        for j in material_request:
            if frappe.db.exists("Material Request", {'name': j}):
                if frappe.db.exists("Workflow", {'document_type': 'Material Request', 'is_active': 1}):
                    fields_ref_doc_mr = ['name', 'workflow_state as state']
                else:
                    fields_ref_doc_mr = ['name', 'status as state']
                get_value_mr = frappe.db.get_value('Material Request', {'name': j}, fields_ref_doc_mr, as_dict=True)
                data_mr.append(get_value_mr)
		
        get_value = frappe.get_all(doctype, fields=fields, filters={'name': name})
        data = {
			'purchase_invoice': get_value,
            'material_request': data_mr
        }
        
    for i in list_doctype:
        if frappe.db.exists("Workflow", {'document_type': i.get('ref_doc'), 'is_active': 1}):
            fields_ref_doc = ['name', 'workflow_state as state']
        else:
            fields_ref_doc = ['name', 'status as state']

        if i.get('external') == 1:
            get_doc = frappe.get_all(
                    i.get('ref_doc'),
                    fields=fields_ref_doc,
                    filters=filters,
                    limit=100,
                    distinct=True,
                    ignore_ifnull=True,
                    order_by='creation desc'
                )
            data.update({i.get('key'): get_doc})

        else:
            get_internals = get_internal_links(doctype, doc, i.get('key_table'), i.get('ref_doc'), fields_ref_doc)
            data.update({i.get('key'): get_internals})    

    if doctype == 'Material Request':
        mr_data = []
        for mr in data.get('purchase_receipt'):
            if frappe.db.exists("Workflow", {'document_type': "Purchase Invoice", 'is_active': 1}):
                fields_ref_doc = ['name', 'workflow_state as state']
            else:
                fields_ref_doc = ['name', 'status as state']

            get_doc = frappe.get_all(
                    "Purchase Invoice",
                    fields=fields_ref_doc,
                    filters={'purchase_receipt': mr.get('name')},
                    limit=100,
                    distinct=True,
                    ignore_ifnull=True,
                    order_by='creation desc'
                )
            mr_data += get_doc
        data.update({'purchase_invoice': mr_data})

    html = frappe.render_template(
                "ditech_core/templates/connection_html.html",
                {
                    "data": data,
                }
            )
        
    return html



def get_internal_links(doctype, doc, link, ref_doc, fields):
    names = []

    if isinstance(link, str):
        # get internal links in parent document
        value = doc.get(link)
        if value and value not in names:
            
            names.append(value)
    elif isinstance(link, list):
        # get internal links in child documents
        table_fieldname, link_fieldname = link
        for row in doc.get(table_fieldname) or []:
            value = row.get(link_fieldname)
            if value and value not in names:
                names.append(value)

    data = []       
    for name in names:
        get_value = frappe.get_all(ref_doc, fields=fields, filters={'name': name})
        data += get_value

    return data

@frappe.whitelist()
def set_sales_person():
    company = get_default_company()
    if company in ["103 Wrought Iron", "103 Glass & Aluminum Decor"]:
        return 'false'
    
    user = frappe.session.user
    if not frappe.db.exists("Employee", {'user_id': user}):
        return ''
    
    employee = frappe.db.get_value("Employee", {'user_id': user}, ['name'])
    if not frappe.db.exists("Sales Person", {'employee': employee, 'enabled': 1}):
        return ''
    
    sales_person = frappe.db.get_value("Sales Person", {'employee': employee, 'enabled': 1}, ['name'])

    return sales_person

