from uuid import uuid4

import frappe
from frappe.tests.utils import FrappeTestCase

from x_electronics.x_electronics.report.stock_balance.stock_balance import execute


class TestStockBalanceReport(FrappeTestCase):
	def setUp(self):
		suffix = uuid4().hex[:8].upper()
		self.item_code = f"TEST-BAL-{suffix}"
		self.warehouse = f"Balance Warehouse {suffix}"

		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": self.item_code,
				"item_name": f"Balance Item {suffix}",
				"unit_of_measure": "Nos",
			}
		).insert()
		frappe.get_doc({"doctype": "Warehouse", "warehouse_name": self.warehouse}).insert()

		for qty, rate in [(10, 100), (10, 200), (-5, 0)]:
			sle = frappe.get_doc(
				{
					"doctype": "Stock Ledger Entry",
					"item": self.item_code,
					"warehouse": self.warehouse,
					"qty": qty,
					"incoming_rate": rate,
					"posting_date": frappe.utils.today(),
				}
			)
			sle.insert()
			sle.submit()

	def test_report_calculation(self):
		columns, data = execute({"to_date": frappe.utils.today()})

		column_fields = [c.get("fieldname") for c in columns]
		self.assertIn("valuation_rate", column_fields)
		self.assertIn("balance_qty", column_fields)
		self.assertIn("total_value", column_fields)

		row = next(
			(entry for entry in data if entry.item == self.item_code and entry.warehouse == self.warehouse),
			None,
		)
		# FIFO: consume 5 takes from oldest batch (100/unit)
		# Remaining queue: [(5, 100), (10, 200)] → value=2500, qty=15, rate=166.67
		self.assertIsNotNone(row)
		self.assertEqual(row.balance_qty, 15)
		self.assertAlmostEqual(row.valuation_rate, 2500 / 15, places=2)
		self.assertAlmostEqual(row.total_value, 2500, places=2)

	def test_warehouse_hierarchy_filter(self):
		"""Filtering by a group warehouse should include child warehouse data."""
		suffix = uuid4().hex[:8].upper()
		group_warehouse = f"Group WH {suffix}"
		child_warehouse = f"Child WH {suffix}"

		frappe.get_doc(
			{"doctype": "Warehouse", "warehouse_name": group_warehouse, "is_group": 1}
		).insert()
		child = frappe.get_doc(
			{"doctype": "Warehouse", "warehouse_name": child_warehouse, "parent_warehouse": group_warehouse}
		).insert()

		item_code = f"TEST-HIER-{suffix}"
		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": item_code,
				"item_name": f"Hierarchy Item {suffix}",
				"unit_of_measure": "Nos",
			}
		).insert()

		sle = frappe.get_doc(
			{
				"doctype": "Stock Ledger Entry",
				"item": item_code,
				"warehouse": child.name,
				"qty": 20,
				"incoming_rate": 300,
				"posting_date": frappe.utils.today(),
			}
		)
		sle.insert()
		sle.submit()

		# Filter by group — should include child warehouse stock
		_, data = execute({"warehouse": group_warehouse, "to_date": frappe.utils.today()})
		row = next((d for d in data if d.item == item_code), None)
		self.assertIsNotNone(row)
		self.assertEqual(row.balance_qty, 20)
