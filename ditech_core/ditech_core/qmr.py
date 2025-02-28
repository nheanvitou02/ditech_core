import frappe
import json
from frappe import _
from frappe.model.db_query import DatabaseQuery
from frappe.utils import cint, flt

doctype_item_group = "Item Group"


@frappe.whitelist()
def get_data(
    item_group=None,
    cache_items=None,
    start=0,
    sort_by="actual_qty",
    sort_order="desc",
):
    """Return data to render the item dashboard"""
    if item_group:
        warehouse = None
        pos_profile = get_pos_profile()
        if pos_profile:
            warehouse = pos_profile["warehouse"]

        filters = []
        if warehouse:
            filters.append(["warehouse", "=", warehouse])
        if item_group:
            lft, rgt = frappe.db.get_value("Item Group", item_group, ["lft", "rgt"])
            items = frappe.db.sql_list(
                """
                select i.name from `tabItem` i
                where exists(select name from `tabItem Group`
                    where name=i.item_group and lft >=%s and rgt<=%s)
            """,
                (lft, rgt),
            )
            filters.append(["item_code", "in", items])
        try:
            # check if user has any restrictions based on user permissions on warehouse
            if DatabaseQuery(
                "Warehouse", user=frappe.session.user
            ).build_match_conditions():
                filters.append(
                    ["warehouse", "in", [w.name for w in frappe.get_list("Warehouse")]]
                )
        except frappe.PermissionError:
            # user does not have access on warehouse
            return []

        items = frappe.db.get_all(
            "Bin",
            fields=[
                "item_code",
                "warehouse",
                "projected_qty",
                "reserved_qty",
                "reserved_qty_for_production",
                "reserved_qty_for_sub_contract",
                "actual_qty",
                "valuation_rate",
            ],
            or_filters={
                "projected_qty": ["!=", 0],
                "reserved_qty": ["!=", 0],
                "reserved_qty_for_production": ["!=", 0],
                "reserved_qty_for_sub_contract": ["!=", 0],
                "actual_qty": ["!=", 0],
            },
            filters=filters,
            order_by=sort_by + " " + sort_order,
            limit_start=start,
            limit_page_length=21,
        )

        precision = cint(
            frappe.db.get_single_value("System Settings", "float_precision")
        )
        if cache_items:
            cache_items = json.loads(cache_items)

        for item in items:
            total_actual_qty = 0
            if warehouse:
                total_aq = frappe.db.sql(
                    f"""SELECT
                            SUM(actual_qty) AS total_actual_qty
                        FROM
                            tabBin tb
                        JOIN tabWarehouse tw ON
                            tw.name = tb.warehouse
                        WHERE
                            tw.is_rejected_warehouse = 0
                            AND tb.item_code = '{item.item_code}'
                            AND tb.warehouse != '{warehouse}'""",
                    as_dict=1,
                )

                total_actual_qty = (
                    total_aq[0]["total_actual_qty"]
                    if total_aq[0]["total_actual_qty"]
                    else 0
                )
            get_item = frappe.db.get_value(
                "Item", item.item_code, ["image", "stock_uom"], as_dict=1
            )
            qty = 0
            for i in cache_items:
                if i["item_code"] == item.item_code:
                    qty = i["qty"]

            item.update(
                {
                    "item_name": frappe.get_cached_value(
                        "Item", item.item_code, "item_name"
                    ),
                    "image": get_item.image,
                    "qty": qty,
                    "stock_uom": get_item.stock_uom,
                    "disable_quick_entry": frappe.get_cached_value(
                        "Item", item.item_code, "has_batch_no"
                    )
                    or frappe.get_cached_value("Item", item.item_code, "has_serial_no"),
                    "projected_qty": flt(item.projected_qty, precision),
                    "reserved_qty": flt(item.reserved_qty, precision),
                    "reserved_qty_for_production": flt(
                        item.reserved_qty_for_production, precision
                    ),
                    "reserved_qty_for_sub_contract": flt(
                        item.reserved_qty_for_sub_contract, precision
                    ),
                    "actual_qty": flt(item.actual_qty, precision),
                    "total_actual_qty": flt(
                        (item.actual_qty + total_actual_qty),
                        precision,
                    ),
                }
            )

        return items
    return []

@frappe.whitelist()
def get_pos_profile():
    user = frappe.session.user
    if user != "Administrator":
        pos_profile = frappe.db.sql(
            f"""SELECT
                    tpp.warehouse,
                    tpp.cost_center,
                    tpp.name
                FROM
                    `tabPOS Profile` tpp
                JOIN `tabPOS Profile User` tppu ON
                    tppu.parent = tpp.name
                WHERE tppu.`user` = '{user}'
                AND tppu.`default` = 1""",
            as_dict=1,
        )
        if len(pos_profile) == 0:
            frappe.throw(_("Not allowed!"))
        else:
            return pos_profile[0]
    return


def get_pos_item_group(name):
    return frappe.db.sql(
        f"""SELECT
                tpig.item_group,
                tig.is_group
            FROM
                `tabPOS Item Group` tpig 
            JOIN `tabItem Group` tig ON tig.name = tpig.item_group 
            WHERE
                tpig.parent = '{name}' AND tig.custom_is_hide_qmr = 0""",
        as_dict=1,
    )


@frappe.whitelist()
def get_item_group():
    all_item_group = frappe.db.get_all(
        doctype_item_group,
        pluck="item_group_name",
        filters={"is_group": 0, "custom_is_hide_qmr": 0},
    )
    return all_item_group


@frappe.whitelist()
def make_material_request(**args):
    from frappe.model.workflow import apply_workflow, get_workflow_name
    pos_profile = get_pos_profile()
    items = json.loads(args["items"])
    mr = frappe.new_doc("Material Request")
    mr.material_request_type = args["material_request_type"]
    mr.schedule_date = args["schedule_date"]
    warehouse = args["set_warehouse"] if args["set_warehouse"] else pos_profile.warehouse
    cost_center = args["cost_center"] if args["cost_center"] else pos_profile.cost_center
        
    if args["material_request_type"] == "Material Transfer":
        mr.set_from_warehouse = args["set_from_warehouse"]
        mr.set_warehouse = warehouse
    else:
        mr.set_warehouse = warehouse
    for item in items:
        mr.append(
            "items",
            {
                "item_code": item["item_code"],
                "qty": item["qty"],
                "uom": item["stock_uom"],
                "schedule_date": args["schedule_date"],
                "warehouse": warehouse,
                "cost_center": cost_center,
            },
        )
    mr.insert()
    workflow = get_workflow_name(mr.doctype)
    if not workflow:
        return

    workflow_doc = frappe.get_doc("Workflow", workflow)
    for transition in workflow_doc.transitions:
        if transition.state == "Save":
            apply_workflow(mr, transition.action)
            break
    return "Successfully!"
