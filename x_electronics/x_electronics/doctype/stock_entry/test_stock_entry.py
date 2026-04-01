from uuid import uuid4

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt


class TestStockEntry(FrappeTestCase):
	def setUp(self):
		suffix = uuid4().hex[:8].upper()
		self.item_code = f"TEST-IPHONE-{suffix}"
		self.source_warehouse = f"Test Store {suffix}"
		self.target_warehouse = f"Target Store {suffix}"

		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": self.item_code,
				"item_name": f"Test iPhone {suffix}",
				"unit_of_measure": "Nos",
			}
		).insert()

		frappe.get_doc({"doctype": "Warehouse", "warehouse_name": self.source_warehouse}).insert()

	def test_receipt_creates_ledger_entry(self):
		ste = frappe.get_doc(
			{
				"doctype": "Stock Entry",
				"stock_entry_type": "Receipt",
				"posting_date": frappe.utils.today(),
				"items": [
					{
						"item": self.item_code,
						"quantity": 50,
						"basic_rate": 800,
						"target_warehouse": self.source_warehouse,
					}
				],
			}
		)
		ste.insert()
		ste.submit()

		ledger_entries = frappe.get_all(
			"Stock Ledger Entry",
			filters={"item": self.item_code, "warehouse": self.source_warehouse, "qty": 50},
			fields=["name", "qty", "incoming_rate"],
		)
		self.assertTrue(len(ledger_entries) > 0)
		self.assertEqual(ledger_entries[0].qty, 50)
		self.assertEqual(ledger_entries[0].incoming_rate, 800)

	def test_consume_creates_negative_ledger_entry(self):
		frappe.get_doc(
			{
				"doctype": "Stock Entry",
				"stock_entry_type": "Receipt",
				"posting_date": frappe.utils.today(),
				"items": [
					{
						"item": self.item_code,
						"quantity": 30,
						"basic_rate": 600,
						"target_warehouse": self.source_warehouse,
					}
				],
			}
		).insert().submit()

		ste = frappe.get_doc(
			{
				"doctype": "Stock Entry",
				"stock_entry_type": "Consume",
				"posting_date": frappe.utils.today(),
				"items": [
					{
						"item": self.item_code,
						"quantity": 15,
						"source_warehouse": self.source_warehouse,
					}
				],
			}
		)
		ste.insert()
		ste.submit()

		ledger_entries = frappe.get_all(
			"Stock Ledger Entry",
			filters={"item": self.item_code, "warehouse": self.source_warehouse, "qty": -15},
			fields=["qty"],
		)
		self.assertTrue(len(ledger_entries) > 0)

	def test_transfer_creates_two_ledger_entries(self):
		frappe.get_doc({"doctype": "Warehouse", "warehouse_name": self.target_warehouse}).insert()
		frappe.get_doc(
			{
				"doctype": "Stock Entry",
				"stock_entry_type": "Receipt",
				"posting_date": frappe.utils.today(),
				"items": [
					{
						"item": self.item_code,
						"quantity": 20,
						"basic_rate": 500,
						"target_warehouse": self.source_warehouse,
					}
				],
			}
		).insert().submit()

		ste = frappe.get_doc(
			{
				"doctype": "Stock Entry",
				"stock_entry_type": "Transfer",
				"posting_date": frappe.utils.today(),
				"items": [
					{
						"item": self.item_code,
						"quantity": 20,
						"source_warehouse": self.source_warehouse,
						"target_warehouse": self.target_warehouse,
					}
				],
			}
		)
		ste.insert()
		ste.submit()

		source_ledger = frappe.get_all(
			"Stock Ledger Entry",
			filters={"item": self.item_code, "warehouse": self.source_warehouse, "qty": -20},
		)
		self.assertTrue(len(source_ledger) > 0)

		target_ledger = frappe.get_all(
			"Stock Ledger Entry",
			filters={"item": self.item_code, "warehouse": self.target_warehouse, "qty": 20},
		)
		self.assertTrue(len(target_ledger) > 0)

	def test_consume_without_available_stock_is_blocked(self):
		ste = frappe.get_doc(
			{
				"doctype": "Stock Entry",
				"stock_entry_type": "Consume",
				"posting_date": frappe.utils.today(),
				"items": [
					{
						"item": self.item_code,
						"quantity": 1,
						"source_warehouse": self.source_warehouse,
					}
				],
			}
		)
		with self.assertRaises(frappe.ValidationError):
			ste.insert()

	def test_non_positive_quantity_is_blocked(self):
		ste = frappe.get_doc(
			{
				"doctype": "Stock Entry",
				"stock_entry_type": "Receipt",
				"posting_date": frappe.utils.today(),
				"items": [
					{
						"item": self.item_code,
						"quantity": 0,
						"basic_rate": 100,
						"target_warehouse": self.source_warehouse,
					}
				],
			}
		)
		with self.assertRaises(frappe.ValidationError):
			ste.insert()

	def test_cancel_reverses_ledger_entries(self):
		"""Cancelling a Stock Entry should cancel its ledger entries and free up stock."""
		ste = frappe.get_doc(
			{
				"doctype": "Stock Entry",
				"stock_entry_type": "Receipt",
				"posting_date": frappe.utils.today(),
				"items": [
					{
						"item": self.item_code,
						"quantity": 25,
						"basic_rate": 400,
						"target_warehouse": self.source_warehouse,
					}
				],
			}
		)
		ste.insert()
		ste.submit()

		# Verify ledger entry exists
		sle_count = frappe.db.count(
			"Stock Ledger Entry",
			{"voucher_no": ste.name, "docstatus": 1},
		)
		self.assertEqual(sle_count, 1)

		# Cancel
		ste.cancel()

		# Ledger entries should now be cancelled
		active_sles = frappe.db.count(
			"Stock Ledger Entry",
			{"voucher_no": ste.name, "docstatus": 1},
		)
		self.assertEqual(active_sles, 0)

		cancelled_sles = frappe.db.count(
			"Stock Ledger Entry",
			{"voucher_no": ste.name, "docstatus": 2},
		)
		self.assertEqual(cancelled_sles, 1)

	def test_full_receipt_consume_transfer_flow(self):
		"""Integration test: Receipt -> Transfer -> Consume across warehouses."""
		frappe.get_doc({"doctype": "Warehouse", "warehouse_name": self.target_warehouse}).insert()

		# 1. Receipt into source warehouse
		frappe.get_doc(
			{
				"doctype": "Stock Entry",
				"stock_entry_type": "Receipt",
				"posting_date": frappe.utils.today(),
				"items": [
					{
						"item": self.item_code,
						"quantity": 100,
						"basic_rate": 500,
						"target_warehouse": self.source_warehouse,
					}
				],
			}
		).insert().submit()

		# 2. Transfer 40 units to target warehouse
		frappe.get_doc(
			{
				"doctype": "Stock Entry",
				"stock_entry_type": "Transfer",
				"posting_date": frappe.utils.today(),
				"items": [
					{
						"item": self.item_code,
						"quantity": 40,
						"source_warehouse": self.source_warehouse,
						"target_warehouse": self.target_warehouse,
					}
				],
			}
		).insert().submit()

		# 3. Consume 10 from target warehouse
		frappe.get_doc(
			{
				"doctype": "Stock Entry",
				"stock_entry_type": "Consume",
				"posting_date": frappe.utils.today(),
				"items": [
					{
						"item": self.item_code,
						"quantity": 10,
						"source_warehouse": self.target_warehouse,
					}
				],
			}
		).insert().submit()

		# Verify final balances via ledger
		source_balance = flt(
			frappe.db.sql(
				"""SELECT COALESCE(SUM(qty), 0) FROM `tabStock Ledger Entry`
				WHERE item = %s AND warehouse = %s AND docstatus = 1""",
				(self.item_code, self.source_warehouse),
			)[0][0]
		)
		target_balance = flt(
			frappe.db.sql(
				"""SELECT COALESCE(SUM(qty), 0) FROM `tabStock Ledger Entry`
				WHERE item = %s AND warehouse = %s AND docstatus = 1""",
				(self.item_code, self.target_warehouse),
			)[0][0]
		)

		self.assertEqual(source_balance, 60)  # 100 - 40
		self.assertEqual(target_balance, 30)  # 40 - 10
