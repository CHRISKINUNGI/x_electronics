import frappe
from frappe.utils import flt


def get_row_warehouses(row):
	"""Return (source_warehouse, target_warehouse) from a Stock Entry Detail row.

	Handles both full field names and short aliases (s_warehouse / t_warehouse).
	"""
	source = row.get("source_warehouse") or row.get("s_warehouse")
	target = row.get("target_warehouse") or row.get("t_warehouse")
	return source, target


def build_stock_conditions(filters):
	"""Build common SQL WHERE conditions for stock reports.

	Handles: docstatus, from_date, to_date, item, and warehouse (tree-aware).
	Returns (conditions_string, values) for use in a WHERE clause.
	"""
	filters = filters or {}
	conditions = ["docstatus = 1"]
	values = []

	if filters.get("from_date"):
		conditions.append("posting_date >= %s")
		values.append(filters["from_date"])

	if filters.get("to_date"):
		conditions.append("posting_date <= %s")
		values.append(filters["to_date"])

	if filters.get("item"):
		conditions.append("item = %s")
		values.append(filters["item"])

	warehouse_filter, warehouse_values = get_warehouse_filter(filters.get("warehouse"))
	if warehouse_filter:
		conditions.append(warehouse_filter)
		values.extend(warehouse_values)

	return " AND ".join(conditions), values


def get_warehouse_filter(warehouse):
	"""Build a SQL filter clause for a warehouse, with tree-aware expansion.

	If the warehouse is a group, all descendant warehouses are included
	using the NestedSet lft/rgt bounds.

	Returns:
		tuple: (filter_clause, values) for use in SQL WHERE conditions.
	"""
	if not warehouse:
		return "", []

	warehouse_doc = frappe.db.get_value("Warehouse", warehouse, ["is_group", "lft", "rgt"], as_dict=True)
	if not warehouse_doc:
		return "warehouse = %s", [warehouse]

	if warehouse_doc.is_group:
		warehouses = frappe.get_all(
			"Warehouse",
			filters={"lft": [">=", warehouse_doc.lft], "rgt": ["<=", warehouse_doc.rgt]},
			pluck="name",
		)
	else:
		warehouses = [warehouse]

	if not warehouses:
		return "warehouse = %s", [warehouse]

	placeholders = ", ".join(["%s"] * len(warehouses))
	return f"warehouse IN ({placeholders})", warehouses


def consume_from_fifo_queue(queue, qty_needed):
	"""Drain qty_needed from the front of the FIFO queue.

	Returns (outgoing_rate, updated_queue) where outgoing_rate is the
	weighted average cost of the consumed batches.
	"""
	qty_remaining_to_consume = qty_needed
	total_cost = 0.0
	updated_queue = [list(batch) for batch in queue]

	for batch in updated_queue:
		if qty_remaining_to_consume <= 0:
			break
		qty_taken_from_batch = min(batch[0], qty_remaining_to_consume)
		total_cost += qty_taken_from_batch * batch[1]
		batch[0] -= qty_taken_from_batch
		qty_remaining_to_consume -= qty_taken_from_batch

	updated_queue = [batch for batch in updated_queue if batch[0] > 1e-9]
	outgoing_rate = (total_cost / qty_needed) if qty_needed else 0
	return outgoing_rate, updated_queue
