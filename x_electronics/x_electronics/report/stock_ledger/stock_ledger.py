import frappe

from x_electronics.x_electronics.utils import build_stock_conditions


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"fieldname": "posting_date", "label": "Date", "fieldtype": "Date", "width": 120},
		{"fieldname": "item", "label": "Item", "fieldtype": "Link", "options": "Item", "width": 150},
		{
			"fieldname": "warehouse",
			"label": "Warehouse",
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": 150,
		},
		{"fieldname": "qty", "label": "Qty (In/Out)", "fieldtype": "Float", "width": 120},
		{"fieldname": "incoming_rate", "label": "Incoming Rate", "fieldtype": "Currency", "width": 120},
		{"fieldname": "outgoing_rate", "label": "Outgoing Rate", "fieldtype": "Currency", "width": 120},
		{"fieldname": "valuation_rate", "label": "Valuation Rate", "fieldtype": "Currency", "width": 120},
		{"fieldname": "balance_qty", "label": "Balance Qty", "fieldtype": "Float", "width": 120},
	]


def get_data(filters):
	conditions, values = build_stock_conditions(filters)

	sql = f"""
		SELECT
			posting_date,
			item,
			warehouse,
			qty,
			incoming_rate,
			outgoing_rate,
			valuation_rate,
			balance_qty
		FROM `tabStock Ledger Entry`
		WHERE {conditions}
		ORDER BY posting_date DESC, creation DESC
	"""

	return frappe.db.sql(sql, values, as_dict=True)
