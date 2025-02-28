import frappe
import json
import copy
from frappe import _
from erpnext.accounts.doctype.pricing_rule.pricing_rule import (
	set_transaction_type,
	get_pricing_rule_details,
	remove_pricing_rule_for_item,
	update_args_for_pricing_rule,
	apply_price_discount_rule,
	update_pricing_rule_uom
)
from datetime import datetime

@frappe.whitelist()
def make_asset_movement(assets, purpose=None):
	import json

	if isinstance(assets, str):
		assets = json.loads(assets)

	if len(assets) == 0:
		frappe.throw(_("Atleast one asset has to be selected."))

	asset_movement = frappe.new_doc("Asset Movement")
	asset_movement.quantity = len(assets)
	for asset in assets:
		asset = frappe.get_doc("Asset", asset.get("name"))
		asset_movement.company = asset.get("company")
		asset_movement.append(
			"assets",
			{
				"asset": asset.get("name"),
				"source_location": asset.get("location"),
				"from_employee": asset.get("custodian"),
				"asset_name": asset.get("asset_name"),
				"custom_from_cost_center": asset.get("cost_center"),
			},
		)

	if asset_movement.get("assets"):
		return asset_movement.as_dict()
	
@frappe.whitelist()
def apply_pricing_rule(args, doc=None):
	"""
	args = {
			"items": [{"doctype": "", "name": "", "item_code": "", "brand": "", "item_group": ""}, ...],
			"customer": "something",
			"customer_group": "something",
			"territory": "something",
			"supplier": "something",
			"supplier_group": "something",
			"currency": "something",
			"conversion_rate": "something",
			"price_list": "something",
			"plc_conversion_rate": "something",
			"company": "something",
			"transaction_date": "something",
			"campaign": "something",
			"sales_partner": "something",
			"ignore_pricing_rule": "something"
	}
	"""

	if isinstance(args, str):
		args = json.loads(args)

	args = frappe._dict(args)

	if not args.transaction_type:
		set_transaction_type(args)

	# list of dictionaries
	out = []

	if args.get("doctype") == "Material Request":
		return out

	item_list = args.get("items")
	args.pop("items")

	item_code_list = tuple(item.get("item_code") for item in item_list)
	query_items = frappe.get_all(
		"Item",
		fields=["item_code", "has_serial_no"],
		filters=[["item_code", "in", item_code_list]],
		as_list=1,
	)
	serialized_items = dict()
	for item_code, val in query_items:
		serialized_items.setdefault(item_code, val)

	for item in item_list:
		args_copy = copy.deepcopy(args)
		args_copy.update(item)
		data = get_pricing_rule_for_item(args_copy, doc=doc)
		out.append(data)

	return out

def get_pricing_rule_for_item(args, doc=None, for_validate=False):
	from erpnext.accounts.doctype.pricing_rule.utils import (
		get_applied_pricing_rules,
		get_pricing_rule_items,
		get_pricing_rules,
		get_product_discount_rule,
	)

	if isinstance(doc, str):
		doc = json.loads(doc)

	if doc:
		doc = frappe.get_doc(doc)

	if args.get("is_free_item") or args.get("parenttype") == "Material Request":
		return {}

	item_details = frappe._dict(
		{
			"doctype": args.doctype,
			"has_margin": False,
			"name": args.name,
			"free_item_data": [],
			"parent": args.parent,
			"parenttype": args.parenttype,
			"child_docname": args.get("child_docname"),
			"discount_percentage": 0.0,
			"discount_amount": 0,
		}
	)

	if args.ignore_pricing_rule or not args.item_code:
		if frappe.db.exists(args.doctype, args.name) and args.get("pricing_rules"):
			item_details = remove_pricing_rule_for_item(
				args.get("pricing_rules"),
				item_details,
				item_code=args.get("item_code"),
				rate=args.get("price_list_rate"),
			)
		return item_details

	update_args_for_pricing_rule(args)

	pricing_rules = (
		get_applied_pricing_rules(args.get("pricing_rules"))
		if for_validate and args.get("pricing_rules")
		else get_pricing_rules(args, doc)
	)

	if pricing_rules:
		rules = []

		for pricing_rule in pricing_rules:
			if not pricing_rule:
				continue

			check_pricing_rule = pricing_rules_not_on_time(pricing_rule.name)
			if check_pricing_rule is True:
				continue

			if isinstance(pricing_rule, str):
				pricing_rule = frappe.get_cached_doc("Pricing Rule", pricing_rule)
				update_pricing_rule_uom(pricing_rule, args)
				fetch_other_item = True if pricing_rule.apply_rule_on_other else False
				pricing_rule.apply_rule_on_other_items = (
					get_pricing_rule_items(pricing_rule, other_items=fetch_other_item) or []
				)

			if pricing_rule.coupon_code_based == 1:
				if not args.coupon_code:
					return item_details

				coupon_code = frappe.db.get_value(
					doctype="Coupon Code", filters={"pricing_rule": pricing_rule.name}, fieldname="name"
				)
				if args.coupon_code != coupon_code:
					continue

			if pricing_rule.get("suggestion"):
				continue

			item_details.validate_applied_rule = pricing_rule.get("validate_applied_rule", 0)
			item_details.price_or_product_discount = pricing_rule.get("price_or_product_discount")

			rules.append(get_pricing_rule_details(args, pricing_rule))

			if pricing_rule.mixed_conditions or pricing_rule.apply_rule_on_other:
				item_details.update(
					{
						"price_or_product_discount": pricing_rule.price_or_product_discount,
						"apply_rule_on": (
							frappe.scrub(pricing_rule.apply_rule_on_other)
							if pricing_rule.apply_rule_on_other
							else frappe.scrub(pricing_rule.get("apply_on"))
						),
					}
				)

				if pricing_rule.apply_rule_on_other_items:
					item_details["apply_rule_on_other_items"] = json.dumps(
						pricing_rule.apply_rule_on_other_items
					)

			if not pricing_rule.validate_applied_rule:
				if pricing_rule.price_or_product_discount == "Price":
					apply_price_discount_rule(pricing_rule, item_details, args)
				else:
					get_product_discount_rule(pricing_rule, item_details, args, doc)

		if not item_details.get("has_margin"):
			item_details.margin_type = None
			item_details.margin_rate_or_amount = 0.0

		item_details.has_pricing_rule = 1

		item_details.pricing_rules = frappe.as_json([d.pricing_rule for d in rules])

		if not doc:
			return item_details

	elif args.get("pricing_rules"):
		item_details = remove_pricing_rule_for_item(
			args.get("pricing_rules"),
			item_details,
			item_code=args.get("item_code"),
			rate=args.get("price_list_rate"),
		)

	return item_details


def pricing_rules_not_on_time(name):
	if not frappe.db.exists("Pricing Rule", {'name': name}):
		return False
	
	pricing_rule = frappe.get_doc("Pricing Rule", name)

	from_time = check_time_format(str(pricing_rule.custom_valid_from_time), time_format="%H:%M:%S")
	upto_time = check_time_format(str(pricing_rule.custom_valid_upto_time), time_format="%H:%M:%S")
	current_time = datetime.now().time()

	if from_time is False or upto_time is False:
		return False
	
	custom_valid_from_time = datetime.strptime(str(pricing_rule.custom_valid_from_time), "%H:%M:%S").time()
	custom_valid_upto_time = datetime.strptime(str(pricing_rule.custom_valid_upto_time), "%H:%M:%S").time()

	# Check if current time is within the range
	if custom_valid_from_time <= current_time <= custom_valid_upto_time:
		return False
	else:
		return True
	
def check_time_format(time_string, time_format):
    try:
        datetime.strptime(time_string, time_format)
        return True  # Valid format
    except ValueError:
        return False  # Invalid format
