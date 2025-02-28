import frappe
import frappe.utils
from frappe import _
import json
from ditech_core.ditech_core.utils import check_user_service

doctype_pos_profile = "POS Profile"

def get_context(context):
    if frappe.session.user == "Guest":
        frappe.throw(
            _("You need to be logged in to access this page"), frappe.PermissionError
        )
    key = frappe.request.args.get("key")
    open = check_open(key)
    context.no_cache = 1
    context.for_test = "customer_facing_display.html"
    context["not_found"] = open["not_found"]
    if not open["not_found"]:
        context["video"] = open["video"]
        context["image"] = open["image"]
    return context


def check_open(cfd_key):
    opening = check_user_service(frappe.session.user)
    data = {"not_found": 1, "image": ""}
    if len(opening):
        image, video = frappe.db.get_value(doctype_pos_profile, opening[0]["pos_profile"], ["custom_image_cfd", "custom_video_cfd"])
        key = opening[0]["pos_profile"]
        data["not_found"] = cfd_key != key
        data["video"] = video
        data["image"] = image
    return data
