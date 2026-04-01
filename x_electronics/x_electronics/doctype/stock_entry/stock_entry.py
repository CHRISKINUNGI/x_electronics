import frappe
from frappe.model.document import Document
from frappe.utils import flt

from x_electronics.x_electronics.utils import get_row_warehouses


class StockEntry(Document):
	def validate(self):
		self.validate_rows()
		self.validate_stock_availability()
		self.calculate_totals()

	def validate_rows(self):
		if self.stock_entry_type not in {"Receipt", "Consume", "Transfer"}:
			frappe.throw(f"Unsupported stock entry type: {self.stock_entry_type}")

		if not self.items:
			frappe.throw("At least one row is required.")

		for row in self.items:
			qty = flt(row.get("quantity"))
			rate = flt(row.get("basic_rate"))
			source_warehouse, target_warehouse = get_row_warehouses(row)

			if qty <= 0:
				frappe.throw("Quantity must be greater than zero.")

			if rate < 0:
				frappe.throw("Basic rate cannot be negative.")

			if self.stock_entry_type == "Receipt" and not target_warehouse:
				frappe.throw("Target warehouse is required for Receipt.")

			if self.stock_entry_type == "Consume" and not source_warehouse:
				frappe.throw("Source warehouse is required for Consume.")

			if self.stock_entry_type == "Transfer":
				if not source_warehouse or not target_warehouse:
					frappe.throw("Both source and target warehouse are required for Transfer.")
				if source_warehouse == target_warehouse:
					frappe.throw("Source and target warehouse cannot be the same for Transfer.")

	def calculate_totals(self):
		self.total_quantity = sum(flt(row.quantity) for row in self.items)
		self.total_amount = sum(flt(row.quantity) * flt(row.basic_rate) for row in self.items)

	def validate_stock_availability(self):
		# Aggregate required outgoing qty per (item, source warehouse) to validate in one pass.
		outgoing_requirements = {}
		for row in self.items:
			if self.stock_entry_type not in {"Consume", "Transfer"}:
				continue

			source_warehouse, _ = get_row_warehouses(row)
			if not source_warehouse:
				continue

			key = (row.item, source_warehouse)
			outgoing_requirements[key] = outgoing_requirements.get(key, 0) + flt(row.quantity)

		for (item, warehouse), required_qty in outgoing_requirements.items():
			available_qty = flt(
				frappe.db.sql(
					"""
					SELECT COALESCE(SUM(qty), 0)
					FROM `tabStock Ledger Entry`
					WHERE item = %s AND warehouse = %s AND docstatus = 1
				""",
					(item, warehouse),
				)[0][0]
			)
			if required_qty > available_qty:
				frappe.throw(
					f"Insufficient stock for item {item} in warehouse {warehouse}. "
					f"Requested: {required_qty}, Available: {available_qty}"
				)

	def on_cancel(self):
		self.cancel_ledger_entries()

	def cancel_ledger_entries(self):
		"""Cancel all Stock Ledger Entries created by this Stock Entry."""
		ledger_entries = frappe.get_all(
			"Stock Ledger Entry",
			filters={"voucher_no": self.name, "docstatus": 1},
			pluck="name",
		)
		for sle_name in ledger_entries:
			sle = frappe.get_doc("Stock Ledger Entry", sle_name)
			sle.cancel()

	def on_submit(self):
		# Create immutable Stock Ledger rows according to entry type semantics.
		for row in self.items:
			qty = flt(row.get("quantity"))
			rate = flt(row.get("basic_rate"))
			source_warehouse, target_warehouse = get_row_warehouses(row)

			# 1. Receipt: Stock comes IN to the Target Warehouse (+)
			if self.stock_entry_type == "Receipt":
				self.create_ledger_entry(row.item, qty, rate, target_warehouse)

			# 2. Consume: Stock goes OUT of the Source Warehouse (-)
			elif self.stock_entry_type == "Consume":
				self.create_ledger_entry(row.item, -qty, rate, source_warehouse)

			# 3. Transfer: Stock leaves Source (-) and enters Target (+)
			elif self.stock_entry_type == "Transfer":
				self.create_ledger_entry(row.item, -qty, rate, source_warehouse)
				self.create_ledger_entry(row.item, qty, rate, target_warehouse)

	def create_ledger_entry(self, item, qty, rate, warehouse):
		# Prevent errors if a user forgets to select a warehouse
		if not warehouse:
			frappe.throw("Warehouse is required for this transaction.")

		sle = frappe.get_doc(
			{
				"doctype": "Stock Ledger Entry",
				"item": item,
				"qty": qty,
				"incoming_rate": rate or 0,
				"warehouse": warehouse,
				"posting_date": self.posting_date,
				"voucher_no": self.name,
			}
		)
		sle.insert()
		sle.submit()
