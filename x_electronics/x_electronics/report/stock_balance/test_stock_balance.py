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
		self.assertIsNotNone(row)
		self.assertEqual(row.balance_qty, 15)
		self.assertAlmostEqual(row.valuation_rate, 150)
		self.assertAlmostEqual(row.total_value, 2250)
