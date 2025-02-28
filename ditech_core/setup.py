import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from ditech_core import constants as CONST
from erpnext import get_default_company


###############################################################################
# after_migration
###############################################################################
# This function is used to add extra
#
# 10-09-2024    CHHAY Sokuon    Created
###############################################################################
def after_migration():
    add_batch_payment_request_in_payment_entry()
    custom_field_asset_movement_item()
    make_custom_field_journal_entry()
    add_company_field()
    add_pos_profile_field()
    add_item_group_field()
    add_item_barcode_field()
    add_pos_invoice_field()
    add_promotional_scheme_field()
    add_pricing_rule_field()
    add_pos_opening_entry_field()
    add_pos_opening_entry_detail_field()
    add_pos_closing_entry_field()
    add_pos_closing_entry_detail_field()
    add_sales_invoice_payment_field()
    add_mode_of_payment_field()
    # add_pos_invoice_item_field()
    # Add custom field
    # add_user_link_field_to_shareholder()
    disable_page_point_of_sale()
    custom_field_on_material_request()
    custom_field_on_purchase_order()
    custom_field_on_purchase_receipt()
    custom_field_on_purchase_invoice()
    make_custom_field_customer()
    make_custom_field_company()
    # make_custom_field_sales_invoice()
    make_custom_field_supplier()
    make_custom_field_material_request()
    make_custom_field_purchase_order()
    make_custom_field_purchase_receipt()
    make_custom_field_purchase_invoice()
    make_custom_field_bank_account()
    make_custom_field_bank_transaction()
    customize_field_for_sales_person()
    make_item_field_percentage_allocation_amount_monthly_distribution_percentage()

# END Function add_extra_options_to_journal_entry_account
    
def customize_field_for_sales_person():
    company = get_default_company()
    if company not in ["103 Wrought Iron", "103 Glass & Aluminum Decor"]:
        make_item_field_sale_person()
        hide_field_targets_sale_person()
        make_item_field_sale_person_lead()
        make_item_field_sale_person_opportunity()
        make_item_field_sale_person_quotation()
        make_item_field_sale_person_sales_invoice()
        make_item_field_sale_person_sales_order()


###############################################################################
# add_batch_payment_request_in_payment_entry
###############################################################################
def add_batch_payment_request_in_payment_entry():
    payment_entry_fields = []
    if not frappe.db.exists(
        CONST.DOCTYPE_CUSTOM_FIELD,
        {
            "dt": CONST.DOCTYPE_PAYMENT_ENTRY,
            "module": "ditech_core",
            "fieldname": "custom_subscription_column_break_01",
        },
    ):
        payment_entry_fields.append(
            frappe._dict(
                fieldname="custom_subscription_column_break_01",
                fieldtype="Column Break",
                insert_after="title",
                is_system_generated=1,
            )
        )

    if not frappe.db.exists(
        CONST.DOCTYPE_CUSTOM_FIELD,
        {
            "dt": CONST.DOCTYPE_PAYMENT_ENTRY,
            "module": "ditech_core",
            "fieldname": "custom_batch_payment_request",
        },
    ):
        payment_entry_fields.append(
            frappe._dict(
                label=_("Batch Payment Request"),
                fieldname="custom_batch_payment_request",
                fieldtype="Link",
                options="Batch Payment Request",
                module="ditech_core",
                insert_after="custom_subscription_column_break_01",
                read_only=1,
                is_system_generated=1,
            )
        )

    if payment_entry_fields:
        custom_fields = {CONST.DOCTYPE_PAYMENT_ENTRY: payment_entry_fields}

        create_custom_fields(custom_fields)


# END Function add_batch_payment_request_in_payment_entry


def custom_field_asset_movement_item():
    custom_fields = {
        "Asset Movement Item": [
            {
                "label": _("From Cost Center"),
                "fieldname": "custom_from_cost_center",
                "fieldtype": "Link",
                "options": "Cost Center",
                "module": "ditech_core",
                "fetch_from": "asset.cost_center",
                "insert_after": "source_location",
            },
            {
                "label": _("To Cost Center"),
                "fieldname": "custom_to_cost_center",
                "fieldtype": "Link",
                "options": "Cost Center",
                "module": "ditech_core",
                "insert_after": "target_location",
            },
        ]
    }

    create_custom_fields(custom_fields)


###############################################################################
# make custom field journal entry
###############################################################################
def make_custom_field_journal_entry():
    custom_fields = {
        "Journal Entry": [
            {
                "label": _("Auto Reverse Journal Entry"),
                "fieldname": "custom_reversed_journal_entry",
                "fieldtype": "Check",
                "default": "0",
                "allow_on_submit": "1",
                "module": "ditech_core",
                "insert_after": "user_remark",
            },
            {
                "label": _("Schedule Date"),
                "fieldname": "custom_schedule_date",
                "fieldtype": "Date",
                "allow_on_submit": "1",
                "module": "ditech_core",
                "mandatory_depends_on": "eval: doc.custom_reversed_journal_entry",
                "depends_on": "eval: doc.custom_reversed_journal_entry",
                "insert_after": "custom_reversed_journal_entry",
            },
        ]
    }

    create_custom_fields(custom_fields)


# check custom field
def exists_field(doctype, field):
    return frappe.db.exists(
        CONST.DOCTYPE_CUSTOM_FIELD,
        {
            "dt": doctype,
            "module": "ditech_core",
            "fieldname": field,
        },
    )


###############################################################################
# add custom field company
###############################################################################
def add_company_field():
    add_fields = [
        {
            "fieldname": "custom_hide_company",
            "fieldtype": "Check",
            "insert_after": "default_holiday_list",
            "label": _("Hide Company"),
            "description": _("Only use in print format"),
            "module": "ditech_core",
        },
        {
            "fieldname": "custom_second_company_name",
            "fieldtype": "Data",
            "insert_after": "company_name",
            "label": _("Second Company Name"),
            "module": "ditech_core",
        },
    ]
    fields = []
    for i in add_fields:
        if not exists_field(CONST.DOCTYPE_COMPANY, i["fieldname"]):
            fields.append(i)
    if fields:
        create_custom_fields({CONST.DOCTYPE_COMPANY: fields})


###############################################################################
# add custom field Mode of Payment
###############################################################################
def add_mode_of_payment_field():
    add_fields = [
        {
            "fieldname": "custom_bank_account",
            "fieldtype": "Link",
            "insert_after": "type",
            "label": _("Bank Account"),
            "module": "ditech_core",
            "options": "Bank Account",
            "depends_on": "eval:doc.type=='Bank'",
        },
    ]
    fields = []
    for i in add_fields:
        if not exists_field(CONST.DOCTYPE_MODE_OF_PAYMENT, i["fieldname"]):
            fields.append(i)
    if fields:
        create_custom_fields({CONST.DOCTYPE_MODE_OF_PAYMENT: fields})


###############################################################################
# add custom field POS Profile
###############################################################################
def add_pos_profile_field():
    add_fields = [
        {
            "fieldtype": "Select",
            "insert_after": "company",
            "label": _("Business Type"),
            "length": 0,
            "fieldname": "custom_business_type",
            "options": "Restaurant\nRetail",
            "default": "Restaurant",
            "module": "ditech_core",
        },
        {
            "fieldname": "custom_user_service_section",
            "fieldtype": "Section Break",
            "label": _("User Service"),
            "insert_after": "payments",
            "module": "ditech_core",
        },
        {
            "fieldname": "custom_pos_user_service",
            "fieldtype": "Table",
            "insert_after": "custom_user_service_section",
            "label": _("User Service"),
            "options": "POS User Service",
            "module": "ditech_core",
        },
        {
            "fieldname": "custom_barkitchen_s",
            "fieldtype": "Section Break",
            "insert_after": "custom_pos_user_service",
            "label": _("Bar/Kitchen"),
            "module": "ditech_core",
        },
        {
            "fieldname": "custom_pos_barkitchen",
            "fieldtype": "Table",
            "insert_after": "custom_barkitchen_s",
            "label": _("Bar/Kitchen"),
            "options": "POS Bar Kitchen",
            "module": "ditech_core",
        },
        {
            "fieldname": "custom_auto_av_table",
            "fieldtype": "Check",
            "insert_after": "allow_discount_change",
            "label": _("Automatically Available Table"),
            "module": "ditech_core",
            "default": 1,
        },
        {
            "fieldname": "custom_receipt_print_format",
            "fieldtype": "Link",
            "insert_after": "print_format",
            "label": _("Receipt Print Format"),
            "module": "ditech_core",
            "options": "Print Format",
        },
        {
            "fieldname": "custom_second_currency",
            "fieldtype": "Link",
            "insert_after": "currency",
            "label": _("Second Currency"),
            "module": "ditech_core",
            "options": "Currency",
        },
        {
            "fieldname": "custom_guest_count",
            "fieldtype": "Check",
            "insert_after": "validate_stock_on_save",
            "label": _("Guest Count"),
            "module": "ditech_core",
        },
        {
            "fieldname": "custom_wait_number",
            "fieldtype": "Check",
            "insert_after": "custom_guest_count",
            "label": _("Wait Number"),
            "module": "ditech_core",
        },
        {
            "fieldname": "custom_start_wait_number",
            "fieldtype": "Int",
            "insert_after": "custom_wait_number",
            "label": _("Start Wait Number"),
            "module": "ditech_core",
            "default": "1",
            "depends_on": "eval:doc.custom_wait_number",
        },
        {
            "fieldname": "custom_end_wait_number",
            "fieldtype": "Int",
            "insert_after": "custom_start_wait_number",
            "label": _("End Wait Number"),
            "module": "ditech_core",
            "default": "100",
            "depends_on": "eval:doc.custom_wait_number",
        },
        {
            "fieldname": "custom_hide_second_price",
            "fieldtype": "Check",
            "insert_after": "hide_unavailable_items",
            "label": _("Hide Second Price Items"),
            "module": "ditech_core",
            "depends_on": "eval:doc.custom_second_currency",
        },
        {
            "fieldname": "custom_prefix_invoice_number",
            "fieldtype": "Data",
            "insert_after": "custom_end_wait_number",
            "label": _("Prefix Invoice Number"),
            "module": "ditech_core",
            "description": "The last 7 characters must be numbers. Example: #..#0000000"
        },
        {
            "fieldname": "custom_video_cfd",
            "fieldtype": "Attach",
            "insert_after": "custom_auto_av_table",
            "label": _("Video CFD"),
            "module": "ditech_core",
        },
        {
            "fieldname": "custom_image_cfd",
            "fieldtype": "Attach Image",
            "insert_after": "custom_video_cfd",
            "label": _("Image CFD"),
            "module": "ditech_core",
        },
        {
            "fieldname": "items",
            "fieldtype": "Table",
            "insert_after": "item_groups",
            "label": _("Items"),
            "module": "ditech_core",
            "options": "POS Item",
            "description": _("Display actual quantity of Items"),
        },
        {
            "fieldname": "custom_print_footer",
            "fieldtype": "Text Editor",
            "insert_after": "select_print_heading",
            "label": _("Print Footer"),
            "module": "ditech_core",
        },
    ]

    fields = []
    for i in add_fields:
        if not exists_field(CONST.DOCTYPE_POS_PROFILE, i["fieldname"]):
            fields.append(i)
    if fields:
        create_custom_fields({CONST.DOCTYPE_POS_PROFILE: fields})


###############################################################################
# add custom field Item Group
###############################################################################
def add_item_group_field():
    add_fields = [
        {
            "description": _("Only use in Quick Material Request"),
            "fieldname": "custom_is_hide_qmr",
            "fieldtype": "Check",
            "insert_after": "is_group",
            "label": _("Hide Item Group"),
            "module": "ditech_core",
        }
    ]

    fields = []
    for i in add_fields:
        if not exists_field(CONST.DOCTYPE_ITEM_GROUP, i["fieldname"]):
            fields.append(i)
    if fields:
        create_custom_fields({CONST.DOCTYPE_ITEM_GROUP: fields})


###############################################################################
# add custom field Item Barcode
###############################################################################
def add_item_barcode_field():
    add_fields = [
        {
            "fieldname": "custom_column_break_obsih",
            "fieldtype": "Column Break",
            "insert_after": "uom",
            "module": "ditech_core",
        },
        {
            "fieldname": "custom_preview",
            "fieldtype": "Barcode",
            "insert_after": "custom_column_break_obsih",
            "label": _("Preview"),
            "read_only": 1,
            "module": "ditech_core",
        },
    ]

    fields = []
    for i in add_fields:
        if not exists_field(CONST.DOCTYPE_ITEM_BARCODE, i["fieldname"]):
            fields.append(i)
    if fields:
        create_custom_fields({CONST.DOCTYPE_ITEM_BARCODE: fields})


###############################################################################
# add custom field Promotional Scheme
###############################################################################
def add_promotional_scheme_field():
    add_fields = [
        {
            "fieldname": "custom_valid_from_time",
            "fieldtype": "Time",
            "insert_after": "valid_upto",
            "label": _("Valid From Time"),
            "module": "ditech_core",
        },
        {
            "fieldname": "custom_valid_upto_time",
            "fieldtype": "Time",
            "insert_after": "custom_valid_from_time",
            "label": _("Valid Upto Time"),
            "module": "ditech_core",
        },
    ]

    fields = []
    for i in add_fields:
        if not exists_field(CONST.DOCTYPE_PROMOTIONAL_SCHEME, i["fieldname"]):
            fields.append(i)
    if fields:
        create_custom_fields({CONST.DOCTYPE_PROMOTIONAL_SCHEME: fields})


###############################################################################
# add custom field Pricing Rule
###############################################################################
def add_pricing_rule_field():
    add_fields = [
        {
            "fieldname": "custom_valid_from_time",
            "fieldtype": "Time",
            "insert_after": "valid_upto",
            "label": _("Valid From Time"),
            "module": "ditech_core",
        },
        {
            "fieldname": "custom_valid_upto_time",
            "fieldtype": "Time",
            "insert_after": "custom_valid_from_time",
            "label": _("Valid Upto Time"),
            "module": "ditech_core",
        },
    ]

    fields = []
    for i in add_fields:
        if not exists_field(CONST.DOCTYPE_PRICING_RULE, i["fieldname"]):
            fields.append(i)
    if fields:
        create_custom_fields({CONST.DOCTYPE_PRICING_RULE: fields})


###############################################################################
# add custom field pos Opening entry
###############################################################################
def add_pos_opening_entry_field():
    add_fields = [
        {
            "fieldname": "custom_currency",
            "fieldtype": "Link",
            "insert_after": "pos_profile",
            "label": _("Currency"),
            "options": "Currency",
            "module": "ditech_core",
            "fetch_from": "pos_profile.currency",
        },
        {
            "fieldname": "custom_second_currency",
            "fieldtype": "Link",
            "insert_after": "custom_currency",
            "label": _("Second Currency"),
            "options": "Currency",
            "module": "ditech_core",
            "fetch_from": "pos_profile.custom_second_currency",
        },
    ]

    fields = []
    for i in add_fields:
        if not exists_field(CONST.DOCTYPE_POS_OPENING_ENTRY, i["fieldname"]):
            fields.append(i)
    if fields:
        create_custom_fields({CONST.DOCTYPE_POS_OPENING_ENTRY: fields})


###############################################################################
# add custom field POS opening Entry Detail
###############################################################################
def add_pos_opening_entry_detail_field():
    add_fields = [
        {
            "fieldname": "custom_opening_amount",
            "fieldtype": "Currency",
            "insert_after": "opening_amount",
            "label": _("Opening Amount"),
            "options": "custom_second_currency",
            "module": "ditech_core",
            "in_list_view": 1,
        },
    ]

    fields = []
    for i in add_fields:
        if not exists_field(CONST.DOCTYPE_POS_OPENING_ENTRY_DETAIL, i["fieldname"]):
            fields.append(i)
    if fields:
        create_custom_fields({CONST.DOCTYPE_POS_OPENING_ENTRY_DETAIL: fields})

    custom_add_options(CONST.DOCTYPE_POS_OPENING_ENTRY_DETAIL, "opening_amount")


###############################################################################
# add custom field pos closing entry
###############################################################################
def add_pos_closing_entry_field():
    add_fields = [
        {
            "fieldname": "custom_currency",
            "fieldtype": "Link",
            "insert_after": "company",
            "label": _("Currency"),
            "options": "Currency",
            "module": "ditech_core",
            "fetch_from": "pos_profile.currency",
        },
        {
            "fieldname": "custom_second_currency",
            "fieldtype": "Link",
            "insert_after": "custom_currency",
            "label": _("Second Currency"),
            "options": "Currency",
            "module": "ditech_core",
            "fetch_from": "pos_profile.custom_second_currency",
        },
    ]

    fields = []
    for i in add_fields:
        if not exists_field(CONST.DOCTYPE_POS_CLOSING_ENTRY, i["fieldname"]):
            fields.append(i)
    if fields:
        create_custom_fields({CONST.DOCTYPE_POS_CLOSING_ENTRY: fields})

    custom_add_options(CONST.DOCTYPE_POS_CLOSING_ENTRY, "grand_total")
    custom_add_options(CONST.DOCTYPE_POS_CLOSING_ENTRY, "net_total")
    custom_add_options("POS Invoice Reference", "grand_total")
    custom_add_options("POS Closing Entry Taxes", "amount")


def custom_add_options(doctype, fieldname):
    frappe.db.sql(
        """
            UPDATE `tabDocField`
            SET options = %s
            WHERE parent = %s AND fieldname = %s
            """,
        ("custom_currency", doctype, fieldname),
    )
    frappe.clear_cache(doctype=doctype)


###############################################################################
# add custom field POS Closing Entry Detail
###############################################################################
def add_pos_closing_entry_detail_field():
    add_fields = [
        {
            "fieldname": "custom_opening_amount",
            "fieldtype": "Currency",
            "insert_after": "opening_amount",
            "label": _("Opening Amount"),
            "options": "custom_second_currency",
            "module": "ditech_core",
            "in_list_view": 1,
            "read_only": 1,
            "columns": 1,
        },
        {
            "fieldname": "custom_closing_amount",
            "fieldtype": "Currency",
            "insert_after": "closing_amount",
            "label": _("Closing Amount"),
            "options": "custom_second_currency",
            "module": "ditech_core",
            "in_list_view": 1,
            "columns": 1,
        },
    ]

    fields = []
    for i in add_fields:
        if not exists_field(CONST.DOCTYPE_POS_CLOSING_ENTRY_DETAIL, i["fieldname"]):
            fields.append(i)
    if fields:
        create_custom_fields({CONST.DOCTYPE_POS_CLOSING_ENTRY_DETAIL: fields})

    custom_add_options(CONST.DOCTYPE_POS_CLOSING_ENTRY_DETAIL, "opening_amount")
    custom_add_options(CONST.DOCTYPE_POS_CLOSING_ENTRY_DETAIL, "expected_amount")
    custom_add_options(CONST.DOCTYPE_POS_CLOSING_ENTRY_DETAIL, "closing_amount")
    custom_add_options(CONST.DOCTYPE_POS_CLOSING_ENTRY_DETAIL, "difference")


###############################################################################
# add custom field POS Invoice Item
###############################################################################
def add_pos_invoice_item_field():
    add_fields = [
        {
            "fieldname": "custom_done_time",
            "fieldtype": "Datetime",
            "insert_after": "custom_take_note",
            "label": _("Done Time"),
            "module": "ditech_core",
            "read_only": 1,
        },
        {
            "fieldname": "custom_note1",
            "fieldtype": "Link",
            "insert_after": "custom_pos_status",
            "label": _("Note1"),
            "module": "ditech_core",
            "options": "POS Take Note",
        },
        {
            "fieldname": "custom_note2",
            "fieldtype": "Link",
            "insert_after": "custom_note1",
            "label": _("Note2"),
            "module": "ditech_core",
            "options": "POS Take Note",
        },
        {
            "fieldname": "custom_note3",
            "fieldtype": "Link",
            "insert_after": "custom_note2",
            "label": _("Note3"),
            "module": "ditech_core",
            "options": "POS Take Note",
        },
        {
            "fieldname": "custom_old_parent",
            "fieldtype": "Data",
            "insert_after": "page_break",
            "label": _("Old Parent"),
            "module": "ditech_core",
            "read_only": 1,
        },
        {
            "default": "Now",
            "fieldname": "custom_order_time",
            "fieldtype": "Datetime",
            "insert_after": "custom_old_parent",
            "label": _("Order Time"),
            "module": "ditech_core",
            "read_only": 1,
        },
        {
            "default": "Todo",
            "fieldname": "custom_pos_status",
            "fieldtype": "Select",
            "insert_after": "custom_done_time",
            "label": _("POS Status"),
            "module": "ditech_core",
            "read_only": 1,
        },
    ]

    fields = []
    for i in add_fields:
        if not exists_field(CONST.DOCTYPE_POS_INVOICE_ITEM, i["fieldname"]):
            fields.append(i)
    if fields:
        create_custom_fields({CONST.DOCTYPE_POS_INVOICE_ITEM: fields})


###############################################################################
# add custom field POS Invoice
###############################################################################
def add_pos_invoice_field():
    add_fields = [
        {
            "fieldname": "custom_pos_table",
            "fieldtype": "Link",
            "insert_after": "pos_profile",
            "label": _("POS Table"),
            "module": "ditech_core",
            "read_only": 1,
            "options": "POS Table",
        },
        {
            "fieldname": "custom_waiting_number",
            "fieldtype": "Int",
            "insert_after": "custom_pos_table",
            "label": _("Waiting Number"),
            "module": "ditech_core",
            "read_only": 1,
        },
        {
            "fieldname": "custom_guest_number",
            "fieldtype": "Int",
            "insert_after": "custom_waiting_number",
            "label": _("Guest Number"),
            "module": "ditech_core",
            "read_only": 1,
        },
        {
            "fieldname": "custom_invoice_number",
            "fieldtype": "Data",
            "insert_after": "custom_pos_table",
            "label": _("Invoice Number"),
            "module": "ditech_core",
            "read_only": 1,
        },
        {
            "fieldname": "custom_receipt_number",
            "fieldtype": "Data",
            "insert_after": "custom_invoice_number",
            "label": _("Receipt Number"),
            "module": "ditech_core",
            "read_only": 1,
            "hidden": 1,
        },
        {
            "fieldname": "custom_is_invoice",
            "fieldtype": "Check",
            "hidden": 1,
            "insert_after": "update_billed_amount_in_delivery_note",
            "label": _("Is Invoiced"),
            "module": "ditech_core",
            "read_only": 1,
        },
        {
            "fieldname": "custom_is_merge",
            "fieldtype": "Check",
            "hidden": 1,
            "insert_after": "custom_is_invoice",
            "label": _("Is Merge"),
            "module": "ditech_core",
            "read_only": 1,
        },
        {
            "fieldname": "custom_is_split",
            "fieldtype": "Check",
            "hidden": 1,
            "insert_after": "custom_is_invoice",
            "label": _("Is Split"),
            "module": "ditech_core",
            "read_only": 1,
        },
        {
            "fieldname": "custom_second_currency",
            "fieldtype": "Link",
            "insert_after": "currency",
            "label": _("Second Currency"),
            "options": "Currency",
            "module": "ditech_core",
            "fetch_from": "pos_profile.custom_second_currency",
        },
    ]

    fields = []
    for i in add_fields:
        if not exists_field(CONST.DOCTYPE_POS_INVOICE, i["fieldname"]):
            fields.append(i)
    if fields:
        create_custom_fields({CONST.DOCTYPE_POS_INVOICE: fields})


###############################################################################
# add custom field sales invoice payment
###############################################################################
def add_sales_invoice_payment_field():
    add_fields = [
        {
            "fieldname": "custom_primary_amount",
            "fieldtype": "Currency",
            "insert_after": "amount",
            "label": _("Amount"),
            "options": "currency",
            "module": "ditech_core",
            "read_only": 1,
        },
        {
            "fieldname": "custom_second_amount",
            "fieldtype": "Currency",
            "insert_after": "amount",
            "label": _("Amount"),
            "options": "custom_second_currency",
            "module": "ditech_core",
            "read_only": 1,
        },
    ]

    fields = []
    for i in add_fields:
        if not exists_field(CONST.DOCTYPE_SALES_INVOICE_PAYMENT, i["fieldname"]):
            fields.append(i)
    if fields:
        create_custom_fields({CONST.DOCTYPE_SALES_INVOICE_PAYMENT: fields})


def disable_page_point_of_sale():
    exist_page = frappe.db.exists("Page", "point-of-sale")
    if exist_page:
        exist = frappe.db.get_value("Page", exist_page, "title")
        if exist:
            frappe.db.set_value("Page", exist_page, "title", "")
            frappe.db.commit()


def exists_field_not_module(doctype, field):
    return frappe.db.exists(
        CONST.DOCTYPE_CUSTOM_FIELD,
        {
            "dt": doctype,
            "fieldname": field,
        },
    )


def custom_field_on_material_request():
    # create_doctype_purchase_option()

    custom_fields = []
    check_field_purchase_option = ["custom_purchase_options", "custom_purchase_option"]
    for i in check_field_purchase_option:
        if not exists_field_not_module("Material Request", i):
            custom_fields.append(
                {
                    "label": _("Purchase Option"),
                    "fieldname": "custom_purchase_option",
                    "fieldtype": "Link",
                    "options": "Purchase Option",
                    "in_standard_filter": 1,
                    "in_list_view": 1,
                    "module": "ditech_core",
                    "insert_after": "schedule_date",
                    "depends_on": "eval:doc.material_request_type=='Purchase'",
                }
            )

    if not exists_field_not_module("Material Request", "custom_asset_code"):
        custom_fields.append(
            {
                "label": _("Asset Code"),
                "fieldname": "custom_asset_code",
                "fieldtype": "Link",
                "options": "Asset",
                "module": "ditech_core",
                "insert_after": "custom_purchase_option",
                "depends_on": "eval:doc.custom_purchase_option=='Repair Asset' && doc.material_request_type=='Purchase'",
            }
        )

    if not exists_field_not_module("Material Request", "custom_column_break_zhzqw"):
        custom_fields.append(
            {
                "label": _(""),
                "fieldname": "custom_column_break_zhzqw",
                "fieldtype": "Column Break",
                "module": "ditech_core",
                "insert_after": "custom_asset_code",
            }
        )

    if not exists_field_not_module("Material Request", "employee"):
        custom_fields.append(
            {
                "label": _("Employee"),
                "fieldname": "employee",
                "fieldtype": "Link",
                "options": "Employee",
                "module": "ditech_core",
                "insert_after": "custom_column_break_zhzqw",
                "depends_on": "eval:doc.custom_purchase_option=='Fixed Asset' && doc.material_request_type=='Purchase'",
            }
        )

    if not exists_field_not_module("Material Request", "project"):
        custom_fields.append(
            {
                "label": _("Project"),
                "fieldname": "project",
                "fieldtype": "Link",
                "options": "Project",
                "module": "ditech_core",
                "insert_after": "employee",
                "depends_on": "eval:in_list(['Project', 'Production', 'Request Expense', 'Operation Expense'], doc.custom_purchase_option)",
            }
        )
    if custom_fields:
        create_custom_fields({"Material Request": custom_fields})


def custom_field_on_purchase_order():

    custom_fields = []
    check_field_purchase_option = ["custom_purchase_options", "custom_purchase_option"]
    for i in check_field_purchase_option:
        if not exists_field_not_module("Purchase Order", i):
            custom_fields.append(
                {
                    "label": _("Purchase Option"),
                    "fieldname": "custom_purchase_option",
                    "fieldtype": "Link",
                    "options": "Purchase Option",
                    "in_standard_filter": 1,
                    "in_list_view": 1,
                    "module": "ditech_core",
                    "insert_after": "schedule_date",
                }
            )

    if not exists_field_not_module("Purchase Order", "custom_asset_code"):
        custom_fields.append(
            {
                "label": _("Asset Code"),
                "fieldname": "custom_asset_code",
                "fieldtype": "Link",
                "options": "Asset",
                "module": "ditech_core",
                "insert_after": "custom_purchase_option",
                "depends_on": "eval:doc.custom_purchase_option=='Repair Asset'",
            }
        )

    if not exists_field_not_module("Purchase Order", "employee"):
        custom_fields.append(
            {
                "label": _("Employee"),
                "fieldname": "employee",
                "fieldtype": "Link",
                "options": "Employee",
                "module": "ditech_core",
                "insert_after": "custom_asset_code",
                "depends_on": "eval:doc.custom_purchase_option=='Fixed Asset'",
            }
        )

    if not exists_field_not_module("Purchase Order", "is_request_for_fixed_asset"):
        custom_fields.append(
            {
                "label": _("Is Request For Fixed Asset"),
                "fieldname": "is_request_for_fixed_asset",
                "fieldtype": "Check",
                "module": "ditech_core",
                "insert_after": "is_subcontracted",
            }
        )

    if custom_fields:
        create_custom_fields({"Purchase Order": custom_fields})


def custom_field_on_purchase_receipt():

    custom_fields = []
    check_field_purchase_option = ["custom_purchase_options", "custom_purchase_option"]
    for i in check_field_purchase_option:
        if not exists_field_not_module("Purchase Receipt", i):
            custom_fields.append(
                {
                    "label": _("Purchase Option"),
                    "fieldname": "custom_purchase_option",
                    "fieldtype": "Link",
                    "options": "Purchase Option",
                    "in_standard_filter": 1,
                    "in_list_view": 1,
                    "module": "ditech_core",
                    "insert_after": "set_posting_time",
                }
            )

    if not exists_field_not_module("Purchase Receipt", "custom_asset_code"):
        custom_fields.append(
            {
                "label": _("Asset Code"),
                "fieldname": "custom_asset_code",
                "fieldtype": "Link",
                "options": "Asset",
                "module": "ditech_core",
                "insert_after": "custom_purchase_option",
                "depends_on": "eval:doc.custom_purchase_option=='Repair Asset'",
            }
        )

    if not exists_field_not_module("Purchase Receipt", "employee"):
        custom_fields.append(
            {
                "label": _("Employee"),
                "fieldname": "employee",
                "fieldtype": "Link",
                "options": "Employee",
                "module": "ditech_core",
                "insert_after": "custom_asset_code",
                "depends_on": "eval:doc.custom_purchase_option=='Fixed Asset'",
            }
        )

    if custom_fields:
        create_custom_fields({"Purchase Receipt": custom_fields})


def custom_field_on_purchase_invoice():

    custom_fields = []
    check_field_purchase_option = ["custom_purchase_options", "custom_purchase_option"]
    for i in check_field_purchase_option:
        if not exists_field_not_module("Purchase Invoice", i):
            custom_fields.append(
                {
                    "label": _("Purchase Option"),
                    "fieldname": "custom_purchase_option",
                    "fieldtype": "Link",
                    "options": "Purchase Option",
                    "in_standard_filter": 1,
                    "in_list_view": 1,
                    "module": "ditech_core",
                    "insert_after": "due_date",
                }
            )

    if not exists_field_not_module("Purchase Invoice", "custom_asset_code"):
        custom_fields.append(
            {
                "label": _("Asset Code"),
                "fieldname": "custom_asset_code",
                "fieldtype": "Link",
                "options": "Asset",
                "module": "ditech_core",
                "insert_after": "custom_purchase_option",
                "depends_on": "eval:doc.custom_purchase_option=='Repair Asset'",
            }
        )

    if not exists_field_not_module("Purchase Invoice", "employee"):
        custom_fields.append(
            {
                "label": _("Employee"),
                "fieldname": "employee",
                "fieldtype": "Link",
                "options": "Employee",
                "module": "ditech_core",
                "insert_after": "custom_asset_code",
                "depends_on": "eval:doc.custom_purchase_option=='Fixed Asset'",
            }
        )

    if custom_fields:
        create_custom_fields({"Purchase Invoice": custom_fields})


def create_doctype_purchase_option():
    if not frappe.db.exists(
        "DocType", {"name": "Purchase Option"}
    ) or not frappe.db.exists("DocType", {"name": "Purchase option"}):
        if not frappe.db.exists("DocType", {"name": "Purchase Option Apply For"}):
            # Purchase Option Apply For
            child = frappe.new_doc("DocType")
            child.__newname = "Purchase Option Apply For"
            child.module = "ditech_core"
            child.istable = 1
            child.editable_grid = 1
            child.allow_rename = 1
            child.append(
                "fields",
                {
                    "label": "Apply For",
                    "fieldtype": "Link",
                    "fieldname": "apply_for_doc",
                    "reqd": 1,
                    "options": "DocType",
                    "in_list_view": 1,
                },
            )
            child.save(ignore_permissions=True)

        # Purchase Option
        new = frappe.new_doc("DocType")
        new.__newname = "Purchase Option"
        new.module = "ditech_core"
        new.quick_entry = 1
        new.append(
            "fields",
            {
                "label": "Title",
                "fieldtype": "Data",
                "fieldname": "title",
                "reqd": 1,
                "in_list_view": 1,
            },
        )
        new.append(
            "fields",
            {
                "label": "Apply For",
                "fieldtype": "Table MultiSelect",
                "fieldname": "apply_for_doc",
                "reqd": 1,
                "options": "Purchase Option Apply For",
            },
        )
        new.append(
            "fields",
            {
                "label": "",
                "fieldtype": "Column Break",
                "fieldname": "column_break_kshp",
            },
        )
        new.append(
            "fields",
            {
                "label": "Auto Create Stock Entry",
                "fieldtype": "Check",
                "fieldname": "auto_create_stock_entry",
            },
        )
        new.append(
            "permissions",
            {
                "role": "System Manager",
                "read": 1,
                "write": 1,
                "create": 1,
                "delete": 1,
                "report": 1,
                "export": 1,
                "share": 1,
                "email": 1,
            },
        )
        new.naming_rule = "By fieldname"
        new.autoname = "field:title"
        new.allow_rename = 1
        new.save(ignore_permissions=True)


def make_custom_field_customer():
    custom_fields = {
        "Customer": [
            {
                "label": _("Foreign"),
                "fieldname": "custom_foreign",
                "fieldtype": "Check",
                "module": "ditech_core",
                "insert_after": "customer_type",
            },
            # {
            #     "label": _("Type of Customer"),
            #     "fieldname": "custom_type_of_customer",
            #     "fieldtype": "Select",
            #     "options": "\nTaxable Person\nNon Taxable Person\nOversea Company",
            #     "module": "ditech_core",
            #     "insert_after": "tax_id",
            # }
        ]
    }

    create_custom_fields(custom_fields)


def make_custom_field_company():
    custom_fields = {
        "Company": [
            {
                "label": _("Type of Company"),
                "fieldname": "custom_type_of_company",
                "fieldtype": "Select",
                "options": "\nVAT 10%\nVAT 0%\nNon-VAT\nVAT State charge 10%\nVAT 10% & Non-VAT\nVAT 10% & VAT 0%",
                "module": "ditech_core",
                "insert_after": "tax_id",
            },
            {
                "label": _("Prepayment of Income Tax"),
                "fieldname": "custom_prepayment_of_income_tax",
                "fieldtype": "Select",
                "options": "\n1%\n5%",
                "module": "ditech_core",
                "insert_after": "custom_type_of_company",
            },
        ]
    }
    create_custom_fields(custom_fields)

def make_custom_field_supplier():
    custom_fields = {
        "Supplier": [
            {
                "label": _("Foreign"),
                "fieldname": "custom_foreign",
                "fieldtype": "Check",
                "module": "ditech_core",
                "insert_after": "supplier_type",
            },
        ]
    }
    create_custom_fields(custom_fields)


# def make_custom_field_sales_invoice():
#     custom_fields = {
#         "Sales Invoice": [
#             {
#                 "label": _("Type Of Customer"),
#                 "fieldname": "custom_type_of_customer",
#                 "fieldtype": "Data",
#                 "hidden": 1,
#                 "read_only": 1,
#                 "fetch_from": "customer.custom_type_of_customer",
#                 "module": "ditech_core",
#                 "insert_after": "customer",
#             },
#             {
#                 "label": _("Type Of Company"),
#                 "fieldname": "custom_type_of_company",
#                 "fieldtype": "Data",
#                 "hidden": 1,
#                 "read_only": 1,
#                 "fetch_from": "company.custom_type_of_company",
#                 "module": "ditech_core",
#                 "insert_after": "company_tax_id",
#             },
#         ],
#     }

#     create_custom_fields(custom_fields)


def make_custom_field_material_request():
    custom_fields = {
        "Material Request": [
            {
                "label": _("Connection Doctype"),
                "fieldname": "custom_connection_doctype",
                "fieldtype": "Section Break",
                "module": "ditech_core",
                "insert_after": "type_section",
                "collapsible": 1,
            },
            {
                "label": _("MR Html"),
                "fieldname": "custom_mr_html",
                "fieldtype": "HTML",
                "module": "ditech_core",
                "insert_after": "custom_connection_doctype",
            },
            {
                "label": _(""),
                "fieldname": "custom_section",
                "fieldtype": "Section Break",
                "module": "ditech_core",
                "insert_after": "custom_mr_html",
            },
        ]
    }
    create_custom_fields(custom_fields)


def make_custom_field_purchase_order():
    custom_fields = {
        "Purchase Order": [
            {
                "label": _("Connection Doctype"),
                "fieldname": "custom_connection_doctype",
                "fieldtype": "Section Break",
                "module": "ditech_core",
                "insert_after": "supplier_section",
                "collapsible": 1,
            },
            {
                "label": _("PO Html"),
                "fieldname": "custom_po_html",
                "fieldtype": "HTML",
                "module": "ditech_core",
                "insert_after": "custom_connection_doctype",
            },
            {
                "label": _(""),
                "fieldname": "custom_section",
                "fieldtype": "Section Break",
                "module": "ditech_core",
                "insert_after": "custom_po_html",
            },
        ]
    }
    create_custom_fields(custom_fields)


def make_custom_field_purchase_receipt():
    custom_fields = {
        "Purchase Receipt": [
            {
                "label": _("Connection Doctype"),
                "fieldname": "custom_connection_doctype",
                "fieldtype": "Section Break",
                "module": "ditech_core",
                "insert_after": "supplier_section",
                "collapsible": 1,
            },
            {
                "label": _("PR Html"),
                "fieldname": "custom_pr_html",
                "fieldtype": "HTML",
                "module": "ditech_core",
                "insert_after": "custom_connection_doctype",
            },
            {
                "label": _(""),
                "fieldname": "custom_section",
                "fieldtype": "Section Break",
                "module": "ditech_core",
                "insert_after": "custom_pr_html",
            },
        ]
    }
    create_custom_fields(custom_fields)


def make_custom_field_purchase_invoice():
    custom_fields = {
        "Purchase Invoice": [
            {
                "label": _("Connection Doctype"),
                "fieldname": "custom_connection_doctype",
                "fieldtype": "Section Break",
                "module": "ditech_core",
                "insert_after": "title",
                "collapsible": 1,
            },
            {
                "label": _("PI Html"),
                "fieldname": "custom_pi_html",
                "fieldtype": "HTML",
                "module": "ditech_core",
                "insert_after": "custom_connection_doctype",
            },
            {
                "label": _(""),
                "fieldname": "custom_section",
                "fieldtype": "Section Break",
                "module": "ditech_core",
                "insert_after": "custom_pi_html",
            },
        ]
    }
    create_custom_fields(custom_fields)


def make_custom_field_bank_account():
    custom_fields = {
        "Bank Account": [
            {
                "label": _("Mapping Bakong"),
                "fieldname": "custom_mapping_bakong",
                "fieldtype": "Check",
                "module": "ditech_core",
                "insert_after": "company",
            },
            {
                "label": _("Bakong Account"),
                "fieldname": "custom_bakong_account",
                "fieldtype": "Data",
                "module": "ditech_core",
                "mandatory_depends_on": "eval: doc.custom_mapping_bakong",
                "depends_on": "eval: doc.custom_mapping_bakong",
                "insert_after": "custom_mapping_bakong",
            },
            {
                "label": _("Bakong Account No"),
                "fieldname": "custom_bakong_account_no",
                "fieldtype": "Data",
                "module": "ditech_core",
                "mandatory_depends_on": "eval: doc.custom_mapping_bakong",
                "depends_on": "eval: doc.custom_mapping_bakong",
                "insert_after": "custom_bakong_account",
            },
        ]
    }
    create_custom_fields(custom_fields)


def make_custom_field_bank_transaction():
    custom_fields = {
        "Bank Transaction": [
            {
                "label": _("Time"),
                "fieldname": "custom_time",
                "fieldtype": "Time",
                "module": "ditech_core",
                "insert_after": "date",
            },
            {
                "label": _("Ref Doc"),
                "fieldname": "custom_ref_doc",
                "fieldtype": "Link",
                "module": "ditech_core",
                "options": "DocType",
                "insert_after": "custom_time",
            },
            {
                "label": _("Ref No"),
                "fieldname": "custom_ref_no",
                "fieldtype": "Dynamic Link",
                "options": "custom_ref_doc",
                "module": "ditech_core",
                "insert_after": "custom_ref_doc",
            },
            {
                "label": _("MD5"),
                "fieldname": "custom_md5",
                "fieldtype": "Data",
                "module": "ditech_core",
                "insert_after": "bank_party_account_number",
            },
            {
                "label": _("Bakong Account No"),
                "fieldname": "custom_bakong_account_no",
                "fieldtype": "Data",
                "module": "ditech_core",
                "insert_after": "bank_party_account_number",
            },
        ]
    }
    create_custom_fields(custom_fields)

###############################################################################
# make custom field Sales Person
###############################################################################
def make_item_field_sale_person():
    custom_fields = {
        "Sales Person": [
            {
                "fieldname": "target_team",
                "fieldtype": "Table",
                "label": "Targets",
                "insert_after": "target_team_monthly",
                "options": "Target Doc",
                "module": "ditech_core",
                "read_only": 1
            },
   
        ]
    }
    try:
        create_custom_fields(custom_fields)
        print("Custom field make_item_field_sale_person for sales team")
    except Exception as e:
        print(f"Error: {e}")

def hide_field_targets_sale_person():
    try:
        # Use Property Setter to hide the 'targets' field
        frappe.make_property_setter({
            "doctype": "Sales Person",
            "fieldname": "targets",
            "property": "hidden",
            "value": 1,
            "property_type": "Check",
            "module": "ditech_core",
        })

        print("Field 'targets' hidden successfully in Sales Person.")
    except Exception as e:
        print(f"Error: {e}")

###############################################################################
# make custom field Sales Person of Lead List
###############################################################################
def make_item_field_sale_person_lead():
    custom_fields = {
        "Lead": [
            {
                "fieldname": "sales_person",
                "fieldtype": "Link",
                "label": "Sales Person",
                "insert_after": "lead_owner",
                "options": "Sales Person",
                "allow_on_submit": 1,
                "module": "ditech_core",
            }
        ]
    }
    try:
        create_custom_fields(custom_fields)
        print("Custom field make_item_field_sale_person lead for sales team")
    except Exception as e:
        print(f"Error: {e}")

###############################################################################
# make custom field Sales Person of Opportunity List
###############################################################################
def make_item_field_sale_person_opportunity():
    custom_fields = {
        "Opportunity": [
            {
                "fieldname": "sales_person",
                "fieldtype": "Link",
                "label": "Sales Person",
                "insert_after": "opportunity_owner",
                "options": "Sales Person",
                "allow_on_submit": 1,
                "module": "ditech_core",
            }
        ]
    }
    try:
        create_custom_fields(custom_fields)
        print("Custom field make_item_field_sale_person opportunity for sales team")
    except Exception as e:
        print(f"Error: {e}")

###############################################################################
# make custom field Sales Person of Quotation List
###############################################################################
def make_item_field_sale_person_quotation():
    custom_fields = {
        "Quotation": [
            {
                "fieldname": "sales_person",
                "fieldtype": "Link",
                "label": "Sales Person",
                "insert_after": "valid_till",
                "options": "Sales Person",
                "allow_on_submit": 1,
                "module": "ditech_core",
            }
        ]
    }
    try:
        create_custom_fields(custom_fields)
        print("Custom field make_item_field_sale_person quotation for sales team")
    except Exception as e:
        print(f"Error: {e}")

###############################################################################
# make custom field Sales Person of Sales Invoice List
###############################################################################
def make_item_field_sale_person_sales_invoice():
    custom_fields = {
        "Sales Invoice": [
            {
                "fieldname": "sales_person",
                "fieldtype": "Link",
                "label": "Sales Person",
                "insert_after": "due_date",
                "options": "Sales Person",
                "allow_on_submit": 1,
                "module": "ditech_core",
            }
        ]
    }
    try:
        create_custom_fields(custom_fields)
        print("Custom field make_item_field_sale_person sales invoice for sales team")
    except Exception as e:
        print(f"Error: {e}")

###############################################################################
# make custom field Sales Person of Sales Order List
###############################################################################
def make_item_field_sale_person_sales_order():
    custom_fields = {
        "Sales Order": [
            {
                "fieldname": "sales_person",
                "fieldtype": "Link",
                "label": "Sales Person",
                "insert_after": "delivery_date",
                "options": "Sales Person",
                "allow_on_submit": 1,
                "module": "ditech_core",
            }
        ]
    }
    try:
        create_custom_fields(custom_fields)
        print("Custom field make_item_field_sale_person sales order for sales team")
    except Exception as e:
        print(f"Error: {e}")

###############################################################################
# make custom field Monthly Distribution Percentage
###############################################################################
def make_item_field_percentage_allocation_amount_monthly_distribution_percentage():
    custom_fields = {
        "Monthly Distribution Percentage": [
            {
                "fieldname": "percentage_allocation_amount",
                "fieldtype": "Float",
                "label": "Percentage Allocation Amount",
                "insert_after": "percentage_allocation",
                "in_list_view": 0,
                "default": 8.333333333333334,
                "module": "ditech_core",
            }
        ]
    }
    try:
        create_custom_fields(custom_fields)
        print("Custom field make_item_field_sale_person sales order for sales team")
    except Exception as e:
        print(f"Error: {e}")