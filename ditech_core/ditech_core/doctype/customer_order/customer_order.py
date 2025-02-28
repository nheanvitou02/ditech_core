# Copyright (c) 2025, tech@ditech.software and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import json
from frappe import _
from frappe.utils import flt
from ditech_core.ditech_core.utils import ref_co

doctype_customer_order = "Customer Order"
doctype_customer_order_item = "Customer Order Item"
doctype_pos_invoice = "POS Invoice"


class CustomerOrder(Document):
    def on_submit(self):
        exist_invoice = frappe.db.exists(
            doctype_pos_invoice, {"customer": self.customer, "docstatus": 0}
        )
        if exist_invoice:
            pos_inv = frappe.get_doc(doctype_pos_invoice, exist_invoice)
            pos_inv.custom_is_invoice = 0
            for item in self.items:
                pos_inv.append(
                    "items",
                    {
                        "warehouse": pos_inv.set_warehouse,
                        "cost_center": pos_inv.cost_center,
                        "item_code": item.item_code,
                        "qty": item.qty,
                        "rate": item.rate,
                        "uom": item.uom,
                    },
                )
            pos_inv.save()
        else:
            create_pos_invoice(self)
        self.set_status(update=True)

    def set_status(self, update=False, status=None, update_modified=True):
        if self.is_new():
            if self.get("amended_from"):
                self.status = "Pending"
            return

        if not status:
            if self.docstatus == 2:
                self.status = "Cancelled"
            elif self.docstatus == 1:
                self.status = "Confirmed"
            else:
                self.status = "Pending"

        if update:
            self.db_set("status", self.status, update_modified=update_modified)

    def on_cancel(self):
        pass


@frappe.whitelist(allow_guest=1)
def create_customer_order(data):
    if isinstance(data, str):
        data = json.loads(data)
    doc = frappe.new_doc(doctype_customer_order)
    doc.customer = data.get("customer")
    doc.pos_profile = data.get("pos_profile")
    doc.table = data.get("table")
    doc.customer = data.get("customer")
    doc.selling_price_list = data.get("selling_price_list")
    total_qty = 0
    total = 0
    for item in data.get("items"):
        amount = flt(item.get("rate")) * flt(item.get("qty"))
        doc.append("items", {**item, "amount": amount})
        total_qty += flt(item.get("qty"))
        total += flt(amount)
    doc.total_qty = total_qty
    doc.total = total
    doc.insert(ignore_permissions=1)
    frappe.publish_realtime(
        event=doc.pos_profile, message={"type": ref_co, "data": None}
    )
    return "Successfully"


@frappe.whitelist(allow_guest=1)
def get_order_history(customer, pos_profile, limit=21, start=0):
    orders = frappe.db.get_all(
        doctype_customer_order,
        fields=["*"],
        filters={"customer": customer, "pos_profile": pos_profile},
        page_length=limit,
        start=start,
    )
    for order in orders:
        order["symbol"] = frappe.db.get_value(
            "Currency", order.get("currency"), "symbol"
        )
        order["items"] = frappe.db.get_all(
            doctype_customer_order_item,
            fields=[
                "item_code",
                "item_name",
                "description",
                "qty",
                "uom",
                "rate",
                "amount",
            ],
            filters={"parent": order.get("name")},
        )

    return orders


def create_pos_invoice(args):
    pos_inv = frappe.new_doc(doctype_pos_invoice)
    pos_inv.update_stock = 1
    pos_inv.is_pos = 1
    pos_inv.pos_profile = args.pos_profile
    pos_inv.posting_date = frappe.utils.nowdate()
    pos_inv.company = args.company
    pos_inv.customer = args.customer
    pos_inv.currency = args.currency
    pos_inv.custom_pos_table = args.table
    pos_inv.set_missing_values()
    for item in args.items:
        pos_inv.append(
            "items",
            {
                "warehouse": pos_inv.set_warehouse,
                "cost_center": pos_inv.cost_center,
                "item_code": item.item_code,
                "qty": item.qty,
                "rate": item.rate,
                "uom": item.uom,
                "custom_customer_order": args.name,
                "custom_co_detail": item.name,
            },
        )
    pos_inv.insert()
