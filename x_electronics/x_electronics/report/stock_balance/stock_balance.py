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
		{"fieldname": "valuation_rate", "label": "Valuation Rate", "fieldtype": "Currency", "width": 120},
		{"fieldname": "total_value", "label": "Total Value", "fieldtype": "Currency", "width": 120},
	]


def get_data(filters):
	filters = filters or {}
	conditions = ["docstatus = 1"]
	values = []

	if filters.get("to_date"):
		conditions.append("posting_date <= %s")
		values.append(filters.get("to_date"))

	warehouse_filter, warehouse_values = get_warehouse_filter(filters.get("warehouse"))
	if warehouse_filter:
		conditions.append(warehouse_filter)
		values.extend(warehouse_values)

	sql = """
		SELECT
			item,
			warehouse,
			SUM(qty) AS balance_qty,
			IFNULL(
				SUM(CASE WHEN qty > 0 THEN qty * incoming_rate ELSE 0 END)
				/ NULLIF(SUM(CASE WHEN qty > 0 THEN qty ELSE 0 END), 0),
			0) AS valuation_rate,
			SUM(qty) * IFNULL(
				SUM(CASE WHEN qty > 0 THEN qty * incoming_rate ELSE 0 END)
				/ NULLIF(SUM(CASE WHEN qty > 0 THEN qty ELSE 0 END), 0),
			0) AS total_value
		FROM `tabStock Ledger Entry`
		WHERE {conditions}
		GROUP BY item, warehouse
		HAVING balance_qty > 0
	""".format(conditions=" AND ".join(conditions))

	return frappe.db.sql(sql, values, as_dict=True)


def get_warehouse_filter(warehouse):
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
