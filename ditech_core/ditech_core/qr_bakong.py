import frappe
from frappe import _
import json
import requests
import qrcode
import base64
from io import BytesIO
from bakong_khqr import KHQR
from frappe.utils import nowdate, nowtime
from ditech_core import constants as CONST

# Doctypes:
doctype_bakong_developer_token_setting = "Bakong Developer Token Settings"
doctype_pos_profile_user = "POS Profile User"
doctype_pos_profile = "POS Profile"
doctype_company = "Company"
doctype_address = "Address"
doctype_dynamic_link = "Dynamic Link"
doctype_bank_account = "Bank Account"
doctype_bank_transaction = "Bank Transaction"


@frappe.whitelist()
def get_bakong_qr(**kwargs):
    try:
        bank_account = kwargs.get("bank_account")
        cashier = kwargs.get("cashier", None)
        ref_doc = kwargs.get("ref_doc")
        ref_no = kwargs.get("ref_no")
        currency = kwargs.get("currency")
        amount = kwargs.get("amount")

        # Get reference document
        get_ref = frappe.get_doc(ref_doc, ref_no)

        if float(amount) != float(get_ref.grand_total):
            frappe.throw(_("Amount not equal Grand Total"))

        # Bakong Settings
        dev_token = frappe.db.get_single_value(
            doctype_bakong_developer_token_setting, "token"
        )
        get_bank_account = frappe.db.get_value(
            doctype_bank_account,
            {"name": bank_account},
            ["custom_bakong_account", "custom_bakong_account_no"],
            as_dict=True,
        )

        if cashier:
            pos_profile = frappe.db.get_value(
                doctype_pos_profile_user, {"user": cashier}, ["parent"]
            )
            get_pos_profile = frappe.get_doc(doctype_pos_profile, pos_profile)
            address, phone = frappe.get_value(
                doctype_address,
                {"name": get_pos_profile.company_address},
                ["address_line1", "phone"],
            )
            store = get_pos_profile.cost_center
            terminal = pos_profile

        else:
            company = frappe.defaults.get_user_default("company")
            company_address = frappe.get_value(
                doctype_dynamic_link,
                {"link_doctype": "Company", "link_name": company},
                ["parent"],
            )
            address, phone = frappe.get_value(
                doctype_address, {"name": company_address}, ["address_line1", "phone"]
            )
            store, terminal = get_ref.cost_center

        if not address:
            frappe.throw(_("Please enter your address."))
        if not phone:
            frappe.throw(_("Please enter your phone."))
        if not store:
            frappe.throw(_("Cost Center isn't empty."))

        # Check Bakong account
        account_status = check_bakong_account(get_bank_account.custom_bakong_account_no)
        if account_status == "invalid":
            frappe.throw(_("Invalid Bakong Account"))

        # Initialize KHQR developer token
        khqr = KHQR(dev_token)

        # Generate QR Code
        qr_code = khqr.create_qr(
            bank_account=get_bank_account.custom_bakong_account_no,
            merchant_name=get_bank_account.custom_bakong_account,
            merchant_city=address,
            amount=amount,
            currency=currency,
            store_label=store,
            phone_number=phone,
            bill_number=ref_no,
            terminal_label=terminal,
        )

        # Generate MD5
        md5 = khqr.generate_md5(qr_code)

        # convert qr code to base64
        b64_qr = text_to_qr_base64(qr_code)

        return {"md5": md5, "image": b64_qr}
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"{e}")
        return {"error": str(e)}


@frappe.whitelist()
def check_transaction_payment(md5):
    try:
        # Bakong Settings
        dev_token = frappe.db.get_single_value(
            doctype_bakong_developer_token_setting, "token"
        )

        api_url = CONST.BASE_BAKONG_URL + CONST.check_transaction_by_md5_endpoint
        CONST.headers["Authorization"] = f"Bearer {dev_token}"
        payload = {"md5": md5}
        response = requests.post(api_url, headers=CONST.headers, json=payload)
        response.raise_for_status()
        data = response.json()
        return data
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"{e}")
        return {"error": str(e)}


@frappe.whitelist()
def create_bank_transaction(kwargs):
    try:
        data = kwargs.get("data")
        ref_doc = kwargs.get("ref_doc")
        ref_no = kwargs.get("ref_no")
        md5 = kwargs.get("md5")
        party_type = kwargs.get("party_type")
        party = kwargs.get("party")
        bank_account = kwargs.get("bank_account")

        if isinstance(data, str):
            data = json.loads(data)

        if frappe.db.exists(
            doctype_bank_transaction, {"ref_doc": ref_doc, "ref_no": ref_no, "md5": md5}
        ):
            frappe.local.response["http_status_code"] = 400
            frappe.response["message"] = "Duplicate Bank Transaction"

        transactions = frappe.new_doc(doctype_bank_transaction)
        transactions.date = nowdate()
        transactions.time = nowtime()
        transactions.status = "Settled"
        transactions.bank_account = bank_account
        transactions.custom_bakong_account_no = data.get("toAccountId")
        transactions.bank_party_account_number = data.get("fromAccountId")
        transactions.currency = data.get("currency")
        transactions.transaction_type = "Tranfer to Bakong Account"
        transactions.reference_number = data.get("externalRef")
        transactions.transaction_id = data.get("externalRef")
        transactions.description = data.get("description")
        transactions.deposit = data.get("amount")
        transactions.custom_ref_doc = ref_doc
        transactions.custom_ref_no = ref_no
        transactions.custom_md5 = md5
        transactions.party_type = party_type
        transactions.party = party
        transactions.submit()

        return "Saved Successfully"

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"{e}")
        return {"error": str(e)}


def check_bakong_account(bank_account):
    try:
        api_url = CONST.BASE_BAKONG_URL + CONST.check_acc_endpoint
        account_id = bank_account
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
            return "valid"
        return "invalid"

    except requests.exceptions.RequestException as e:
        frappe.log_error(frappe.get_traceback(), f"{e}")
        return {"error": str(e)}


def text_to_qr_base64(qr_code):
    img = qrcode.make(qr_code)
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    b64 = base64.b64encode(buffer.getvalue())
    return "data:image/png;base64,{0}".format(b64.decode("utf-8"))
