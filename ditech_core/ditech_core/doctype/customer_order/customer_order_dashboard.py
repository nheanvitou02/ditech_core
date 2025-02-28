from frappe import _


def get_data():
	return {
		"fieldname": "custom_customer_order",
		"transactions": [
			{
				"label": _("Fulfillment"),
				"items": ["POS Invoice"],
			},
		],
	}
