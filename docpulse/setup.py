# Copyright (c) 2025, DocPulse and contributors
# For license information, please see license.txt

import frappe


def after_install():
	"""Create roles and set up permissions after app installation"""
	setup_roles()


def setup_roles():
	"""Create DocPulse roles if they don't exist"""
	roles = [
		{
			"role_name": "DocPulse Master Manager",
			"desk_access": 1,
			"is_custom": 1,
			"disabled": 0
		},
		{
			"role_name": "DocPulse Manager",
			"desk_access": 1,
			"is_custom": 1,
			"disabled": 0
		}
	]
	
	for role_data in roles:
		if not frappe.db.exists("Role", role_data["role_name"]):
			frappe.get_doc({
				"doctype": "Role",
				**role_data
			}).insert(ignore_permissions=True)
			frappe.db.commit()

