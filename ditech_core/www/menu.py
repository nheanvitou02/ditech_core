import frappe
import frappe.utils
from frappe import _
import json
from frappe.utils import cint
from ditech_core.ditech_core.utils import (
    get_currency_exchange,
)
docype_menu_qr_code = "Menu QR Code"
docype_menu_qr_code_category = "Menu QR Code Category"
docype_menu_category = "Menu Category"
docype_website_slideshow_item = "Website Slideshow Item"
docype_infomation = "Menu Information"
doctype_pro_profile = "POS Profile"
doctype_customer = "Customer"

def get_context(context):
    key = frappe.request.args.get("key")
    pro_profile = frappe.request.args.get("pro")
    context["pos_profile"] = ""
    if pro_profile:
        context["pos_profile"] = get_pos_profile(pro_profile)
        
    menu = get_menu_qr(key)
    context.no_cache = 1
    context.for_test = "menu.html"
    context["not_found"] = menu["not_found"]
    if not menu["not_found"]:
        context["title"] = menu["title"] or _("Menu")
        context["categories"] = menu["categories"]
        context["slideshow"] = menu["slideshow"]
        context["primary_color"] = menu["primary_color"]
        context["info"] = menu["info"]
        context["profile"] = menu["profile"]
        context["cover"] = menu["cover"]
        context["company_name"] = menu["company_name"]
        context["description"] = menu["description"]
        context["logo"] = (
            menu["logo"]
            or frappe.get_website_settings("app_logo")
            or frappe.get_hooks("app_logo_url")[-1]
        )
    return context


icons = {
    "facebook": """<svg width="28" height="28" viewBox="126.445 2.281 589 589" xmlns="http://www.w3.org/2000/svg"><circle cx="420.945" cy="296.781" r="294.5" fill="#3c5a9a"/><path d="M516.704 92.677h-65.239c-38.715 0-81.777 16.283-81.777 72.402.189 19.554 0 38.281 0 59.357H324.9v71.271h46.174v205.177h84.847V294.353h56.002l5.067-70.117h-62.531s.14-31.191 0-40.249c0-22.177 23.076-20.907 24.464-20.907 10.981 0 32.332.032 37.813 0V92.677h-.032z" fill="#ffffff"/></svg>""",
    "telegram": """<svg width="28" height="28" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><circle fill="#59AAE7" cx="256" cy="256" r="256"/><path fill="#3D9AE3" d="M256,0c-11.317,0-22.461,0.744-33.391,2.167C348.216,18.53,445.217,125.933,445.217,256 s-97.002,237.47-222.609,253.833C233.539,511.256,244.683,512,256,512c141.385,0,256-114.616,256-256S397.385,0,256,0z"/><path fill="#FCFCFC" d="M164.689,311.141L82.127,269.86c-2.263-1.132-2.285-4.353-0.038-5.516L395.75,102.105 c2.304-1.192,4.964,0.811,4.456,3.355l-54.004,270.017c-0.385,1.927-2.446,3.011-4.253,2.237l-73.393-31.453 c-0.879-0.377-1.884-0.326-2.721,0.139l-94.839,52.688c-2.062,1.145-4.597-0.345-4.597-2.705v-82.474 C166.4,312.736,165.738,311.665,164.689,311.141z"/><path fill="#D8D7DA" d="M200.31,338.967l-0.513-82.428c-0.003-0.528,0.27-1.018,0.72-1.293l133.899-81.798 c1.518-0.927,3.106,1.083,1.852,2.345l-101.9,102.624c-0.112,0.114-0.207,0.244-0.278,0.387l-17.43,34.858l-13.509,25.988 C202.426,341.045,200.32,340.538,200.31,338.967z"/></svg>""",
    "tiktok": """<svg width="28" height="28" viewBox="0 0 250 250" xmlns="http://www.w3.org/2000/svg"><g clip-rule="evenodd" fill-rule="evenodd"><path d="M25 0h200c13.808 0 25 11.192 25 25v200c0 13.808-11.192 25-25 25H25c-13.808 0-25-11.192-25-25V25C0 11.192 11.192 0 25 0z" fill="#010101"/><path d="M156.98 230c7.607 0 13.774-6.117 13.774-13.662s-6.167-13.663-13.774-13.663h-2.075c7.607 0 13.774 6.118 13.774 13.663S162.512 230 154.905 230z" fill="#ee1d51"/><path d="M154.717 202.675h-2.075c-7.607 0-13.775 6.118-13.775 13.663S145.035 230 152.642 230h2.075c-7.608 0-13.775-6.117-13.775-13.662s6.167-13.663 13.775-13.663z" fill="#66c8cf"/><ellipse cx="154.811" cy="216.338" fill="#010101" rx="6.699" ry="6.643"/><path d="M50 196.5v6.925h8.112v26.388h8.115v-26.201h6.603l2.264-7.112zm66.415 0v6.925h8.112v26.388h8.115v-26.201h6.603l2.264-7.112zm-39.81 3.93c0-2.17 1.771-3.93 3.959-3.93 2.19 0 3.963 1.76 3.963 3.93s-1.772 3.93-3.963 3.93c-2.188-.001-3.959-1.76-3.959-3.93zm0 6.738h7.922v22.645h-7.922zM87.924 196.5v33.313h7.925v-8.608l2.453-2.248L106.037 230h8.49l-11.133-16.095 10-9.733h-9.622l-7.923 7.86V196.5zm85.47 0v33.313h7.926v-8.608l2.452-2.248L191.509 230H200l-11.133-16.095 10-9.733h-9.622l-7.925 7.86V196.5z" fill="#ffffff"/><path d="M161.167 81.186c10.944 7.819 24.352 12.42 38.832 12.42V65.755a39.26 39.26 0 0 1-8.155-.853v21.923c-14.479 0-27.885-4.601-38.832-12.42v56.835c0 28.432-23.06 51.479-51.505 51.479-10.613 0-20.478-3.207-28.673-8.707C82.187 183.57 95.23 189.5 109.66 189.5c28.447 0 51.508-23.047 51.508-51.48V81.186zm10.06-28.098c-5.593-6.107-9.265-14-10.06-22.726V26.78h-7.728c1.945 11.09 8.58 20.565 17.788 26.308zm-80.402 99.107a23.445 23.445 0 0 1-4.806-14.256c0-13.004 10.548-23.547 23.561-23.547a23.6 23.6 0 0 1 7.147 1.103V87.022a51.97 51.97 0 0 0-8.152-.469v22.162a23.619 23.619 0 0 0-7.15-1.103c-13.013 0-23.56 10.543-23.56 23.548 0 9.195 5.272 17.157 12.96 21.035z" fill="#ee1d52"/><path d="M153.012 74.405c10.947 7.819 24.353 12.42 38.832 12.42V64.902c-8.082-1.72-15.237-5.942-20.617-11.814-9.208-5.743-15.843-15.218-17.788-26.308H133.14v111.239c-.046 12.968-10.576 23.468-23.561 23.468-7.652 0-14.45-3.645-18.755-9.292-7.688-3.878-12.96-11.84-12.96-21.035 0-13.005 10.547-23.548 23.56-23.548 2.493 0 4.896.388 7.15 1.103V86.553c-27.945.577-50.42 23.399-50.42 51.467 0 14.011 5.597 26.713 14.68 35.993 8.195 5.5 18.06 8.707 28.673 8.707 28.445 0 51.505-23.048 51.505-51.479z" fill="#ffffff"/><path d="M191.844 64.902v-5.928a38.84 38.84 0 0 1-20.617-5.887 38.948 38.948 0 0 0 20.617 11.815zM153.439 26.78a39.524 39.524 0 0 1-.427-3.198V20h-28.028v111.24c-.045 12.967-10.574 23.467-23.56 23.467-3.813 0-7.412-.904-10.6-2.512 4.305 5.647 11.103 9.292 18.755 9.292 12.984 0 23.515-10.5 23.561-23.468V26.78zm-44.864 59.773v-6.311a51.97 51.97 0 0 0-7.067-.479C73.06 79.763 50 102.811 50 131.24c0 17.824 9.063 33.532 22.835 42.772-9.083-9.28-14.68-21.982-14.68-35.993 0-28.067 22.474-50.889 50.42-51.466z" fill="#69c9d0"/><path d="M154.904 230c7.607 0 13.775-6.117 13.775-13.662s-6.168-13.663-13.775-13.663h-.188c-7.607 0-13.774 6.118-13.774 13.663S147.109 230 154.716 230zm-6.792-13.662c0-3.67 3-6.643 6.7-6.643 3.697 0 6.697 2.973 6.697 6.643s-3 6.645-6.697 6.645c-3.7-.001-6.7-2.975-6.7-6.645z" fill="#ffffff"/></g></svg>""",
}


@frappe.whitelist(allow_guest=1)
def get_pos_profile(pro_profile):
    if frappe.db.exists(doctype_pro_profile, pro_profile):
        pos_profile = frappe.db.get_value(doctype_pro_profile, pro_profile, ["selling_price_list", "currency", "custom_second_currency", "name"], as_dict=1)
        pos_profile.symbol = get_symbole(pos_profile.currency)
        pos_profile.second_symbol = get_symbole(pos_profile.custom_second_currency) or ""
        pos_profile.custom_second_currency = pos_profile.custom_second_currency or ''
        pos_profile.exchange_rate = 1
        if pos_profile.custom_second_currency:
            pos_profile.exchange_rate = get_currency_exchange(
                pos_profile.currency, pos_profile.custom_second_currency
        )
        return pos_profile
    return

def get_symbole(currency):
    return frappe.db.get_value("Currency", currency, "symbol")

@frappe.whitelist(allow_guest=1)
def check_customer(customer_name):
    return bool(frappe.db.exists(doctype_customer, customer_name))

@frappe.whitelist(allow_guest=1)
def get_menu_qr(key):
    exist_menu = frappe.db.exists(docype_menu_qr_code, {"key": key})
    if exist_menu:
        categories = frappe.db.get_all(
            docype_menu_qr_code_category,
            pluck="category",
            filters={"parent": exist_menu},
            order_by="idx asc",
        )
        menu = frappe.db.get_value(
            docype_menu_qr_code,
            exist_menu,
            [
                "qr_name",
                "slideshow",
                "website_logo",
                "primary_color",
                "profile",
                "cover",
                "description",
                "company_name",
            ],
            as_dict=1,
        )
        slideshow = []
        if menu.slideshow:
            slideshow = frappe.db.get_all(
                docype_website_slideshow_item,
                fields=["image", "heading", "description", "url"],
                filters={"parent": menu.slideshow},
            )
        info = []
        infos = frappe.db.get_all(
            docype_infomation,
            fields=["*"],
            filters={"parent": exist_menu},
            order_by="idx asc",
        )
        for i in infos:
            if i["link"].startswith("https://www.facebook.com"):
                info.append(
                    f"""
                        <a class="pl-4" target="_blank" href="{i["link"]}">{icons["facebook"]}</a>
                                """
                )
            elif i["link"].startswith("https://www.tiktok.com"):
                info.append(
                    f"""
                        <a class="pl-4" target="_blank" href="{i["link"]}">{icons["tiktok"]}</a>
                                """
                )
            elif i["link"].startswith("https://t.me"):
                info.append(
                    f"""
                        <a class="pl-4" target="_blank" href="{i["link"]}">{icons["telegram"]}</a>
                                """
                )
            elif i["type"] == "Phone":
                info.append(
                    f"""
                        <div class="flex items-center pl-4"><svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 4h4l2 5l-2.5 1.5a11 11 0 0 0 5 5l1.5 -2.5l5 2v4a2 2 0 0 1 -2 2a16 16 0 0 1 -15 -15a2 2 0 0 1 2 -2"></path></svg><a class="pl-1" href="tel:{i["link"]}"> {i["link"]}</a></div>
                    """
                )

        return {
            "categories": frappe.db.get_all(
                docype_menu_category,
                fields=["name", "category_name"],
                filters={"name": ["in", categories]},
            ),
            "not_found": 0,
            "title": menu.qr_name,
            "primary_color": menu.primary_color,
            "slideshow": slideshow,
            "logo": menu.website_logo,
            "info": info,
            "profile": menu.profile,
            "cover": menu.cover,
            "description": menu.description,
            "company_name": menu.company_name,
        }
    return {"not_found": 1}


@frappe.whitelist(allow_guest=1)
def save_customer(customer_name):
    exist_customer = frappe.db.exists(doctype_customer, customer_name)
    if not exist_customer:
        new_customer = frappe.new_doc(doctype_customer)
        new_customer.customer_name = customer_name
        new_customer.save(ignore_permissions=1)
    return customer_name
        
@frappe.whitelist(allow_guest=1)
def get_items(key, query="", cat=[], limit=21, start=0, price_list=None):
    cat = json.loads(cat)
    exist_menu = frappe.db.exists(docype_menu_qr_code, {"key": key})
    result = []
    if exist_menu:
        if not price_list:
            price_list = frappe.db.get_value(
                docype_menu_qr_code, exist_menu, "selling_price_list"
            )
            
        if len(cat) == 0:
            cat = frappe.db.get_all(
                docype_menu_qr_code_category,
                pluck="category",
                filters={"parent": exist_menu},
                order_by="idx asc",
            ) + [exist_menu]
        query_sql = f"""
            SELECT
                tmci.name,
                tmci.item_code,
                tmci.item_name,
                tmci.description,
                tmci.image,
                tmci.uom,
                tmci.show_uom
            FROM
                `tabMenu Category Item` tmci
            WHERE 
                tmci.enable = 1
                AND (tmci.item_code LIKE '%{query}%' OR tmci.item_name LIKE '%{query}%')
        """
        if len(cat) == 1:
            query_sql += f""" AND tmci.parent = '{cat[0]}'"""
        else:
            query_sql += f""" AND tmci.parent IN {tuple(cat)} GROUP BY tmci.item_code"""

        query_sql += f""" LIMIT {limit} OFFSET {start} """
        items = frappe.db.sql(query_sql, as_dict=True)

        if not items:
            return result

        for item in items:
            item_price = frappe.get_all(
                "Item Price",
                fields=["price_list_rate", "currency", "uom", "batch_no"],
                filters={
                    "price_list": price_list,
                    "item_code": item.item_code,
                    "uom": item.uom,
                    "selling": True,
                },
            )

            if not item_price:
                result.append(item)

            for price in item_price:
                result.append(
                    {
                        **item,
                        "price_list_rate": price.get("price_list_rate"),
                        "currency": price.get("currency"),
                        "symbol": get_symbole(price.get("currency")),
                        "uom": price.uom or item.uom,
                    }
                )

    return result

