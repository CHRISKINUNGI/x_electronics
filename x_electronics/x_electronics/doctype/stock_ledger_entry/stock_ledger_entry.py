import frappe
from frappe.model.document import Document


class StockLedgerEntry(Document):
	def on_submit(self):
		self.update_item_valuation()

	def update_item_valuation(self):
		item = frappe.get_doc("Item", self.item)

		# Bulletproof parameterized SQL for aggregation
		result = frappe.db.sql(
			"""
            SELECT SUM(qty)
            FROM `tabStock Ledger Entry`
            WHERE item = %s AND name != %s AND docstatus = 1
        """,
			(self.item, self.name),
		)

		# Extract the sum from the SQL result tuple
		previous_qty = result[0][0] if result and result[0][0] else 0
		previous_rate = item.valuation_rate or 0

		current_qty = self.qty
		current_rate = self.incoming_rate or 0
		total_qty = previous_qty + current_qty

		if total_qty > 0:
			new_valuation = ((previous_qty * previous_rate) + (current_qty * current_rate)) / total_qty
		else:
			new_valuation = current_rate

		# Update Item Master and current record
		item.db_set("valuation_rate", new_valuation)
		self.db_set("valuation_rate", new_valuation)
