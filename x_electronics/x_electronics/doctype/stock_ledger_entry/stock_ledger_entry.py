import json

import frappe
from frappe.model.document import Document
from frappe.utils import flt

from x_electronics.x_electronics.utils import consume_from_fifo_queue


class StockLedgerEntry(Document):
	def validate(self):
		if flt(self.qty) == 0:
			frappe.throw("Quantity cannot be zero.")

		if flt(self.incoming_rate) < 0:
			frappe.throw("Incoming rate cannot be negative.")

	def on_submit(self):
		self.update_running_balance_and_valuation()
		self._repost_subsequent_entries()

	def on_cancel(self):
		# Docstatus is already 2 here; subsequent entries won't see this entry
		# when they recalculate their prior-entry lookup.
		self._repost_subsequent_entries()
		last = frappe.db.sql(
			"""
			SELECT valuation_rate FROM `tabStock Ledger Entry`
			WHERE item = %s AND docstatus = 1
			ORDER BY posting_date DESC, creation DESC
			LIMIT 1
		""",
			self.item,
		)
		frappe.db.set_value(
			"Item", self.item, "valuation_rate", last[0][0] if last else 0, update_modified=False
		)

	def _repost_subsequent_entries(self):
		subsequent = frappe.db.sql(
			"""
			SELECT name FROM `tabStock Ledger Entry`
			WHERE item = %s AND warehouse = %s AND docstatus = 1 AND name != %s
			AND (posting_date > %s OR (posting_date = %s AND creation > %s))
			ORDER BY posting_date ASC, creation ASC
		""",
			(
				self.item,
				self.warehouse,
				self.name,
				self.posting_date,
				self.posting_date,
				self.creation,
			),
			as_dict=True,
		)
		for entry in subsequent:
			doc = frappe.get_doc("Stock Ledger Entry", entry.name)
			doc.update_running_balance_and_valuation()

	def update_running_balance_and_valuation(self):
		# Lock the item and all its SLEs for this warehouse so two concurrent
		# submits cannot both read the same prior state and produce duplicate balances.
		frappe.db.sql("SELECT name FROM `tabItem` WHERE name = %s FOR UPDATE", self.item)
		frappe.db.sql(
			"""
			SELECT name FROM `tabStock Ledger Entry`
			WHERE item = %s AND warehouse = %s AND docstatus = 1
			FOR UPDATE
		""",
			(self.item, self.warehouse),
		)

		# Read queue state from the immediately prior submitted entry — O(1) per submit.
		prior = frappe.db.sql(
			"""
			SELECT balance_qty, fifo_queue FROM `tabStock Ledger Entry`
			WHERE item = %s AND warehouse = %s AND docstatus = 1 AND name != %s
			AND (posting_date < %s OR (posting_date = %s AND creation < %s))
			ORDER BY posting_date DESC, creation DESC
			LIMIT 1
		""",
			(
				self.item,
				self.warehouse,
				self.name,
				self.posting_date,
				self.posting_date,
				self.creation,
			),
			as_dict=True,
		)

		if prior:
			queue = json.loads(prior[0].fifo_queue or "[]")
			balance_qty = flt(prior[0].balance_qty) + flt(self.qty)
		else:
			queue = []
			balance_qty = flt(self.qty)

		if balance_qty < 0:
			frappe.throw(
				f"Negative stock is not allowed for item {self.item} in warehouse {self.warehouse}."
			)

		outgoing_rate = 0.0

		if flt(self.qty) > 0:
			# Receipt: new stock arrives at a known purchase rate, added to the back of the queue.
			queue.append([flt(self.qty), flt(self.incoming_rate)])
		else:
			# Consume: drain the oldest batches first; outgoing_rate is the weighted
			# average cost of exactly the batches that left.
			outgoing_rate, queue = consume_from_fifo_queue(queue, abs(flt(self.qty)))

		# Valuation rate = cost of what is still in the queue, not a historical blend.
		remaining_value = sum(batch_qty * batch_rate for batch_qty, batch_rate in queue)
		remaining_qty = sum(batch_qty for batch_qty, batch_rate in queue)
		valuation_rate = (remaining_value / remaining_qty) if remaining_qty else 0

		self.db_set("fifo_queue", json.dumps(queue), update_modified=False)
		self.db_set("outgoing_rate", outgoing_rate, update_modified=False)
		self.db_set("valuation_rate", valuation_rate, update_modified=False)
		self.db_set("balance_qty", balance_qty, update_modified=False)
		frappe.db.set_value("Item", self.item, "valuation_rate", valuation_rate, update_modified=False)
