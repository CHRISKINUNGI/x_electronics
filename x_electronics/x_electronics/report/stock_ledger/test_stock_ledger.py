from uuid import uuid4

import frappe
from frappe.tests.utils import FrappeTestCase

from x_electronics.x_electronics.report.stock_ledger.stock_ledger import execute


class TestStockLedgerReport(FrappeTestCase):
	def setUp(self):
		suffix = uuid4().hex[:8].upper()
		self.item_code = f"TEST-LEDGER-{suffix}"
		self.warehouse = f"Ledger Warehouse {suffix}"

		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": self.item_code,
				"item_name": f"Ledger Item {suffix}",
				"unit_of_measure": "Nos",
			}
		).insert()
		frappe.get_doc({"doctype": "Warehouse", "warehouse_name": self.warehouse}).insert()

		for qty, rate in [(12, 100), (-2, 0)]:
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

	def test_report_returns_movement_rows(self):
		columns, data = execute({"to_date": frappe.utils.today()})
		column_fields = [c.get("fieldname") for c in columns]
		self.assertIn("qty", column_fields)
		self.assertIn("valuation_rate", column_fields)
		self.assertIn("balance_qty", column_fields)

		rows = [d for d in data if d.item == self.item_code and d.warehouse == self.warehouse]
		self.assertEqual(len(rows), 2)
		self.assertTrue(any(r.qty == 12 for r in rows))
		self.assertTrue(any(r.qty == -2 for r in rows))

	def test_date_range_filter(self):
		"""Entries outside the date range should be excluded."""
		suffix = uuid4().hex[:8].upper()
		item_code = f"TEST-DATE-{suffix}"
		warehouse = f"Date Warehouse {suffix}"

		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": item_code,
				"item_name": f"Date Item {suffix}",
				"unit_of_measure": "Nos",
			}
		).insert()
		frappe.get_doc({"doctype": "Warehouse", "warehouse_name": warehouse}).insert()

		# Entry in January
		sle1 = frappe.get_doc(
			{
				"doctype": "Stock Ledger Entry",
				"item": item_code,
				"warehouse": warehouse,
				"qty": 10,
				"incoming_rate": 100,
				"posting_date": "2026-01-15",
			}
		)
		sle1.insert()
		sle1.submit()

		# Entry in March
		sle2 = frappe.get_doc(
			{
				"doctype": "Stock Ledger Entry",
				"item": item_code,
				"warehouse": warehouse,
				"qty": 5,
				"incoming_rate": 200,
				"posting_date": "2026-03-15",
			}
		)
		sle2.insert()
		sle2.submit()

		# Filter Feb-Apr: should only include March entry
		_, data = execute({"from_date": "2026-02-01", "to_date": "2026-04-01", "item": item_code})
		rows = [d for d in data if d.item == item_code]
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0].qty, 5)

		# Filter Jan only: should only include January entry
		_, data = execute({"from_date": "2026-01-01", "to_date": "2026-01-31", "item": item_code})
		rows = [d for d in data if d.item == item_code]
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0].qty, 10)
