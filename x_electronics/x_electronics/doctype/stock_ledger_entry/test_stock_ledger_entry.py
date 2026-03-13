from uuid import uuid4

import frappe
from frappe.tests.utils import FrappeTestCase


class TestStockLedgerEntry(FrappeTestCase):
	def setUp(self):
		suffix = uuid4().hex[:8].upper()
		self.item_code = f"TEST-SLE-ITEM-{suffix}"
		self.warehouse = f"SLE Warehouse {suffix}"

		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": self.item_code,
				"item_name": f"SLE Item {suffix}",
				"unit_of_measure": "Nos",
			}
		).insert()
		frappe.get_doc({"doctype": "Warehouse", "warehouse_name": self.warehouse}).insert()

	def _submit_sle(self, qty, incoming_rate):
		doc = frappe.get_doc(
			{
				"doctype": "Stock Ledger Entry",
				"item": self.item_code,
				"warehouse": self.warehouse,
				"qty": qty,
				"incoming_rate": incoming_rate,
				"posting_date": frappe.utils.today(),
			}
		)
		doc.insert()
		doc.submit()
		return frappe.get_doc("Stock Ledger Entry", doc.name)

	def test_moving_average_and_balance(self):
		receipt_1 = self._submit_sle(qty=10, incoming_rate=100)
		self.assertEqual(receipt_1.balance_qty, 10)
		self.assertEqual(receipt_1.valuation_rate, 100)

		receipt_2 = self._submit_sle(qty=5, incoming_rate=200)
		self.assertEqual(receipt_2.balance_qty, 15)
		self.assertAlmostEqual(receipt_2.valuation_rate, (10 * 100 + 5 * 200) / 15)

		consume = self._submit_sle(qty=-4, incoming_rate=0)
		self.assertEqual(consume.balance_qty, 11)
		self.assertAlmostEqual(consume.valuation_rate, (10 * 100 + 5 * 200) / 15)

		item_rate = frappe.db.get_value("Item", self.item_code, "valuation_rate")
		self.assertAlmostEqual(item_rate, consume.valuation_rate)

	def test_direct_negative_stock_submission_is_blocked(self):
		with self.assertRaises(frappe.ValidationError):
			self._submit_sle(qty=-1, incoming_rate=0)
