import frappe


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
		{"fieldname": "valuation_rate", "label": "Valuation Rate", "fieldtype": "Currency", "width": 130},
		{"fieldname": "total_value", "label": "Total Value", "fieldtype": "Currency", "width": 130},
	]


def get_data(filters):
	# We group by Item and Warehouse to get the current standing
	data = frappe.db.sql(
		"""
        SELECT 
            item, 
            warehouse, 
            SUM(qty) as balance_qty
        FROM `tabStock Ledger Entry`
        WHERE docstatus = 1
        GROUP BY item, warehouse
        HAVING SUM(qty) != 0
    """,
		as_dict=True,
	)

	# Attach the latest valuation rate to each row
	for row in data:
		item_doc = frappe.get_doc("Item", row.item)
		row.valuation_rate = item_doc.valuation_rate or 0
		row.total_value = row.balance_qty * row.valuation_rate

	return data
