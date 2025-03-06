app_name = "ditech_core"
app_title = "ditech_core"
app_publisher = "tech@ditech.software"
app_description = "DiTech Core Module"
app_email = "tech@ditech.software"
app_license = "cc0-1.0"
# required_apps = []

# Includes in <head>
# ------------------
app_include_js = [
    "/assets/ditech_core/js/chart.js",
]

# include js, css files in header of desk.html
# app_include_css = "/assets/ditech_core/css/ditech_core.css"
# app_include_js = "/assets/ditech_core/js/ditech_core.js"

# include js, css files in header of web template
# web_include_css = "/assets/ditech_core/css/ditech_core.css"
# web_include_js = "/assets/ditech_core/js/ditech_core.js"

# app_include_js = "ditech.bundle.js"
app_include_css = "ditech.bundle.css"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "ditech_core/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}
page_js = {
    "point-of-sale": "public/js/custom_point_of_sale.js"
}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

doctype_js = {
    "Item": "public/js/custom_item.js",
    "Payment Entry": "public/js/custom_payment_entry.js",
    "POS Profile": "public/js/custom_pos_profile.js",
    "Mode of Payment": "public/js/custom_mode_of_payment.js",
    "Journal Entry" : "public/js/journal_entry_custom.js",
    "POS Closing Entry" : "public/js/custom_pos_closing_entry.js",
    # "Material Request" : "public/js/material_request_custom.js",
    # "Purchase Order" : "public/js/purchase_order_custom.js",
    # "Purchase Receipt" : "public/js/purchase_receipt_custom.js",
    # "Purchase Invoice" : "public/js/purchase_invoice_custom.js",
    "Customer" : "public/js/customer_custom.js",
    "Overtime Request" : "public/js/overtime_request_custom.js",
    "Sales Person" : "public/js/sales_person_custom.js",
    "Lead" : "public/js/lead_custom.js",
    "Opportunity" : "public/js/opportunity_custom.js",
    "Monthly Distribution" : "public/js/monthly_distribution_custom.js",
}
# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "ditech_core/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "ditech_core.utils.jinja_methods",
# 	"filters": "ditech_core.utils.jinja_filters"
# }


jinja = {
	"methods": [
        "ditech_core.ditech_core.utils.get_data_shift_type",
        "ditech_core.ditech_core.utils.get_data_print_pos_invoice",
        "ditech_core.ditech_core.utils.get_note_print_pos_invoice",
        "ditech_core.ditech_core.utils.get_loyalty_points_print_pos_invoice",
        "ditech_core.ditech_core.pos.get_closing_detail",
        ],
}

# Installation
# ------------

# before_install = "ditech_core.install.before_install"
# after_install = "ditech_core.install.after_install"

before_install = "ditech_core.utils.install_dependencies"

after_migrate = "ditech_core.setup.after_migration"

# Uninstallation
# ------------

# before_uninstall = "ditech_core.uninstall.before_uninstall"
# after_uninstall = "ditech_core.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "ditech_core.utils.before_app_install"
# after_app_install = "ditech_core.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "ditech_core.utils.before_app_uninstall"
# after_app_uninstall = "ditech_core.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "ditech_core.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

override_doctype_class = {
	"Leave Policy Assignment": "ditech_core.overrides.CustomLeavePolicyAssignment",
	"POS Closing Entry": "ditech_core.overrides.CustomPOSClosingEntry",
	"POS Invoice": "ditech_core.overrides.CustomPOSInvoice",
	"Item": "ditech_core.overrides.CustomItem",
    "Promotional Scheme": "ditech_core.overrides.CustomPromotionalScheme",
    "Asset": "ditech_core.overrides.CustomAsset",
}

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }
doc_events = {
    # "Item": {
    #     "before_insert": "ditech_core.overrides.before_insert_item"
    # },
    "POS Invoice": {
		"after_insert": "ditech_core.overrides.update_status",
		"on_update": "ditech_core.overrides.on_update_pos_inv",
		"on_submit": "ditech_core.overrides.update_status_open",
	},
    "Asset Movement": {
        "on_update": "ditech_core.overrides.on_update_asset_movement"
    },
    "Payment Entry": {
        "on_submit": "ditech_core.overrides.on_submit_payment_entry",
        "validate": "ditech_core.overrides.on_validate_payment_entry"
    },
    "Bank Account": {
        "before_save": "ditech_core.overrides.before_save_bank_account",
    },
    "Pricing Rule": {
        "before_save": "ditech_core.overrides.before_save_pricing_rule",
    },
    # "Sales Person": {
    #     "before_save": "ditech_core.overrides.before_save_sale_person",
    # },
    "Monthly Distribution": {
        "before_insert": "ditech_core.overrides.before_insert_monthly_distribution",
    },
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"ditech_core.tasks.all"
# 	],
# 	"daily": [
# 		"ditech_core.tasks.daily"
# 	],
# 	"hourly": [
# 		"ditech_core.tasks.hourly"
# 	],
# 	"weekly": [
# 		"ditech_core.tasks.weekly"
# 	],
# 	"monthly": [
# 		"ditech_core.tasks.monthly"
# 	],
# }
scheduler_events = {
    "daily": [
		"ditech_core.tasks.auto_reverse_journal_entry"
	],
}


# Testing
# -------

# before_tests = "ditech_core.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "ditech_core.event.get_events"
# }
override_whitelisted_methods = {
	"erpnext.assets.doctype.asset.asset.make_asset_movement": "ditech_core.event.make_asset_movement",
	"erpnext.accounts.doctype.pos_closing_entry.pos_closing_entry.get_pos_invoices": "ditech_core.overrides.get_pos_invoices",
    "erpnext.accounts.doctype.pricing_rule.pricing_rule.apply_pricing_rule": "ditech_core.event.apply_pricing_rule",
}
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "ditech_core.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["ditech_core.utils.before_request"]
# after_request = ["ditech_core.utils.after_request"]

# Job Events
# ----------
# before_job = ["ditech_core.utils.before_job"]
# after_job = ["ditech_core.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"ditech_core.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

fixtures = [
    "E Filing Settings"
]
