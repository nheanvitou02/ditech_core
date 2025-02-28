import frappe
import json
from frappe.utils import flt, today, fmt_money, get_datetime

ref_tb = "Refresh Table"
ref_kch = "Refresh Kitchen"
ref_co = "Refresh CO"
ref_cfd = "Refresh CFD"
ref_cfd_iamge = "Refresh CFD Image"
check_transaction = "Check Transaction"
doctype_pos_user_detail = "POS User Detail"
doctype_pos_user_service = "POS User Service"
doctype_pos_profile = "POS Profile"


def make_publish_realtime(type, data=None, user=None):
    opening = check_user_service(frappe.session.user)
    if len(opening):
        key = opening[0]["pos_profile"]
        frappe.publish_realtime(
            event=key, message={"type": type, "data": data}, user=user
        )
    return


def check_opening(user):
    open_vouchers = frappe.db.get_all(
        "POS Opening Entry",
        filters={"user": user, "pos_closing_entry": ["in", ["", None]], "docstatus": 1},
        fields=["name", "company", "pos_profile", "period_start_date"],
        order_by="period_start_date desc",
    )
    return open_vouchers


def check_user_service(user):
    if len(check_opening(user)):
        return check_opening(user)

    user = frappe.db.sql(
        f"""
        SELECT
            tppu.user
        FROM
            `tabPOS User Service` tpus
        JOIN `tabPOS Profile User` tppu ON
            tppu.parent = tpus.parent
        WHERE
            tpus.user = '{frappe.session.user}'
            AND tppu.`default` = 1
            AND tpus.disabled = 0
        """,
        as_dict=1,
    )

    for u in user:
        open = check_opening(u["user"])
        if len(open) > 0:
            return [open[0].update({"is_service": True})]
    return []

from erpnext import get_default_company
@frappe.whitelist()
def render_print_template(barcodes, item_code, item_name):
    barcodes = json.loads(barcodes)
    new_barcodes = []
    for b in barcodes:
        item_price = frappe.db.get_value(
            "Item Price",
            {"item_code": item_code, "uom": b.get("uom"), "selling": 1},
            ["price_list_rate", "currency"], as_dict=1
        )
        if item_price:
            new_barcodes.append({**b, "price": item_price.price_list_rate, "currency": item_price.currency, "uom": b.get("uom"), "company": get_default_company(), "item_name": item_code})
        else:
            new_barcodes.append({**b, "price": None, "currency": None, "uom": b.get("uom"), "company": get_default_company(), "item_name": item_name})

    rendered_template = frappe.render_template(
        "ditech_core/templates/item_barcode.html",
        {
            "barcodes": new_barcodes,
        },
    )
    return rendered_template


from erpnext.setup.utils import get_exchange_rate


@frappe.whitelist()
def get_currency_exchange(from_currency="USD", to_currency="KHR"):
    return get_exchange_rate(from_currency, to_currency, None, "for_selling")


from ditech_core.ditech_core.qr_code import get_qrcode


def get_data_shift_type(name, company, ref_location):
    data = {"shift": name, "com": company}
    if ref_location:
        ref_location = json.loads(ref_location)
        data["loc"] = [
            {
                "lat": feature["geometry"]["coordinates"][0],
                "lon": feature["geometry"]["coordinates"][1],
            }
            for feature in ref_location["features"]
        ]

    logo = frappe.get_value("Company", company, "company_logo")
    return {"qrcode": get_qrcode(data), "logo": logo}


def get_last_paid_invoice(pos_profile):
    pin = frappe.db.get_value(
        "POS Profile", pos_profile, "custom_prefix_invoice_number"
    )
    if not pin:
        pin = "25INV0000000"
    start_pos_profile = pin[0 : (len(pin) - 7)]

    query = f"""
            SELECT custom_invoice_number from `tabPOS Invoice` tpi 
            WHERE 
                tpi.status in("Paid","consolidated","Draft") AND pos_profile = "{pos_profile}"
                AND tpi.docstatus in(1,0)
                AND tpi.custom_invoice_number is not null
                AND (tpi.custom_invoice_number like "%{start_pos_profile}%" AND CHAR_LENGTH(tpi.custom_invoice_number)={len(pin)})
                ORDER BY tpi.custom_invoice_number desc
                limit 1 offset 0;
        """
    query_old = f"""
            SELECT custom_invoice_number from `tabPOS Invoice` tpi 
            WHERE 
                pos_profile = "{pos_profile}"
                AND tpi.docstatus in(2) 
                AND tpi.modified_by="{frappe.session.user}"
                AND tpi.custom_invoice_number not in(select t1.custom_invoice_number 
                    from `tabPOS Invoice` t1 
                    where t1.docstatus in(1,0)
                        AND t1.custom_invoice_number is not null 
                        AND (t1.custom_invoice_number like "%{start_pos_profile}%" AND CHAR_LENGTH(t1.custom_invoice_number)={len(pin)}))
                AND tpi.custom_invoice_number is not null
                AND (tpi.custom_invoice_number like "%{start_pos_profile}%" AND CHAR_LENGTH(tpi.custom_invoice_number)={len(pin)})
                ORDER BY tpi.custom_invoice_number ASC
                limit 1 offset 0;
        """
    get_old_invoice_number = frappe.db.sql(query_old, as_dict=True)
    invoice_number = ""
    data = frappe.db.sql(query, as_dict=True)
    if len(data) > 0:
        if len(get_old_invoice_number) > 0:
            invoice_number = get_old_invoice_number[0].custom_invoice_number
        else:
            last_inv_number = int(
                flt(
                    data[0].custom_invoice_number[
                        (len(data[0].custom_invoice_number) - 7) :
                    ]
                )
            )
            next_invoice_number = str(last_inv_number + 1).zfill(7)
            invoice_number = (
                data[0].custom_invoice_number[
                    0 : (len(data[0].custom_invoice_number) - 7)
                ]
                + next_invoice_number
            )
    else:
        last_inv_number = int(flt(pin[(len(pin) - 7) :]))
        next_invoice_number = str(last_inv_number + 1).zfill(7)
        invoice_number = start_pos_profile + next_invoice_number
    return invoice_number


def get_data_print_pos_invoice(pos_profile, name):
    data = {}
    data["print_footer"] = frappe.db.get_value(
        doctype_pos_profile, pos_profile, "custom_print_footer"
    )
    data["exchange"] = get_print_currency_exchange(pos_profile)
    data["vat_included"] = (
        False
        if not frappe.db.exists(
            "Sales Taxes and Charges",
            {"parent": name, "included_in_print_rate": 1},
        )
        else True
    )
    return data


def get_print_currency_exchange(pos_profile):
    from_currency, to_currency = frappe.db.get_value(
        doctype_pos_profile, pos_profile, ["currency", "custom_second_currency"]
    )
    exchange = get_exchange_rate(from_currency, to_currency)
    if from_currency == "USD":
        exchange = get_exchange_rate("USD", "KHR")
        return {"from_currency": "USD", "to_currency": "KHR", "exchange": exchange}

    if from_currency == "KHR":
        exchange = get_exchange_rate("KHR", "USD")
        return {"from_currency": "KHR", "to_currency": "USD", "exchange": exchange}

    return {
        "from_currency": from_currency,
        "to_currency": to_currency,
        "exchange": exchange,
    }


def get_note_print_pos_invoice(name):
    notes = []
    note1, note2, note3 = frappe.db.get_value(
        "POS Invoice Item", name, ["custom_note1", "custom_note2", "custom_text_note"]
    )
    if note1:
        notes.append(frappe.db.get_value("POS Take Note", note1, "note"))
    if note2:
        notes.append(frappe.db.get_value("POS Take Note", note2, "note"))
    if note3:
        notes.append(note3)

    return ", ".join(notes)


def get_loyalty_points_print_pos_invoice(
    customer,
    invoice,
    loyalty_program,
    expiry_date=None,
    company=None,
    include_expired_entry=False,
):

    new_lp_details = frappe.db.sql(
        f"""select sum(loyalty_points) as new_lp, creation from `tabLoyalty Point Entry`
        where customer=%s and loyalty_program=%s and invoice=%s
        """,
        (customer, loyalty_program, invoice),
        as_dict=1,
    )
    new_lp = 0
    old_lp = 0
    if new_lp_details:
        new_lp = new_lp_details[0].new_lp or 0

        if not expiry_date:
            expiry_date = today()

        condition = ""
        if company:
            condition = " and company=%s " % frappe.db.escape(company)
        if not include_expired_entry:
            condition += " and expiry_date>='%s' " % expiry_date
        old_lp_details = frappe.db.sql(
            f"""select sum(loyalty_points) as old_lp from `tabLoyalty Point Entry`
            where customer=%s and loyalty_program=%s and creation<=%s and invoice!=%s
            {condition}
            group by customer""",
            (customer, loyalty_program, new_lp_details[0].creation, invoice),
            as_dict=1,
        )
        if old_lp_details:
            old_lp = old_lp_details[0].old_lp or 0

    operator = "+" if new_lp >= 0 else "-"

    get_coversion_factor = frappe.db.get_value(
        "Loyalty Program", loyalty_program, "conversion_factor"
    )
    currency = frappe.get_cached_value("Company", company, "default_currency")
    return {
        "points": f"""ពិន្ទុចាស់​ {operator} ពិន្ទុថ្មី : {int(old_lp)} {operator} {int(abs(new_lp))} = {int(old_lp+new_lp)}""",
        "amount": f""" = {fmt_money((old_lp+new_lp) * get_coversion_factor, currency=currency)}""",
    }


def get_last_waiting_number(pos_profile):
    default_number = frappe.get_all(
        "POS Profile",
        fields=["name", "custom_start_wait_number", "custom_end_wait_number", "custom_wait_number"],
        filters={"name": pos_profile},
    )

    if len(default_number) and default_number[0].get("custom_wait_number"):
        start_number = int(default_number[0].get("custom_start_wait_number"))
        end_number = int(default_number[0].get("custom_end_wait_number"))
    else:
        return 0
    
    data = frappe.db.sql(
        """select
            custom_waiting_number, name, timestamp(posting_date, posting_time) as "timestamp"
        from
            `tabPOS Invoice`
        where
            docstatus = 1 and pos_profile = %s and ifnull(consolidated_invoice,'') = ''
        Order By posting_date DESC, posting_time DESC limit 1;""",
        (pos_profile),
        as_dict=1
    )

    opening = check_opening(frappe.session.user)
    if len(opening):
        start = opening[0].get("period_start_date")
        data = list(
            filter(
                lambda d: get_datetime(start) <= get_datetime(d.timestamp),
                data,
            )
        )

    waiting_number = 0
    if len(data):
        waiting_number = int(data[0].get("custom_waiting_number"))
    if end_number > waiting_number:
        return waiting_number + 1
    return start_number
