import frappe

from x_electronics.x_electronics.utils import build_stock_conditions


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"fieldname": "item", "label": "Item", "fieldtype": "Link", "options": "Item", "width": 150},
		{
			"fieldname": "warehouse",
			"label": "Warehouse",
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": 150,
		},
		{"fieldname": "balance_qty", "label": "Balance Qty", "fieldtype": "Float", "width": 120},
		{"fieldname": "valuation_rate", "label": "Valuation Rate", "fieldtype": "Currency", "width": 120},
		{"fieldname": "total_value", "label": "Total Value", "fieldtype": "Currency", "width": 120},
	]


def get_data(filters):
	conditions, values = build_stock_conditions(filters)

	# Get balance quantities per item/warehouse.
	rows = frappe.db.sql(
		f"""
		SELECT item, warehouse, SUM(qty) AS balance_qty
		FROM `tabStock Ledger Entry`
		WHERE {conditions}
		GROUP BY item, warehouse
		HAVING balance_qty > 0
	""",
		values,
		as_dict=True,
	)

	# Valuation rate under FIFO is the rate stored on the most recent SLE —
	# it reflects the weighted cost of whatever batches remain in the queue.
	for row in rows:
		latest = frappe.db.sql(
			"""
			SELECT valuation_rate FROM `tabStock Ledger Entry`
			WHERE item = %s AND warehouse = %s AND docstatus = 1
			ORDER BY posting_date DESC, creation DESC
			LIMIT 1
		""",
			(row.item, row.warehouse),
		)
		row.valuation_rate = latest[0][0] if latest else 0
		row.total_value = row.balance_qty * row.valuation_rate

	return rows
