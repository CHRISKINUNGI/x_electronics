import frappe
from frappe.model.document import Document
from frappe.utils import flt


class StockLedgerEntry(Document):
	def validate(self):
		if flt(self.qty) == 0:
			frappe.throw("Quantity cannot be zero.")

		if flt(self.incoming_rate) < 0:
			frappe.throw("Incoming rate cannot be negative.")

	def on_submit(self):
		self.update_running_balance_and_valuation()

	def update_running_balance_and_valuation(self):
		# Row locks reduce write races for same item/warehouse valuation updates.
		frappe.db.sql("SELECT name FROM `tabItem` WHERE name = %s FOR UPDATE", self.item)
		frappe.db.sql(
			"""
			SELECT name
			FROM `tabStock Ledger Entry`
			WHERE item = %s AND warehouse = %s AND docstatus = 1
			FOR UPDATE
		""",
			(self.item, self.warehouse),
		)

		# Stateless moving average: derive prior state from posted rows each submit.
		result = frappe.db.sql(
			"""
			SELECT
				COALESCE(SUM(qty), 0) AS previous_balance_qty,
				COALESCE(SUM(CASE WHEN qty > 0 THEN qty * incoming_rate ELSE 0 END), 0) AS previous_incoming_value,
				COALESCE(SUM(CASE WHEN qty > 0 THEN qty ELSE 0 END), 0) AS previous_incoming_qty
			FROM `tabStock Ledger Entry`
			WHERE item = %s AND warehouse = %s AND docstatus = 1 AND name != %s
		""",
			(self.item, self.warehouse, self.name),
			as_dict=True,
		)[0]

		incoming_qty = self.qty if self.qty > 0 else 0
		incoming_rate = self.incoming_rate or 0
		total_incoming_qty = result.previous_incoming_qty + incoming_qty
		total_incoming_value = result.previous_incoming_value + (incoming_qty * incoming_rate)

		valuation_rate = (total_incoming_value / total_incoming_qty) if total_incoming_qty else 0
		balance_qty = result.previous_balance_qty + self.qty
		if balance_qty < 0:
			frappe.throw(
				f"Negative stock is not allowed for item {self.item} in warehouse {self.warehouse}."
			)

		self.db_set("valuation_rate", valuation_rate, update_modified=False)
		self.db_set("balance_qty", balance_qty, update_modified=False)
		frappe.db.set_value("Item", self.item, "valuation_rate", valuation_rate, update_modified=False)
