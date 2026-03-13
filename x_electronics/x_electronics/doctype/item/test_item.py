# Copyright (c) 2026, Chris and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestItem(FrappeTestCase):
	def test_item_creation(self):
		# Test if item inserts correctly
		item_code = "LAPTOP-001"
		if frappe.db.exists("Item", item_code):
			frappe.delete_doc("Item", item_code)

		item = frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": item_code,
				"item_name": "Gaming Laptop",
				"unit_of_measure": "Nos",
			}
		).insert()

		self.assertEqual(item.name, item_code)
