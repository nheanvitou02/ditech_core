import frappe
import requests
import json
import re
import calendar
from frappe.utils import now
from collections import defaultdict
from ditech_core.ditech_core.utils import (
    make_publish_realtime,
    ref_tb,
    ref_kch,
    get_last_waiting_number,
    get_last_paid_invoice
)
from frappe.utils import get_datetime, add_days, cint, flt, getdate, strip
from frappe import _
from hrms.hr.doctype.leave_policy_assignment.leave_policy_assignment import (
    LeavePolicyAssignment,
    get_leave_type_details,
)
from ditech_core import constants as CONST
from erpnext.accounts.doctype.pos_closing_entry.pos_closing_entry import POSClosingEntry
from erpnext.accounts.doctype.pos_invoice.pos_invoice import POSInvoice
from erpnext.controllers.item_variant import make_variant_item_code
from erpnext.stock.doctype.item.item import Item
from erpnext import get_default_company
from erpnext.accounts.doctype.promotional_scheme.promotional_scheme import (
    PromotionalScheme,
    get_pricing_rules,
)
from erpnext.accounts.doctype.loyalty_program.loyalty_program import (
    get_loyalty_program_details_with_points,
)
from erpnext.assets.doctype.asset.asset import Asset

######################## FOR POS ###########################


def update_status(doc, method):
    if doc.custom_pos_table and not doc.custom_is_split:
        pos_table = frappe.get_doc("POS Table", doc.custom_pos_table)
        pos_table.pos_invoice = doc.name
        pos_table.disabled = 0
        pos_table.status = "Invoiced" if doc.custom_is_invoice else "Occupied"
        pos_table.save()
        frappe.db.commit()
        make_publish_realtime(ref_tb)


def on_update_pos_inv(doc, method):
    if doc.custom_pos_table and not doc.custom_is_split:
        for item in doc.get("items"):
            if item.get("__unsaved", None) == 1:
                frappe.db.commit()
                make_publish_realtime(ref_kch)
                break


def update_status_open(doc, method):
    if doc.custom_pos_table and not doc.custom_is_merge and not doc.custom_is_split:
        pos_table = frappe.get_doc("POS Table", doc.custom_pos_table)
        if pos_table.invoice_split:
            split = pos_table.invoice_split.split(" , ")
            if len(split) > 1:
                split.remove(doc.name)
                pos_table.pos_invoice = split[0]
                pos_table.invoice_split = " , ".join(split) if len(split) > 1 else ""
                pos_table.save()

                inv = frappe.get_doc("POS Invoice", split[0])
                inv.custom_is_split = 0
                inv.save()
                make_publish_realtime(ref_tb)
                return

        if pos_table.invoice_merge:
            labels = pos_table.label.split(" + ")
            merge = pos_table.invoice_merge.split(" , ")
            pos_table.label = labels[0]

            if len(merge) > 1:
                for m in merge:
                    if m != doc.name:
                        tb_name = frappe.db.get_value(
                            "POS Invoice", m, "custom_pos_table"
                        )
                        tb = frappe.get_doc("POS Table", tb_name)
                        tb.disabled = 0
                        tb.pos_invoice = ""
                        tb.invoice_merge = ""
                        tb.invoice_split = ""
                        tb.status = "Opened"
                        tb.save()

        pos_table.pos_invoice = ""
        pos_table.invoice_merge = ""
        pos_table.invoice_split = ""
        pos_table.status = (
            "Opened"
            if frappe.db.get_value(
                "POS Profile", doc.pos_profile, "custom_auto_av_table"
            )
            else "Paid"
        )
        pos_table.save()
        make_publish_realtime(ref_tb)


class CustomPOSClosingEntry(POSClosingEntry):
    def validate_pos_invoices(self):
        invalid_rows = []
        for d in self.pos_transactions:
            invalid_row = {"idx": d.idx}
            pos_invoice = frappe.db.get_values(
                "POS Invoice",
                d.pos_invoice,
                ["consolidated_invoice", "pos_profile", "docstatus", "owner"],
                as_dict=1,
            )[0]
            if pos_invoice.consolidated_invoice:
                invalid_row.setdefault("msg", []).append(
                    _("POS Invoice is already consolidated")
                )
                invalid_rows.append(invalid_row)
                continue
            if pos_invoice.pos_profile != self.pos_profile:
                invalid_row.setdefault("msg", []).append(
                    _("POS Profile doesn't match {}").format(
                        frappe.bold(self.pos_profile)
                    )
                )
            if pos_invoice.docstatus != 1:
                invalid_row.setdefault("msg", []).append(
                    _("POS Invoice is not submitted")
                )

            if invalid_row.get("msg"):
                invalid_rows.append(invalid_row)

        if not invalid_rows:
            return

        error_list = []
        for row in invalid_rows:
            for msg in row.get("msg"):
                error_list.append(_("Row #{}: {}").format(row.get("idx"), msg))

        frappe.throw(error_list, title=_("Invalid POS Invoices"), as_list=True)

    @frappe.whitelist()
    def get_payment_reconciliation_details(self):
        return frappe.render_template(
            "erpnext/accounts/doctype/pos_closing_entry/closing_voucher_details.html",
            {"data": self, "currency": self.custom_currency},
        )


@frappe.whitelist()
def get_pos_invoices(start, end, pos_profile, user):
    data = frappe.db.sql(
        """
	select
		name, timestamp(posting_date, posting_time) as "timestamp"
	from
		`tabPOS Invoice`
	where
		docstatus = 1 and pos_profile = %s and ifnull(consolidated_invoice,'') = ''
	""",
        (pos_profile),
        as_dict=1,
    )

    data = list(
        filter(
            lambda d: get_datetime(start)
            <= get_datetime(d.timestamp)
            <= get_datetime(end),
            data,
        )
    )
    # need to get taxes and payments so can't avoid get_doc
    data = [frappe.get_doc("POS Invoice", d.name).as_dict() for d in data]

    return data


class CustomPOSInvoice(POSInvoice):
    def before_submit(self):
        exist_prefix_invoice_number = frappe.db.get_value("POS Profile", self.pos_profile, "custom_prefix_invoice_number")
        if not self.custom_invoice_number and exist_prefix_invoice_number:
            self.db_set("custom_invoice_number", get_last_paid_invoice(self.pos_profile))
            self.db_set("custom_receipt_number", self.custom_invoice_number)
        else:
            self.db_set("custom_receipt_number", self.name)
        self.db_set("custom_waiting_number", get_last_waiting_number(self.pos_profile))

    def on_submit(self):
        # create the loyalty point ledger entry if the customer is enrolled in any loyalty program
        if not self.is_return and self.loyalty_program:
            self.make_loyalty_point_entry()
        elif self.is_return and self.return_against and self.loyalty_program:
            against_psi_doc = frappe.get_doc("POS Invoice", self.return_against)
            against_psi_doc.delete_loyalty_point_entry()
            against_psi_doc.make_loyalty_point_entry()
        if self.redeem_loyalty_points and self.loyalty_points:
            self.apply_loyalty_points()
        self.check_phone_payments()
        self.set_status(update=True)
        self.make_bundle_for_sales_purchase_return()
        for table_name in ["items", "packed_items"]:
            self.make_bundle_using_old_serial_batch_fields(table_name)
            self.submit_serial_batch_bundle(table_name)

        if self.coupon_code:
            from erpnext.accounts.doctype.pricing_rule.utils import (
                update_coupon_code_count,
            )

            update_coupon_code_count(self.coupon_code, "used")

    def make_loyalty_point_entry(self):
        returned_amount = self.get_returned_amount()
        current_amount = flt(self.base_grand_total) - cint(self.loyalty_amount)
        eligible_amount = current_amount - returned_amount
        lp_details = get_loyalty_program_details_with_points(
            self.customer,
            company=self.company,
            current_transaction_amount=current_amount,
            loyalty_program=self.loyalty_program,
            expiry_date=self.posting_date,
            include_expired_entry=True,
        )
        if (
            lp_details
            and getdate(lp_details.from_date) <= getdate(self.posting_date)
            and (
                not lp_details.to_date
                or getdate(lp_details.to_date) >= getdate(self.posting_date)
            )
        ):
            collection_factor = (
                lp_details.collection_factor if lp_details.collection_factor else 1.0
            )
            points_earned = cint(eligible_amount / collection_factor)

            doc = frappe.get_doc(
                {
                    "doctype": "Loyalty Point Entry",
                    "company": self.company,
                    "loyalty_program": lp_details.loyalty_program,
                    "loyalty_program_tier": lp_details.tier_name,
                    "customer": self.customer,
                    "invoice_type": self.doctype,
                    "invoice": self.name,
                    "loyalty_points": points_earned,
                    "purchase_amount": eligible_amount,
                    "expiry_date": add_days(
                        self.posting_date, lp_details.expiry_duration
                    ),
                    "posting_date": self.posting_date,
                }
            )
            doc.flags.ignore_permissions = 1
            doc.save()
            self.set_loyalty_program_tier()


######################## END POS ###########################


######################## Override item code ###########################
class CustomItem(Item):
    def autoname(self):
        if frappe.db.get_default("item_naming_by") == "Naming Series":
            if self.variant_of:
                if not self.item_code:
                    template_item_name = frappe.db.get_value(
                        "Item", self.variant_of, "item_name"
                    )
                    make_variant_item_code(self.variant_of, template_item_name, self)
            else:
                from frappe.model.naming import set_name_by_naming_series

                set_name_by_naming_series(self)
                self.item_code = self.name
        general_settings = frappe.get_doc("General Settings")
        if general_settings.auto_item_code:
            self.item_name = self.item_name if self.item_name else strip(self.item_code)
            self.item_code = (
                strip(self.item_code)
                + " - "
                + frappe.db.get_value("Company", get_default_company(), "abbr")
            )
            self.name = self.item_code
        else:
            self.item_code = strip(self.item_code)
            self.name = self.item_code


######################## End override item code ###########################


def on_update_asset_movement(self, method):
    if self.assets:
        for i in self.assets:
            old = frappe.db.get_value("Asset", i.asset, "cost_center")
            new = i.custom_to_cost_center
            frappe.db.sql(
                f""" UPDATE `tabAsset` SET cost_center = '{new}' WHERE name = '{i.asset}'; """,
                as_dict=True,
            )

            if new != old:
                version = frappe.new_doc("Version")
                version.ref_doctype = "Asset"
                version.docname = i.asset
                version.data = frappe.as_json({"changed": [["cost_center", old, new]]})
                version.flags.ignore_links = True
                version.flags.ignore_permissions = True
                version.insert()


###############################################################################
# This class use to override class LeavePolicyAssignment
# Request:
#
# Response:
#
# Taks:
#
# History
# 06-11-2024  Pisethpong    Created
###############################################################################
class CustomLeavePolicyAssignment(LeavePolicyAssignment):
    def grant_leave_alloc_for_employee(self):
        if self.leaves_allocated:
            frappe.throw(
                _("Leave already have been assigned for this Leave Policy Assignment")
            )
        else:
            leave_allocations = {}
            leave_type_details = get_leave_type_details()

            leave_policy = frappe.get_doc("Leave Policy", self.leave_policy)
            date_of_joining = frappe.db.get_value(
                "Employee", self.employee, "date_of_joining"
            )

            for leave_policy_detail in leave_policy.leave_policy_details:
                leave_details = leave_type_details.get(leave_policy_detail.leave_type)

                if not leave_details.is_lwp:
                    leave_allocation, new_leaves_allocated = (
                        self.create_leave_allocation(
                            leave_policy_detail.annual_allocation,
                            leave_details,
                            date_of_joining,
                        )
                    )
                    # validate total leaves allocation == 0
                    if new_leaves_allocated > 0:
                        leave_allocations[leave_details.name] = {
                            "name": leave_allocation,
                            "leaves": new_leaves_allocated,
                        }

            self.db_set("leaves_allocated", 1)
            return leave_allocations

    def create_leave_allocation(
        self, annual_allocation, leave_details, date_of_joining
    ):
        # Creates leave allocation for the given employee in the provided leave period
        carry_forward = self.carry_forward
        if self.carry_forward and not leave_details.is_carry_forward:
            carry_forward = 0

        new_leaves_allocated = self.get_new_leaves(
            annual_allocation, leave_details, date_of_joining
        )

        # validate total leaves allocation == 0
        if new_leaves_allocated <= 0:
            return None, new_leaves_allocated

        allocation = frappe.get_doc(
            dict(
                doctype="Leave Allocation",
                employee=self.employee,
                leave_type=leave_details.name,
                from_date=self.effective_from,
                to_date=self.effective_to,
                new_leaves_allocated=new_leaves_allocated,
                leave_period=(
                    self.leave_period
                    if self.assignment_based_on == "Leave Policy"
                    else ""
                ),
                leave_policy_assignment=self.name,
                leave_policy=self.leave_policy,
                carry_forward=carry_forward,
            )
        )
        allocation.save(ignore_permissions=True)
        allocation.submit()
        return allocation.name, new_leaves_allocated


### END Cass ###


###############################################################################
# on_submit_payment_entry
###############################################################################
# This function is used to hook payment entry on submit event
# Request:
#
# Response:
#
# Taks:
#
# History
# 06-11-2024  CHHAY Sokuon    Created
###############################################################################
def on_submit_payment_entry(doc, _):
    # frappe.throw("Submit payment entry...")
    if doc.custom_batch_payment_request:
        frappe.db.set_value(
            CONST.DOCTYPE_BATCH_PAYMENT_REQUEST,
            doc.custom_batch_payment_request,
            {"status": CONST.STATUS_PAID},
        )
        frappe.db.commit()


# END Function on_submit_payment_entry


###############################################################################
# on_validate_payment_entry
###############################################################################
# This function is used to hook payment entry on validate event
# Request:
#
# Response:
#
# Taks:
#
# History
# 06-11-2024  CHHAY Sokuon    Created
###############################################################################
def on_validate_payment_entry(doc, _):
    if doc.custom_batch_payment_request and frappe.db.exists(
        doc.doctype,
        {
            "custom_batch_payment_request": doc.custom_batch_payment_request,
            "name": ["!=", doc.name],
        },
    ):
        frappe.throw(
            f"The payment request id {doc.custom_batch_payment_request} \
        is already linked with another payment entry."
        )


# END Function on_validate_payment_entry


class CustomPromotionalScheme(PromotionalScheme):
    def update_pricing_rules(self, pricing_rules):
        rules = {}
        count = 0
        names = []
        for rule in pricing_rules:
            names.append(rule.name)
            rules[rule.get("promotional_scheme_id")] = names

        docs = get_pricing_rules(self, rules)

        for doc in docs:
            doc.run_method("validate")
            doc.custom_valid_from_time = self.custom_valid_from_time
            doc.custom_valid_upto_time = self.custom_valid_upto_time
            if doc.get("__islocal"):
                count += 1
                doc.insert()
            else:
                doc.save()
                frappe.msgprint(_("Pricing Rule {0} is updated").format(doc.name))

        if count:
            frappe.msgprint(_("New {0} pricing rules are created").format(count))

    def before_save(self):
        before_save_pricing_rule(self, None)

def before_save_pricing_rule(self, method):
    if (
        not self.custom_valid_from_time
        or not self.custom_valid_upto_time
        or format_time(self.custom_valid_from_time)
        == format_time(self.custom_valid_upto_time)
    ):
        self.custom_valid_from_time = None
        self.custom_valid_upto_time = None

def format_time(time):
    if not time:
        return
    from frappe.utils import format_time, get_time

    time_obj = get_time(time)
    return format_time(time_obj, format_string="HH:mm:ss")


def before_save_bank_account(self, method):
    if self.custom_mapping_bakong:
        try:
            api_url = CONST.BASE_BAKONG_URL + CONST.check_acc_endpoint
            account_id = self.custom_bakong_account_no
            payload = {"accountId": account_id}
            response = requests.post(api_url, headers=CONST.headers, json=payload)
            response.raise_for_status()
            data = response.json().get("data", {})

            if (
                response.json().get("responseMessage") == "Account ID exists"
                and data.get("accountStatus") == "ACTIVATED"
                and data.get("canReceive")
                and not data.get("frozen")
                and data.get("kycStatus") == "FULL_KYC"
            ):

                account_status = "valid"

            else:
                frappe.throw(
                    title="Error",
                    msg=_("Invalid Bakong Bank Account."),
                )
        except requests.exceptions.RequestException as e:
            frappe.throw(
                title="Connection Error",
                msg=_(
                    "Failed to connect to the Bakong API. Please check your internet connection or contact support."
                ),
            )


class CustomAsset(Asset):
    def make_asset_movement(self):
        reference_doctype = (
            "Purchase Receipt" if self.purchase_receipt else "Purchase Invoice"
        )
        reference_docname = self.purchase_receipt or self.purchase_invoice
        transaction_date = getdate(self.purchase_date)
        if reference_docname:
            posting_date, posting_time = frappe.db.get_value(
                reference_doctype, reference_docname, ["posting_date", "posting_time"]
            )
            transaction_date = get_datetime(f"{posting_date} {posting_time}")
        assets = [
            {
                "asset": self.name,
                "asset_name": self.asset_name,
                "target_location": self.location,
                "to_employee": self.custodian,
                "custom_to_cost_center": self.cost_center,
            }
        ]
        asset_movement = frappe.get_doc(
            {
                "doctype": "Asset Movement",
                "assets": assets,
                "purpose": "Receipt",
                "company": self.company,
                "transaction_date": transaction_date,
                "reference_doctype": reference_doctype,
                "reference_name": reference_docname,
            }
        ).insert()
        asset_movement.submit()

MONTHS_ORDER = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
def print_as_json(data):
    json_str = json.dumps(data, indent=4)  # Convert to formatted JSON string
    colored_json = re.sub(r'\"(.*?)\"(?=\:)', r'\033[32m"\1"\033[0m', json_str)  # Colorize keys
    print(colored_json)

def before_save_sale_person(doc, method):
    print(doc.target_team)
    validate_target_group_data(doc)

def validate_target_group_data(doc):
    target_team_monthly = doc.target_team_monthly
    datum_list = [{
        "name": datum.name,
        "target_group": datum.target_group,
        "months": datum.months,
        "target_qty": datum.target_qty,
        "target__amount": datum.target__amount,
        "fiscal_year": datum.fiscal_year,
        "parent": datum.parent
    } for datum in target_team_monthly]

    target_group_data = defaultdict(lambda: defaultdict(set))

    for target_monthly in datum_list:
        if target_monthly["parent"] == doc.name:
            group = target_monthly["target_group"]
            year = target_monthly["fiscal_year"]
            target_group_data[group][year].add(target_monthly["months"])
    
    for group, years in target_group_data.items():
        for year, months in years.items():
            if set(months) != set(MONTHS_ORDER):  # Ensure all 12 months are present
                frappe.throw("Each target group must have exactly 12 months from January to December and belong to the same fiscal year.")
                return False

    auto_create_monthly_distribution_sp(doc, datum_list)
    return True

def auto_create_monthly_distribution_sp(doc, datum_list):
    """Auto-generate monthly distribution for target groups."""
    grouped_data, total_target_qty_per_group, total_target_amount_per_group = defaultdict(lambda: defaultdict(list)), defaultdict(lambda: defaultdict(int)), defaultdict(lambda: defaultdict(int))
    percentage_allocation = []
    for target_monthly in datum_list:
        group = target_monthly["target_group"]
        year = target_monthly["fiscal_year"]
        grouped_data[group][year].append(target_monthly)
        total_target_qty_per_group[group][year] += target_monthly["target_qty"] or 0
        total_target_amount_per_group[group][year] += target_monthly["target__amount"] or 0

    for group, years in grouped_data.items():
        for year, data in years.items():
            data.sort(key=lambda x: MONTHS_ORDER.index(x["months"]))
            total_qty = total_target_qty_per_group[group][year]
            total_amount = total_target_amount_per_group[group][year]
            
            distribution_type = "Monthly" if doc.distribution_type == "By Month" else "Year"
            monthly_distribution_name = f"{doc.name} {distribution_type} {group} {year}"
            
            for entry in data:
                percentage_allocation.append({
                    "parent": doc.name,
                    "target_group": group,
                    "month": entry["months"],
                    "fiscal_year": year,
                    "target_qty": entry["target_qty"],
                    "target__amount": entry["target__amount"],
                    "percentage_allocation": ((entry["target_qty"] or 0) / total_qty * 100) if total_qty else 0,
                    "percentage_allocation_amount": ((entry["target__amount"] or 0) / total_amount * 100) if total_amount else 0,
                    "monthly_distribution_name": monthly_distribution_name
                })
    create_monthly_distribution(doc, percentage_allocation)
    create_target_doc(doc, percentage_allocation)

def create_monthly_distribution(doc, percentage_allocation):
    current_user = frappe.session.user
    now_datetime = now()
    monthly_distributions_name = set()
    for allocation in percentage_allocation:
        monthly_distribution_name = allocation["monthly_distribution_name"]
        monthly_distributions_name.add(monthly_distribution_name)

    for monthly_distribution_name in monthly_distributions_name:
        if not frappe.db.exists("Monthly Distribution", {"name": monthly_distribution_name}):
            frappe.db.sql("""
                INSERT INTO `tabMonthly Distribution`(
                    `name`, `distribution_id`, `owner`, `creation`, `modified`
                ) VALUES (%s, %s, %s, %s, %s)
            """, (monthly_distribution_name, monthly_distribution_name, current_user, now_datetime, now_datetime))
            frappe.db.commit()

        create_monthly_distribution_percentage(percentage_allocation, monthly_distribution_name)

def create_monthly_distribution_percentage(percentage_allocation, monthly_distribution_name):
    monthly_distribution = frappe.get_doc("Monthly Distribution", monthly_distribution_name)
    filtered_allocations = [
        allocation for allocation in percentage_allocation
        if allocation["monthly_distribution_name"] == monthly_distribution_name
    ]
    for idx, allocation in enumerate(filtered_allocations, start=1):
        month, percentage,percentage_amount = allocation["month"], allocation["percentage_allocation"],allocation["percentage_allocation_amount"]
        existing_record = next((record for record in monthly_distribution.percentages if record.month == month), None)
        if existing_record:
            existing_record.percentage_allocation = percentage
            existing_record.percentage_allocation_amount = percentage_amount
        else:
            monthly_distribution.append("percentages", {
                "idx": idx,
                "month": month,
                "percentage_allocation": percentage,
                "percentage_allocation_amount": percentage_amount,
            })
    monthly_distribution.save()

def create_target_doc(doc, percentage_allocation):
    data_summary = defaultdict(lambda: {"total_target_qty": 0, "total_target_amount": 0, "monthly_distribution_name": None})
    for entry in percentage_allocation:
        key = (entry["target_group"], entry["fiscal_year"])
        data_summary[key]["total_target_qty"] += (entry.get("target_qty") or 0)
        data_summary[key]["total_target_amount"] += (entry.get("target__amount") or 0)
        data_summary[key]["monthly_distribution_name"] = entry["monthly_distribution_name"]

    summarized_data = [
        {"target_group": k[0], "fiscal_year": k[1], **v} 
        for k, v in data_summary.items()
    ]
    for record in summarized_data:
        existing_row = next(
            (row for row in doc.get("target_team", []) 
             if row.item_group == record['target_group'] and row.fiscal_year == record['fiscal_year']), 
            None
        )
        if existing_row:
            existing_row.target_qty = record['total_target_qty']
            existing_row.target__amount = record['total_target_amount']
            existing_row.target_distribution = record['monthly_distribution_name']
        else:
            doc.append('target_team', {
                "item_group": record['target_group'],
                "fiscal_year": record['fiscal_year'], 
                "target_qty": record['total_target_qty'],
                "target__amount": record['total_target_amount'],
                "target_distribution": record['monthly_distribution_name'],
            })

def before_insert_monthly_distribution(doc, method):
    auto_set_percentage_allocation_amount(doc, method)
    
def auto_set_percentage_allocation_amount(doc, method):
    for distribution in doc.percentages:
        distribution.percentage_allocation_amount = 8.333333333333334