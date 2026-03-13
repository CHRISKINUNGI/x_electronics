import frappe
from frappe.tests.utils import FrappeTestCase


class TestWarehouse(FrappeTestCase):
	def test_warehouse_tree(self):
		# Create a Parent Warehouse
		if not frappe.db.exists("Warehouse", "Parent WH"):
			parent = frappe.get_doc(
				{"doctype": "Warehouse", "warehouse_name": "Parent WH", "is_group": 1}
			).insert()

		# Create a Child Warehouse
		child_name = "Child WH"
		if not frappe.db.exists("Warehouse", child_name):
			child = frappe.get_doc(
				{
					"doctype": "Warehouse",
					"warehouse_name": child_name,
					"is_group": 0,
					"parent_warehouse": "Parent WH",
				}
			).insert()

		# Assert the child correctly points to the parent
		self.assertEqual(frappe.db.get_value("Warehouse", child_name, "parent_warehouse"), "Parent WH")
