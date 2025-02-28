# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import json

import frappe
from frappe.utils import nowdate, now, cint, cstr, flt, time_diff_in_hours, get_fullname
from frappe.utils.nestedset import get_root_of

from erpnext.accounts.doctype.pos_invoice.pos_invoice import (
    get_stock_availability,
    get_bin_qty,
    get_pos_reserved_qty,
)
from erpnext.accounts.doctype.pos_profile.pos_profile import (
    get_child_nodes,
    get_item_groups,
)
from erpnext.stock.utils import scan_barcode
from ditech_core.ditech_core.utils import (
    make_publish_realtime,
    check_opening,
    check_user_service,
    ref_tb,
    ref_kch,
    ref_cfd,
    ref_cfd_iamge,
    get_currency_exchange,
    get_last_paid_invoice,
)
from ditech_core.ditech_core.qr_bakong import (
    get_bakong_qr,
    check_transaction_payment,
    create_bank_transaction,
)

doctype_pos_profile = "POS Profile"
doctype_company = "Company"
doctype_pos_table = "POS Table"
doctype_pos_invoice = "POS Invoice"
doctype_pos_reason = "POS Reason"
doctype_pos_invoice_item = "POS Invoice Item"
doctype_pos_log_delete_item = "POS Log Delete Item"
doctype_pos_user_detail = "POS User Detail"
doctype_pos_user_service = "POS User Service"
doctype_product_bundle = "Product Bundle"
doctype_product_bundle_item = "Product Bundle Item"
doctype_currency = "Currency"
doctype_item = "Item"
doctype_item_group = "Item Group"
doctype_pos_item = "POS Item"
doctype_customer_order = "Customer Order"


@frappe.whitelist()
def get_tables(start, page_length, pos_profile, status="", floor="", search_term=""):
    warehouse = frappe.db.get_value(doctype_pos_profile, pos_profile, "warehouse")
    table_query = f"""SELECT
                        tpt.name,
                        tpt.label,
                        tpt.status,
                        tpt.pos_invoice,
                        tpt.invoice_split
                    FROM
                        `tabPOS Table` tpt
                    WHERE tpt.disabled = 0
                    AND tpt.pos_profile = '{pos_profile}'
                    AND tpt.label LIKE '%{search_term}%'
    """
    if floor:
        table_query += f""" AND tpt.pos_floor = '{floor}'"""

    if status:
        table_query += f""" AND tpt.status = '{status}'"""

    table_query += """ ORDER By tpt.index ASC"""

    table_query += f""" LIMIT {page_length} OFFSET {start}"""

    tables_data = frappe.db.sql(table_query, as_dict=1)

    pos_items = frappe.db.get_all(
        doctype_pos_item, {"parent": pos_profile}, pluck="item_code"
    )

    data = {"tables": tables_data, "actual_items": []}
    if len(pos_items):
        data["actual_items"] = get_actual_items(warehouse, pos_items)

    return data


@frappe.whitelist()
def get_item_groups_list(pos_profile):
    pos_item_group = get_pos_item_group(pos_profile)
    all_item_group = []

    if pos_item_group:
        for ig in pos_item_group:
            if ig["is_group"]:
                child_item_groups = frappe.db.sql(
                    """
                    SELECT tig.name as item_group, tig.idx
                    FROM `tabItem Group` tig
                    WHERE tig.parent_item_group = %s
                    ORDER BY tig.idx ASC
                    """,
                    (ig["item_group"],),
                    as_dict=1,
                )
                all_item_group.extend(x["item_group"] for x in child_item_groups)
            all_item_group.append(ig["item_group"])
        all_item_group = list(dict.fromkeys(all_item_group))
    else:
        all_item_group = frappe.db.get_all(
            "Item Group",
            fields=["name as item_group"],
            filters={"is_group": 0},
            order_by="idx ASC",
        )
        all_item_group = [x["item_group"] for x in all_item_group]
    return all_item_group


def get_pos_item_group(name):
    return frappe.db.sql(
        """
        SELECT tpig.item_group, tig.is_group, tpig.idx
        FROM `tabPOS Item Group` tpig
        JOIN `tabItem Group` tig ON tig.name = tpig.item_group
        WHERE tpig.parent = %s
        ORDER BY tpig.idx ASC
        """,
        (name,),
        as_dict=1,
    )


def search_by_term(search_term, warehouse, price_list):
    result = search_for_serial_or_batch_or_barcode_number(search_term) or {}

    item_code = result.get("item_code", search_term)
    serial_no = result.get("serial_no", "")
    batch_no = result.get("batch_no", "")
    barcode = result.get("barcode", "")

    if not result:
        return

    item_doc = frappe.get_doc("Item", item_code)

    if not item_doc:
        return

    item = {
        "barcode": barcode,
        "batch_no": batch_no,
        "description": item_doc.description,
        "is_stock_item": item_doc.is_stock_item,
        "item_code": item_doc.name,
        "item_image": item_doc.image,
        "item_name": item_doc.item_name,
        "serial_no": serial_no,
        "stock_uom": item_doc.stock_uom,
        "uom": item_doc.stock_uom,
    }

    if barcode:
        barcode_info = next(
            filter(lambda x: x.barcode == barcode, item_doc.get("barcodes", [])), None
        )
        if barcode_info and barcode_info.uom:
            uom = next(filter(lambda x: x.uom == barcode_info.uom, item_doc.uoms), {})
            item.update(
                {
                    "uom": barcode_info.uom,
                    "conversion_factor": uom.get("conversion_factor", 1),
                }
            )

    item_stock_qty, is_stock_item = get_stock_availability(item_code, warehouse)
    item_stock_qty = item_stock_qty // item.get("conversion_factor", 1)
    item.update({"actual_qty": item_stock_qty})

    price = frappe.get_list(
        doctype="Item Price",
        filters={
            "price_list": price_list,
            "item_code": item_code,
            "batch_no": batch_no,
        },
        fields=["uom", "currency", "price_list_rate", "batch_no"],
    )

    def __sort(p):
        p_uom = p.get("uom")

        if p_uom == item.get("uom"):
            return 0
        elif p_uom == item.get("stock_uom"):
            return 1
        else:
            return 2

    # sort by fallback preference. always pick exact uom match if available
    price = sorted(price, key=__sort)

    if len(price) > 0:
        p = price.pop(0)
        item.update(
            {
                "currency": p.get("currency"),
                "price_list_rate": p.get("price_list_rate"),
            }
        )

    return {"items": [item]}


@frappe.whitelist()
def get_items(start, page_length, price_list, item_group, pos_profile, search_term=""):
    warehouse, hide_unavailable_items = frappe.db.get_value(
        doctype_pos_profile, pos_profile, ["warehouse", "hide_unavailable_items"]
    )

    result = []

    if search_term:
        result = search_by_term(search_term, warehouse, price_list) or []
        if result:
            return result

    if not frappe.db.exists("Item Group", item_group):
        item_group = get_root_of("Item Group")

    condition = get_conditions(search_term)
    condition += get_item_group_condition(pos_profile)

    lft, rgt = frappe.db.get_value("Item Group", item_group, ["lft", "rgt"])

    bin_join_selection, bin_join_condition = "", ""
    if hide_unavailable_items:
        bin_join_selection = ", `tabBin` bin"
        bin_join_condition = "AND bin.warehouse = %(warehouse)s AND bin.item_code = item.name AND bin.actual_qty > 0"

    items_data = frappe.db.sql(
        """
		SELECT
			item.name AS item_code,
			item.item_name,
			item.description,
			item.stock_uom,
			item.image AS item_image,
			item.is_stock_item
		FROM
			`tabItem` item {bin_join_selection}
		WHERE
			item.disabled = 0
			AND item.has_variants = 0
			AND item.is_sales_item = 1
			AND item.is_fixed_asset = 0
			AND item.item_group in (SELECT name FROM `tabItem Group` WHERE lft >= {lft} AND rgt <= {rgt})
			AND {condition}
			{bin_join_condition}
		ORDER BY
			item.name asc
		LIMIT
			{page_length} offset {start}""".format(
            start=cint(start),
            page_length=cint(page_length),
            lft=cint(lft),
            rgt=cint(rgt),
            condition=condition,
            bin_join_selection=bin_join_selection,
            bin_join_condition=bin_join_condition,
        ),
        {"warehouse": warehouse},
        as_dict=1,
    )

    # return (empty) list if there are no results
    if not items_data:
        return result

    for item in items_data:
        uoms = frappe.get_doc("Item", item.item_code).get("uoms", [])

        item.actual_qty, _ = get_stock_availability(item.item_code, warehouse)
        item.uom = item.stock_uom

        item_price = frappe.get_all(
            "Item Price",
            fields=["price_list_rate", "currency", "uom", "batch_no"],
            filters={
                "price_list": price_list,
                "item_code": item.item_code,
                "selling": True,
            },
        )

        if not item_price:
            result.append(item)

        for price in item_price:
            uom = next(filter(lambda x: x.uom == price.uom, uoms), {})

            if price.uom != item.stock_uom and uom and uom.conversion_factor:
                item.actual_qty = item.actual_qty // uom.conversion_factor

            result.append(
                {
                    **item,
                    "price_list_rate": price.get("price_list_rate"),
                    "currency": price.get("currency"),
                    "uom": price.uom or item.uom,
                    "batch_no": price.batch_no,
                }
            )
    pos_items = frappe.db.get_all(
        doctype_pos_item, {"parent": pos_profile}, pluck="item_code"
    )
    data = {"items": result, "actual_items": []}
    if len(pos_items):
        data["actual_items"] = get_actual_items(warehouse, pos_items)
    return data


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_item_query(doctype, txt, searchfield, start, page_len, filters):
    items = get_items(
        start=start,
        page_length=page_len,
        search_term=txt,
        item_group="All Item Groups",
        price_list=filters.get("price_list"),
        pos_profile=filters.get("pos_profile"),
    )
    return tuple((item["item_name"], item["item_code"]) for item in items["items"])


@frappe.whitelist()
def get_packed_item(item_code):
    if frappe.db.exists(doctype_product_bundle, item_code):
        return frappe.db.get_all(
            doctype_product_bundle_item,
            fields=[
                "item_code",
                "qty",
                "description",
                "uom",
                "rate",
                "parent as parent_item",
            ],
            filters={"parent": item_code},
        )
    return


@frappe.whitelist()
def search_for_serial_or_batch_or_barcode_number(
    search_value: str,
) -> dict[str, str | None]:
    return scan_barcode(search_value)


def get_conditions(search_term):
    condition = "("
    condition += """item.name like {search_term}
		or item.item_name like {search_term}""".format(
        search_term=frappe.db.escape("%" + search_term + "%")
    )
    condition += add_search_fields_condition(search_term)
    condition += ")"

    return condition


def add_search_fields_condition(search_term):
    condition = ""
    search_fields = frappe.get_all("POS Search Fields", fields=["fieldname"])
    if search_fields:
        for field in search_fields:
            condition += " or item.`{}` like {}".format(
                field["fieldname"], frappe.db.escape("%" + search_term + "%")
            )
    return condition


def get_item_group_condition(pos_profile):
    cond = "and 1=1"
    item_groups = get_item_groups(pos_profile)
    if item_groups:
        cond = "and item.item_group in (%s)" % (", ".join(["%s"] * len(item_groups)))

    return cond % tuple(item_groups)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def item_group_query(doctype, txt, searchfield, start, page_len, filters):
    item_groups = []
    cond = "1=1"
    pos_profile = filters.get("pos_profile")

    if pos_profile:
        item_groups = get_item_groups(pos_profile)

        if item_groups:
            cond = "name in (%s)" % (", ".join(["%s"] * len(item_groups)))
            cond = cond % tuple(item_groups)

    return frappe.db.sql(
        f""" select distinct name from `tabItem Group`
			where {cond} and (name like %(txt)s) limit {page_len} offset {start}""",
        {"txt": "%%%s%%" % txt},
    )


@frappe.whitelist()
def check_opening_entry(user):
    return check_user_service(user)


@frappe.whitelist()
def create_opening_voucher(pos_profile, company, balance_details):
    if isinstance(balance_details, str):
        balance_details = json.loads(balance_details)

    new_pos_opening = frappe.get_doc(
        {
            "doctype": "POS Opening Entry",
            "period_start_date": frappe.utils.get_datetime(),
            "posting_date": frappe.utils.getdate(),
            "user": frappe.session.user,
            "pos_profile": pos_profile,
            "company": company,
        }
    )
    new_pos_opening.set("balance_details", balance_details)
    new_pos_opening.submit()

    return new_pos_opening.as_dict()


@frappe.whitelist()
def get_past_order_list(search_term, status, pos_profile, limit=20):
    fields = [
        "name",
        "grand_total",
        "currency",
        "customer",
        "posting_time",
        "posting_date",
    ]
    invoice_list = []

    if search_term and status:
        invoices_by_customer = frappe.db.get_all(
            doctype_pos_invoice,
            filters={
                "customer": ["like", f"%{search_term}%"],
                "status": status,
                "pos_profile": pos_profile,
            },
            fields=fields,
            page_length=limit,
        )
        invoices_by_name = frappe.db.get_all(
            doctype_pos_invoice,
            filters={
                "name": ["like", f"%{search_term}%"],
                "status": status,
                "pos_profile": pos_profile,
            },
            fields=fields,
            page_length=limit,
        )

        invoice_list = invoices_by_customer + invoices_by_name
    elif status:
        invoice_list = frappe.db.get_all(
            doctype_pos_invoice,
            filters={"status": status, "pos_profile": pos_profile},
            fields=fields,
            page_length=limit,
        )

    return invoice_list


@frappe.whitelist()
def get_customer_order_list(search_term, status, pos_profile, limit=20):
    fields = [
        "name",
        "currency",
        "customer",
        "posting_time",
        "posting_date",
        "total_qty",
        "total"
    ]
    invoice_list = []

    if search_term and status:
        invoices_by_customer = frappe.db.get_all(
            "Customer Order",
            filters={
                "customer": ["like", f"%{search_term}%"],
                "status": status,
                "pos_profile": pos_profile,
            },
            fields=fields,
            page_length=limit,
        )
        invoices_by_name = frappe.db.get_all(
            "Customer Order",
            filters={
                "name": ["like", f"%{search_term}%"],
                "status": status,
                "pos_profile": pos_profile,
            },
            fields=fields,
            page_length=limit,
        )

        invoice_list = invoices_by_customer + invoices_by_name
    elif status:
        invoice_list = frappe.db.get_all(
            "Customer Order",
            filters={"status": status, "pos_profile": pos_profile},
            fields=fields,
            page_length=limit,
        )

    return invoice_list


@frappe.whitelist()
def set_customer_info(fieldname, customer, value=""):
    if fieldname == "loyalty_program":
        frappe.db.set_value("Customer", customer, "loyalty_program", value)

    contact = frappe.get_cached_value("Customer", customer, "customer_primary_contact")
    if not contact:
        contact = frappe.db.sql(
            """
			SELECT parent FROM `tabDynamic Link`
			WHERE
				parenttype = 'Contact' AND
				parentfield = 'links' AND
				link_doctype = 'Customer' AND
				link_name = %s
			""",
            (customer),
            as_dict=1,
        )
        contact = contact[0].get("parent") if contact else None

    if not contact:
        new_contact = frappe.new_doc("Contact")
        new_contact.is_primary_contact = 1
        new_contact.first_name = customer
        new_contact.set("links", [{"link_doctype": "Customer", "link_name": customer}])
        new_contact.save()
        contact = new_contact.name
        frappe.db.set_value("Customer", customer, "customer_primary_contact", contact)

    contact_doc = frappe.get_doc("Contact", contact)
    if fieldname == "email_id":
        contact_doc.set("email_ids", [{"email_id": value, "is_primary": 1}])
        frappe.db.set_value("Customer", customer, "email_id", value)
    elif fieldname == "mobile_no":
        contact_doc.set("phone_nos", [{"phone": value, "is_primary_mobile_no": 1}])
        frappe.db.set_value("Customer", customer, "mobile_no", value)
    contact_doc.save()


@frappe.whitelist()
def get_pos_profile_data(pos_profile):
    pos_profile = frappe.get_doc(doctype_pos_profile, pos_profile)
    pos_profile = pos_profile.as_dict()

    _customer_groups_with_children = []
    for row in pos_profile.customer_groups:
        children = get_child_nodes("Customer Group", row.customer_group)
        _customer_groups_with_children.extend(children)

    pos_profile.customer_groups = _customer_groups_with_children
    pos_profile.business_type = pos_profile.custom_business_type
    pos_profile.exchange_rate = 1
    if pos_profile.custom_second_currency:
        pos_profile.exchange_rate = get_currency_exchange(
            pos_profile.currency, pos_profile.custom_second_currency
        )
    return pos_profile


@frappe.whitelist()
def cancel_invoice(invoice, reason):
    inv = frappe.get_doc(doctype_pos_invoice, invoice)
    if inv.custom_is_invoice:
        return
    inv.remarks = frappe.db.get_value(doctype_pos_reason, reason, "reason")
    inv.save()
    inv.submit()
    inv.cancel()
    return


@frappe.whitelist()
def update_table_invoice(**args):
    pos_invoice = frappe.get_doc(doctype_pos_invoice, args["name"])
    pos_invoice.custom_is_invoice = 1
    pos_invoice.custom_invoice_number = get_last_paid_invoice(pos_invoice.pos_profile)
    for payment in pos_invoice.payments:
        payment.amount = 0
        payment.base_amount = 0
    pos_invoice.save()
    if pos_invoice.docstatus == 0:
        pos_table = frappe.get_doc(doctype_pos_table, args["table_name"])
        if pos_table.invoice_split:
            split = pos_table.invoice_split.split(" , ")
            if len(split) > 1:
                for i in split:
                    is_invoice = frappe.db.get_value(doctype_pos_invoice, i, "custom_is_invoice")
                    if not is_invoice:
                        return
        pos_table.status = "Invoiced"
        pos_table.save()
        make_publish_realtime(ref_tb)
    return


@frappe.whitelist()
def merge_table(**args):
    table1 = frappe.get_doc(doctype_pos_table, args["table1"])
    pos_invoice = frappe.get_doc(doctype_pos_invoice, args["invoice_name"])
    label = table1.label
    merge = table1.invoice_merge or pos_invoice.name
    guest_num = pos_invoice.custom_guest_number
    table2 = args["table2"]
    if isinstance(table2, str):
        table2 = json.loads(table2)
    for table in table2:
        inv_table2 = frappe.db.get_value(
            doctype_pos_table, table["pos_table"], "pos_invoice"
        )
        next_inv = frappe.get_doc(doctype_pos_invoice, inv_table2)
        dict_inv = next_inv.as_dict()
        for item in dict_inv["items"]:
            item.update({"custom_old_parent": item["parent"]})
        pos_inv_items_update(pos_invoice, dict_inv["items"])

        tb = frappe.db.get_value(
            doctype_pos_table,
            table["pos_table"],
            ["label", "invoice_merge", "pos_invoice"],
            as_dict=1,
        )
        label = label + " + " + tb.label
        merge = merge + " , " + (tb.invoice_merge or tb.pos_invoice)
        guest_num += next_inv.custom_guest_number
        org_table = frappe.get_doc(doctype_pos_table, table["pos_table"])
        org_table.disabled = 1
        org_table.save()

        next_inv.remarks = "Cancelled by merge"
        next_inv.custom_is_invoice = 0
        next_inv.custom_is_merge = 1
        next_inv.due_date = nowdate()
        next_inv.save()
        next_inv.submit()
        next_inv.cancel()
    table1.label = label
    table1.invoice_merge = merge
    table1.status = "Merged"
    table1.save()
    frappe.db.commit()
    pos_invoice.custom_guest_number = guest_num
    pos_invoice.due_date = nowdate()
    pos_invoice.save()
    return "Successfully"


@frappe.whitelist()
def unmerge_table(table_name):
    pos_table = frappe.get_doc(doctype_pos_table, table_name)
    merges = pos_table.invoice_merge.split(" , ")

    old_doc = frappe.get_doc(doctype_pos_invoice, pos_table.pos_invoice)
    guest_num = old_doc.custom_guest_number
    for inv in merges:
        if inv != old_doc.name:
            old_doc.items = [
                row for row in old_doc.items if row.custom_old_parent != inv
            ]

            cancel_doc = frappe.get_doc(doctype_pos_invoice, inv)
            new_inv = frappe.copy_doc(cancel_doc)
            new_inv.custom_is_merge = 0
            guest_num -= new_inv.custom_guest_number
            new_inv.save()

    labels = pos_table.label.split(" + ")
    pos_table.label = labels[0]
    pos_table.invoice_merge = ""
    pos_table.status = "Occupied"
    pos_table.save()
    frappe.db.commit()

    old_doc.custom_guest_number = guest_num
    old_doc.due_date = nowdate()
    old_doc.save()
    make_publish_realtime(ref_kch)
    return "Successfully"


@frappe.whitelist()
def get_items_table(table_name):
    inv_name = frappe.db.get_value(doctype_pos_table, table_name, "pos_invoice")
    items_inv = frappe.db.sql(
        f"""SELECT
                tpii.name, 
                tpii.item_name, 
                tpii.item_code, 
                tpii.description,
                tpii.warehouse, 
                tpii.qty,
                tpii.rate, 
                tpii.amount, 
                tpii.income_account, 
                tpii.expense_account,
                tpii.cost_center, 
                tpii.uom,
                tpii.stock_uom,
                tpii.serial_and_batch_bundle, 
                tpii.use_serial_batch_fields, 
                tpii.custom_pos_status, 
                tpii.custom_old_parent, 
                tpii.custom_order_time, 
                tpii.serial_no, 
                tpii.batch_no,
                tpii.parent
            FROM
                `tabPOS Invoice Item` tpii 
            WHERE tpii.parent = '{inv_name}'
            ORDER BY tpii.idx ASC
            """,
        as_dict=1,
    )
    return items_inv


@frappe.whitelist()
def move_items(data):
    old_inv = ""
    data = data
    if isinstance(data, str):
        data = json.loads(data)
    for i in data:
        items = i["items"]
        inv_exist = frappe.db.get_value(doctype_pos_table, i["table"], "pos_invoice")
        if inv_exist:
            inv_doc = frappe.get_doc(doctype_pos_invoice, inv_exist)
            if validate_items_change(inv_doc, items):
                if len(items) == 0:
                    inv_doc.remarks = "Cancelled by move"
                    inv_doc.custom_is_move = 1
                    inv_doc.due_date = nowdate()
                    inv_doc.save()
                    inv_doc.submit()
                    inv_doc.cancel()
                    old_inv = inv_doc.name
                else:
                    inv_doc.items = []
                    pos_inv_items_update(inv_doc, items)

                    if old_inv:
                        inv = frappe.db.get_value(
                            doctype_pos_invoice,
                            old_inv,
                            ["name", "custom_pos_table"],
                            as_dict=1,
                        )
                        old_table_doc = frappe.get_doc(
                            doctype_pos_table, inv.custom_pos_table
                        )

                        table_doc = frappe.get_doc(doctype_pos_table, i["table"])
                        merge = old_table_doc.invoice_merge
                        split = old_table_doc.invoice_split
                        if old_table_doc.invoice_merge:
                            merge_inv = old_table_doc.invoice_merge.split(" , ")
                            old_merge = [s for s in merge_inv if s != inv.name]
                            merge = (
                                table_doc.invoice_merge + " , " + " , ".join(old_merge)
                            )

                        if old_table_doc.invoice_split:
                            split_inv = old_table_doc.invoice_split.split(" , ")
                            old_split = [s for s in split_inv if s != inv.name]
                            split = (
                                table_doc.invoice_split + " , " + " , ".join(old_split)
                            )

                        table_doc.invoice_merge = merge
                        table_doc.invoice_split = split
                        table_doc.save()

                        old_table_doc.invoice_merge = ""
                        old_table_doc.invoice_split = ""
                        old_table_doc.save()
                    inv_doc.save()
        else:
            if old_inv:
                inv = frappe.get_doc(doctype_pos_invoice, old_inv)
                old_table_doc = frappe.get_doc(doctype_pos_table, inv.custom_pos_table)
                new_inv = frappe.copy_doc(inv)
                new_inv.custom_pos_table = i["table"]

                new_inv.save()

                table_doc = frappe.get_doc(doctype_pos_table, i["table"])
                merge = old_table_doc.invoice_merge
                split = old_table_doc.invoice_split
                if old_table_doc.invoice_merge:
                    merge_inv = old_table_doc.invoice_merge.split(" , ")
                    merge_inv[0] = new_inv.name
                    merge = " , ".join(merge_inv)

                if old_table_doc.invoice_split:
                    split_inv = old_table_doc.invoice_split.split(" , ")
                    split_inv[0] = new_inv.name
                    split = " , ".join(split_inv)

                table_doc.invoice_merge = merge
                table_doc.invoice_split = split
                table_doc.save()

                old_table_doc.invoice_merge = ""
                old_table_doc.invoice_split = ""
                old_table_doc.save()
            else:
                if len(items) > 0:
                    inv = frappe.get_doc(doctype_pos_invoice, items[0]["parent"])
                    new_inv = frappe.copy_doc(inv)
                    new_inv.custom_pos_table = i["table"]
                    new_inv.custom_is_invoice = 0
                    new_inv.items = []
                    pos_inv_items_update(new_inv, items)
                    new_inv.save()
    return "Successfully"


def validate_items_change(doc, items):
    doc_before_save = doc
    if not doc_before_save:
        return

    if len(doc_before_save.items) != len(items):
        return True

    for prev_item, item in zip(doc_before_save.items, items, strict=False):
        fields = [
            "item_code",
            "qty",
        ]
        b_doc = prev_item.as_dict()
        b_doc["qty"] = int(b_doc["qty"])
        for field in fields:
            if cstr(b_doc[field]) != cstr(item.get(field)):
                return True


@frappe.whitelist()
def get_items_invoice(invoice):
    items_inv = []
    if invoice:
        items_inv = frappe.db.sql(
            f"""SELECT
                    tpii.name, 
                    tpii.item_name, 
                    tpii.item_code, 
                    tpii.description,
                    tpii.warehouse, 
                    tpii.qty,
                    tpii.rate, 
                    tpii.amount, 
                    tpii.income_account, 
                    tpii.expense_account,
                    tpii.cost_center, 
                    tpii.uom,
                    tpii.stock_uom,
                    tpii.serial_and_batch_bundle, 
                    tpii.use_serial_batch_fields, 
                    tpii.custom_pos_status, 
                    tpii.custom_old_parent, 
                    tpii.custom_order_time, 
                    tpii.serial_no, 
                    tpii.batch_no,
                    tpii.parent
                FROM
                    `tabPOS Invoice Item` tpii 
                WHERE tpii.parent = '{invoice}'
                ORDER BY tpii.idx ASC
                """,
            as_dict=1,
        )
    return items_inv


@frappe.whitelist()
def split_invoice(main_invoice, main_items, items):
    if isinstance(main_items, str):
        main_items = json.loads(main_items)
    if isinstance(items, str):
        items = json.loads(items)
    inv = frappe.get_doc(doctype_pos_invoice, main_invoice)

    new_inv = frappe.copy_doc(inv)
    new_inv.custom_is_invoice = 0
    new_inv.custom_is_split = 1
    new_inv.items = []
    # new_inv.custom_guest_number = 1
    pos_inv_items_update(new_inv, items)
    new_inv.save()

    table = frappe.get_doc(doctype_pos_table, inv.custom_pos_table)
    old_split = ""
    if table.invoice_split:
        old_split = table.invoice_split + " , "
    split = old_split + main_invoice + " , " + new_inv.name
    table.invoice_split = " , ".join(set(value.strip() for value in split.split(" , ")))
    table.status = "Occupied"
    table.save()

    inv.items = []
    inv.custom_is_invoice = 0
    inv.custom_is_split = 1
    pos_inv_items_update(inv, main_items)
    inv.save()
    return "Successfully"


def pos_inv_items_update(inv, items):
    for item in items:
        inv.append(
            "items",
            {
                "item_name": item["item_name"],
                "item_code": item["item_code"],
                "description": item["description"],
                "warehouse": item["warehouse"],
                "qty": item["qty"],
                "rate": item["rate"],
                "income_account": item["income_account"],
                "expense_account": item["expense_account"],
                "cost_center": item["cost_center"],
                "uom": item["uom"],
                "stock_uom": item["stock_uom"],
                "serial_and_batch_bundle": item["serial_and_batch_bundle"],
                "use_serial_batch_fields": item["use_serial_batch_fields"],
                "custom_pos_status": item["custom_pos_status"],
                "custom_old_parent": item["custom_old_parent"],
                "custom_order_time": item["custom_order_time"],
                "serial_no": item["serial_no"],
                "batch_no": item["batch_no"],
            },
        )


@frappe.whitelist()
def unsplit_invoice(table):
    table_doc = frappe.get_doc(doctype_pos_table, table)

    invs_split = table_doc.invoice_split.split(" , ")
    inv_doc = frappe.get_doc(doctype_pos_invoice, table_doc.pos_invoice)
    inv_doc.custom_is_invoice = 0
    inv_doc.custom_is_split = 0
    items = []
    for inv in invs_split:
        if inv != inv_doc.name:
            items += get_items_invoice(inv)
            inv_split = frappe.get_doc(doctype_pos_invoice, inv)
            inv_split.remarks = "Cancelled by split"
            inv_split.due_date = nowdate()
            inv_split.save()
            inv_split.submit()
            inv_split.cancel()

    for item in items:
        inv_doc.append(
            "items",
            {
                "item_name": item.item_name,
                "item_code": item.item_code,
                "description": item.description,
                "warehouse": item.warehouse,
                "qty": item.qty,
                "rate": item.rate,
                "amount": item.amount,
                "income_account": item.income_account,
                "expense_account": item.expense_account,
                "cost_center": item.cost_center,
                "uom": item.uom,
                "stock_uom": item.stock_uom,
                "serial_and_batch_bundle": item.serial_and_batch_bundle,
                "use_serial_batch_fields": item.use_serial_batch_fields,
                "custom_pos_status": item.custom_pos_status,
                "custom_old_parent": item.custom_old_parent,
                "custom_order_time": item.custom_order_time,
                "serial_no": item.serial_no,
                "batch_no": item.batch_no,
            },
        )
    inv_doc.save()

    table_doc.invoice_split = ""
    table_doc.status = "Occupied"
    table_doc.save()
    return "Successfully"


@frappe.whitelist()
def get_bar_kitchen(start, page_length, pos_profile, status="", search_term=""):
    def get_note(name):
        if name:
            return frappe.db.get_value("POS Take Note", name, "note")

    item_group = frappe.db.sql(
        f"""
            SELECT
                tpbk.item_group,
                tig.is_group
            FROM
                `tabPOS Bar Kitchen` tpbk
            JOIN `tabItem Group` tig ON
                tig.name = tpbk.item_group
            WHERE
                tpbk.user = '{frappe.session.user}'
                AND tpbk.parent = '{pos_profile}'
                AND tpbk.disabled = 0
        """,
        as_dict=1,
    )

    all_item_group_set = set()

    for ig in item_group:
        if ig["is_group"]:
            child_item_groups = frappe.db.sql(
                f"""
                    SELECT
                        tig.name as item_group
                    FROM `tabItem Group` tig
                    WHERE tig.parent_item_group = '{ig['item_group']}'
                """,
                as_dict=1,
            )
            all_item_group_set.update(x["item_group"] for x in child_item_groups)
        all_item_group_set.add(ig["item_group"])

    all_item_group = list(all_item_group_set)
    if len(all_item_group) > 0:
        query = f"""SELECT
                tpii.name,
                tpt.label as 'table',
                tpii.custom_note1 as 'note1',
                tpii.custom_note2 as 'note2',
                tpii.custom_text_note as 'note3',
                tpii.item_code,
                tpii.item_name,
                tpii.qty,
                tpii.uom,
                tpii.custom_order_time as 'order_time'
            FROM
                `tabPOS Invoice` tpi
            JOIN `tabPOS Table` tpt ON
                tpt.name = tpi.custom_pos_table
            JOIN `tabPOS Invoice Item` tpii ON
                tpii.parent = tpi.name
            WHERE
                tpi.docstatus = 0
            AND tpi.pos_profile = '{pos_profile}'
            AND tpii.custom_pos_status != 'Done'
            """
        if len(all_item_group) == 1:
            query += f""" AND tpii.item_group = '{all_item_group[0]}'"""
        else:
            query += f""" AND tpii.item_group IN {tuple(all_item_group)}"""
        query += " ORDER BY tpii.custom_order_time ASC"
        items = frappe.db.sql(query, as_dict=1)

        for item in items:
            note = []
            if get_note(item["note1"]):
                note += [get_note(item["note1"])]
            if get_note(item["note2"]):
                note += [get_note(item["note2"])]
            note += [item["note3"]]
            item.update({"note": note})

        return items
    return []


@frappe.whitelist()
def confirm_done(data):
    if isinstance(data, str):
        data = json.loads(data)
    frappe.db.set_value(
        doctype_pos_invoice_item,
        data["name"],
        {"custom_pos_status": "Done", "custom_done_time": now()},
    )
    frappe.db.commit()
    data["is_noti"] = True
    opening = check_bar_kitchen()
    if len(opening):
        key = opening[0]["pos_profile"] + "-" + opening[0]["name"]
        frappe.publish_realtime(event=key, message={"type": ref_kch, "data": data})
    return "Successfully"


@frappe.whitelist()
def delete_items(items, invoice, reason):
    if isinstance(items, str):
        items = json.loads(items)
    for item in items:
        log_delete_item(
            item.get("name"), item.get("item_code"), item.get("qty"), reason, invoice
        )
    return


def log_delete_item(name, item, qty, pos_reason, pos_invoice):
    inv = frappe.get_doc(doctype_pos_invoice, pos_invoice)
    inv.items = remove_item(inv.items, name, qty)
    inv.save()

    log_doc = frappe.new_doc(doctype_pos_log_delete_item)
    log_doc.item = item
    log_doc.qty = qty
    log_doc.pos_reason = pos_reason
    log_doc.pos_invoice = pos_invoice
    log_doc.pos_table = inv.custom_pos_table
    log_doc.pos_profile = inv.pos_profile
    log_doc.user = frappe.session.user
    log_doc.insert()


def remove_item(invoice_items, name, qty):
    updated_items = []
    for item in invoice_items:
        if item.name == name:
            if item.qty == qty:
                continue
            elif item.qty > qty:
                item.qty -= qty
        updated_items.append(item)
    return updated_items


@frappe.whitelist()
def check_bar_kitchen():
    bar_kitchen = frappe.db.sql(
        f"""
        SELECT
            tppu.user
        FROM
            `tabPOS Bar Kitchen` tpbk
        JOIN `tabPOS Profile User` tppu ON
            tppu.parent = tpbk.parent
        WHERE
            tpbk.user = '{frappe.session.user}'
            AND tppu.`default` = 1
            AND tpbk.disabled = 0
        """,
        as_dict=1,
    )
    for u in bar_kitchen:
        open = check_opening(u["user"])
        if len(open) > 0:
            return open
    return []


from erpnext.accounts.doctype.pos_closing_entry.pos_closing_entry import (
    get_pos_invoices,
)


@frappe.whitelist()
def make_closing_entry_from_opening(**args):
    closing_entry = frappe.new_doc("POS Closing Entry")
    closing_entry.pos_opening_entry = args["name"]
    closing_entry.period_start_date = args["period_start_date"]
    closing_entry.period_end_date = frappe.utils.get_datetime()
    closing_entry.pos_profile = args["pos_profile"]
    closing_entry.user = args["user"]
    closing_entry.company = args["company"]
    closing_entry.grand_total = 0
    closing_entry.net_total = 0
    closing_entry.total_quantity = 0

    invoices = get_pos_invoices(
        closing_entry.period_start_date,
        closing_entry.period_end_date,
        closing_entry.pos_profile,
        closing_entry.user,
    )

    pos_transactions = []
    taxes = []
    payments = []
    for detail in args["balance_details"]:
        payments.append(
            frappe._dict(
                {
                    "mode_of_payment": detail["mode_of_payment"],
                    "opening_amount": detail["opening_amount"],
                    "expected_amount": detail["opening_amount"],
                }
            )
        )

    for d in invoices:
        pos_transactions.append(
            frappe._dict(
                {
                    "pos_invoice": d.name,
                    "posting_date": d.posting_date,
                    "grand_total": d.grand_total,
                    "customer": d.customer,
                }
            )
        )
        closing_entry.grand_total += flt(d.grand_total)
        closing_entry.net_total += flt(d.net_total)
        closing_entry.total_quantity += flt(d.total_qty)

        for t in d.taxes:
            existing_tax = [
                tx
                for tx in taxes
                if tx.account_head == t.account_head and tx.rate == t.rate
            ]
            if existing_tax:
                existing_tax[0].amount += flt(t.tax_amount)
            else:
                taxes.append(
                    frappe._dict(
                        {
                            "account_head": t.account_head,
                            "rate": t.rate,
                            "amount": t.tax_amount,
                        }
                    )
                )

        for p in d.payments:
            existing_pay = [
                pay for pay in payments if pay.mode_of_payment == p.mode_of_payment
            ]
            if existing_pay:
                existing_pay[0].expected_amount += flt(p.amount)
            else:
                payments.append(
                    frappe._dict(
                        {
                            "mode_of_payment": p.mode_of_payment,
                            "opening_amount": 0,
                            "expected_amount": p.amount,
                        }
                    )
                )

    closing_entry.set("pos_transactions", pos_transactions)
    closing_entry.set("payment_reconciliation", payments)
    closing_entry.set("taxes", taxes)

    return closing_entry


@frappe.whitelist()
def submit_closing_entry(**args):
    closing_shift_doc = frappe.get_doc(args)
    closing_shift_doc.save()
    closing_shift_doc.submit()


@frappe.whitelist()
def get_closing_detail(name):
    get_closing_detail = frappe.get_doc("POS Closing Entry", name)
    downtime = time_diff_in_hours(
        get_closing_detail.period_end_date, get_closing_detail.period_start_date
    )

    # get number of customer and number of transaction
    query_number = f"""
        SELECT 
            COUNT(*) as number_transaction,
            SUM(tpi.paid_amount - tpi.change_amount) as paid_amount,
            SUM(tpi.discount_amount) as item_dis,
            custom_guest_number
        FROM `tabPOS Invoice` tpi 
        WHERE tpi.name IN(SELECT 
                                tdir.pos_invoice 
                            FROM `tabPOS Invoice Reference` tdir 
                            WHERE tdir.parent='{name}')
    """
    get_number = frappe.db.sql(query_number, as_dict=True)

    # get all items
    query_items = f"""
        SELECT      
            tpii.item_code,
            tpii.item_name,
            tpii.base_rate,
            tig.item_group_name,
            SUM(tpii.qty) as qty,
            SUM(tpii.price_list_rate) as amount,
            SUM(tpii.discount_amount) as item_dis
        FROM `tabPOS Invoice Item` tpii 
        JOIN `tabItem Group` tig ON tig.name = tpii.item_group 
        WHERE 
            tpii.parent IN( SELECT tdir.pos_invoice FROM `tabPOS Invoice Reference` tdir WHERE tdir.parent='{name}' )
        GROUP BY tpii.item_code
    """
    get_items = frappe.db.sql(query_items, as_dict=True)
    group_array = []
    items = []
    for i in get_items:
        if i.item_group_name not in group_array:
            group_array.append(i.item_group_name)
            items.append({"item_group": i.item_group_name, "items": [i]})
        else:
            for n in items:
                if n["item_group"] == i.item_group_name:
                    n["items"].append(i)

    # get discount amount
    dis_amount = flt(get_number[0].item_dis)
    service_charge = 0
    tax = 0
    # get discount by items
    for n in get_items:
        dis_amount += flt(n.item_dis)
    # get discount by invoice
    for i in get_closing_detail.taxes:
        tax += flt(i.amount)

    # get invoice tender
    query_num_tendor = f"""
                SELECT 
                    COUNT(*) as num_tendor,
                    SUM(grand_total) as amount_tendor
                FROM `tabPOS Invoice`
                WHERE
                    docstatus=0 AND
                    (creation BETWEEN "{get_closing_detail.period_start_date}" AND "{get_closing_detail.period_end_date}") AND
                    owner="{get_closing_detail.user}"
            """
    get_num_tendor = frappe.db.sql(query_num_tendor, as_dict=True)

    # get invoice void
    query_num_void = f"""
                SELECT 
                    COUNT(*) as num_void,
                    SUM(grand_total) as amount_void
                FROM `tabPOS Invoice`
                WHERE
                    docstatus=2 AND
                    (creation BETWEEN "{get_closing_detail.period_start_date}" AND "{get_closing_detail.period_end_date}") AND
                    owner="{get_closing_detail.user}"
            """
    get_num_void = frappe.db.sql(query_num_void, as_dict=True)

    # payment mode
    total_closing = 0
    total_second_closing = 0
    over_short = 0
    mode_of_payment = []
    for i in get_closing_detail.payment_reconciliation:
        mode_of_payment.append(
            {
                "mode_of_payment": i.mode_of_payment,
                "expected": i.expected_amount,
                "closing": i.closing_amount,
                "second_closing": i.custom_closing_amount,
                "difference": i.difference,
            }
        )
        total_closing += flt(i.closing_amount)
        total_second_closing += flt(i.custom_closing_amount)
        over_short += flt(i.difference)

    return {
        "start": get_closing_detail.period_start_date,
        "end": get_closing_detail.period_end_date,
        "work_hours": round(downtime, 2),
        "start_shift_by": get_fullname(get_closing_detail.user),
        "end_shift_by": get_fullname(get_closing_detail.modified_by),
        "station": get_closing_detail.company,
        "shift_id": get_closing_detail.name,
        "total_qty": get_closing_detail.total_quantity,
        "grand_total": get_closing_detail.grand_total,
        "net_total": get_closing_detail.net_total,
        "number_of_customer": get_number[0].custom_guest_number,
        "number_of_transaction": get_number[0].number_transaction,
        "average_num_cus": round(
            flt(get_number[0].custom_guest_number)
            / flt(get_number[0].number_transaction)
        ),
        "average_tran_val": round(
            (
                flt(get_closing_detail.grand_total)
                / flt(get_number[0].number_transaction)
            ),
            2,
        ),
        "average_val_per_cus": (
            round(
                (
                    flt(get_closing_detail.grand_total)
                    / flt(get_number[0].custom_guest_number)
                ),
                2,
            )
            if flt(get_number[0].custom_guest_number) > 0
            else None
        ),
        "items": items,
        "discount_amount": (round(dis_amount, 2)),
        "service_charge": service_charge,
        "tax": tax,
        "paid_amount": get_number[0].paid_amount,
        "number_tendor": get_num_tendor[0].num_tendor or 0,
        "amount_tendor": get_num_tendor[0].amount_tendor or 0,
        "number_void": get_num_void[0].num_void or 0,
        "amount_void": get_num_void[0].amount_void or 0,
        "pos_profile": get_closing_detail.pos_profile,
        "currency": get_closing_detail.custom_currency,
        "second_currency": get_closing_detail.custom_second_currency,
        "mode_of_payment": mode_of_payment,
        "total_closing": total_closing,
        "total_second_closing": total_second_closing,
        "over_short": over_short,
    }


@frappe.whitelist()
def available_table(table):
    frappe.db.set_value(doctype_pos_table, table, "status", "Opened")
    return "Successfully"


@frappe.whitelist()
def load_data_display(data):
    if isinstance(data, str):
        data = json.loads(data)
    data["symbol"] = frappe.db.get_value(doctype_currency, data["currency"], "symbol")
    if data.get("second_currency", None):
        data["second_symbol"] = frappe.db.get_value(
            doctype_currency, data["second_currency"], "symbol"
        )
    make_publish_realtime(ref_cfd, data, frappe.session.user)
    return


@frappe.whitelist()
def get_payment_qrcode(data):
    data = json.loads(data)
    timeleft = data["timeout"]
    qrcode = get_bakong_qr(**data)
    if qrcode.get("image"):
        make_publish_realtime(
            ref_cfd_iamge,
            {"image": qrcode.get("image") or "", "timeleft": timeleft},
            frappe.session.user,
        )
        return {"md5": qrcode.get("md5")}
    return


@frappe.whitelist()
def check_transaction_payment_job(data):
    if isinstance(data, str):
        data = json.loads(data)
    data_paid = check_transaction_payment(data.get("md5"))
    data = {**data_paid, **data}
    if not data["responseCode"] and data["responseMessage"] == "Success":
        create_bank_transaction(data)
        return "Successfully"
    return


@frappe.whitelist()
def clear_payment_qr():
    make_publish_realtime(ref_cfd_iamge, {"image": "", "timeout": 0})
    return


def get_actual_items(warehouse, items):
    result = []
    items_data = frappe.db.get_all(
        doctype_item,
        fields=[
            "name AS item_code",
            "item_name",
            "stock_uom AS uom",
            "image AS item_image",
            "is_stock_item",
        ],
        filters={
            "disabled": 0,
            "has_variants": 0,
            "is_sales_item": 1,
            "is_fixed_asset": 0,
            "name": ["in", items],
        },
    )

    if not items_data:
        return result

    for item in items_data:
        item_bin_qty = get_bin_qty(item.item_code, warehouse)
        item_pos_reserved_qty = get_pos_reserved_qty(item.item_code, warehouse)
        available_qty = item_bin_qty - item_pos_reserved_qty
        bundle_items = frappe.db.get_all(
            doctype_product_bundle_item,
            filters={"item_code": item.get("item_code")},
            fields=["parent", "qty"],
        )
        if len(bundle_items):
            pos_reserved_qty = 0
            for i in bundle_items:
                parent_qty = get_pos_reserved_qty(i.get("parent"), warehouse)
                pos_reserved_qty += i.get("qty") * parent_qty

            result.append(
                {**item, "actual_qty": round(available_qty - pos_reserved_qty, 2)}
            )
        else:
            result.append({**item, "actual_qty": available_qty})

    return result


@frappe.whitelist()
def update_status_order(name, status):
    doc = frappe.get_doc(doctype_customer_order, name)
    doc.status = status
    doc.save()
    if status == "Confirmed":
        doc.submit()
    return "Successfully"
