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

	def test_fifo_valuation_and_balance(self):
		# Queue after receipt 1: [(10, 100)]
		receipt_1 = self._submit_sle(qty=10, incoming_rate=100)
		self.assertEqual(receipt_1.balance_qty, 10)
		self.assertEqual(receipt_1.valuation_rate, 100)
		self.assertEqual(receipt_1.outgoing_rate, 0)

		# Queue after receipt 2: [(10, 100), (5, 200)]
		# Remaining value = 1000 + 1000 = 2000, qty = 15, rate = 133.33
		receipt_2 = self._submit_sle(qty=5, incoming_rate=200)
		self.assertEqual(receipt_2.balance_qty, 15)
		self.assertAlmostEqual(receipt_2.valuation_rate, (10 * 100 + 5 * 200) / 15, places=2)

		# Consume 4: FIFO takes from oldest batch (100/unit)
		# Queue after: [(6, 100), (5, 200)]
		# Outgoing rate = 100 (all from first batch)
		# Remaining value = 600 + 1000 = 1600, qty = 11, rate = 145.45
		consume = self._submit_sle(qty=-4, incoming_rate=0)
		self.assertEqual(consume.balance_qty, 11)
		self.assertAlmostEqual(consume.outgoing_rate, 100, places=2)
		self.assertAlmostEqual(consume.valuation_rate, (6 * 100 + 5 * 200) / 11, places=2)

		item_rate = frappe.db.get_value("Item", self.item_code, "valuation_rate")
		self.assertAlmostEqual(item_rate, consume.valuation_rate)

	def test_fifo_cross_batch_consume(self):
		# Queue: [(5, 100), (5, 200)]
		self._submit_sle(qty=5, incoming_rate=100)
		self._submit_sle(qty=5, incoming_rate=200)

		# Consume 8: takes all 5 from first batch + 3 from second
		# Outgoing rate = (5*100 + 3*200) / 8 = 1100/8 = 137.50
		# Queue after: [(2, 200)], valuation_rate = 200
		consume = self._submit_sle(qty=-8, incoming_rate=0)
		self.assertAlmostEqual(consume.outgoing_rate, (5 * 100 + 3 * 200) / 8, places=2)
		self.assertEqual(consume.balance_qty, 2)
		self.assertAlmostEqual(consume.valuation_rate, 200, places=2)

	def test_direct_negative_stock_submission_is_blocked(self):
		with self.assertRaises(frappe.ValidationError):
			self._submit_sle(qty=-1, incoming_rate=0)

	def test_backdated_entry_recalculates_subsequent(self):
		# Submit a receipt dated today first.
		today = frappe.utils.today()
		yesterday = frappe.utils.add_days(today, -1)

		sle_today = frappe.get_doc(
			{
				"doctype": "Stock Ledger Entry",
				"item": self.item_code,
				"warehouse": self.warehouse,
				"qty": 5,
				"incoming_rate": 200,
				"posting_date": today,
			}
		)
		sle_today.insert()
		sle_today.submit()

		# Now submit a backdated entry — it is chronologically first.
		sle_yesterday = frappe.get_doc(
			{
				"doctype": "Stock Ledger Entry",
				"item": self.item_code,
				"warehouse": self.warehouse,
				"qty": 10,
				"incoming_rate": 100,
				"posting_date": yesterday,
			}
		)
		sle_yesterday.insert()
		sle_yesterday.submit()

		# After repost, the "today" entry should see queue [[10,100],[5,200]].
		reloaded = frappe.get_doc("Stock Ledger Entry", sle_today.name)
		self.assertEqual(reloaded.balance_qty, 15)
		expected_rate = (10 * 100 + 5 * 200) / 15
		self.assertAlmostEqual(reloaded.valuation_rate, expected_rate, places=2)

	def test_cancel_recalculates_subsequent(self):
		sle1 = self._submit_sle(qty=10, incoming_rate=100)
		sle2 = self._submit_sle(qty=5, incoming_rate=200)

		# sle2 sees both batches in the queue.
		self.assertEqual(sle2.balance_qty, 15)

		# Cancel the first receipt — sle2 should be recalculated without it.
		sle1_doc = frappe.get_doc("Stock Ledger Entry", sle1.name)
		sle1_doc.cancel()

		reloaded = frappe.get_doc("Stock Ledger Entry", sle2.name)
		self.assertEqual(reloaded.balance_qty, 5)
		self.assertAlmostEqual(reloaded.valuation_rate, 200, places=2)
