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

	incoming_value = "SUM(CASE WHEN qty > 0 THEN qty * incoming_rate ELSE 0 END)"
	incoming_qty = "NULLIF(SUM(CASE WHEN qty > 0 THEN qty ELSE 0 END), 0)"
	valuation_rate = f"IFNULL({incoming_value} / {incoming_qty}, 0)"

	sql = f"""
		SELECT
			item,
			warehouse,
			SUM(qty) AS balance_qty,
			{valuation_rate} AS valuation_rate,
			SUM(qty) * {valuation_rate} AS total_value
		FROM `tabStock Ledger Entry`
		WHERE {conditions}
		GROUP BY item, warehouse
		HAVING balance_qty > 0
	"""

	return frappe.db.sql(sql, values, as_dict=True)
