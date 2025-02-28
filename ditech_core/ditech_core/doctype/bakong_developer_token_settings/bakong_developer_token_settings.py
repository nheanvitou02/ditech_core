# Copyright (c) 2025, tech@ditech.software and contributors
# For license information, please see license.txt

import frappe
import requests
from frappe import _
from frappe.model.document import Document
from ditech_core import constants as CONST


class BakongDeveloperTokenSettings(Document):
	def before_save(self):
		try:
			email = self.email
			api_url = CONST.BASE_BAKONG_URL + CONST.renew_token_endpoint
			payload = {"email": email}
			response = requests.post(api_url, headers=CONST.headers, json=payload)
			response.raise_for_status()
			print(f'response {type(response)}: {response}')
			data = response.json()
			if data.get("responseCode") == 0:
				message = 'success'

			else:
				frappe.throw(
					title='Error',
					msg=_('Invalid Developer Email.'),
				)

		except requests.exceptions.RequestException as e:
			frappe.throw(
				title='Connection Error',
				msg=_('Failed to connect to the Bakong API. Please check your internet connection or contact support.'),
			)