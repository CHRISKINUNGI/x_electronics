import frappe


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
		{"fieldname": "valuation_rate", "label": "Valuation Rate", "fieldtype": "Currency", "width": 120},
		{"fieldname": "balance_qty", "label": "Balance Qty", "fieldtype": "Float", "width": 120},
	]


def get_data(filters):
	filters = filters or {}
	conditions = ["docstatus = 1"]
	values = []

	if filters.get("from_date"):
		conditions.append("posting_date >= %s")
		values.append(filters.get("from_date"))

	if filters.get("to_date"):
		conditions.append("posting_date <= %s")
		values.append(filters.get("to_date"))

	warehouse_filter, warehouse_values = get_warehouse_filter(filters.get("warehouse"))
	if warehouse_filter:
		conditions.append(warehouse_filter)
		values.extend(warehouse_values)

	sql = """
		SELECT
			posting_date,
			item,
			warehouse,
			qty,
			incoming_rate,
			valuation_rate,
			balance_qty
		FROM `tabStock Ledger Entry`
		WHERE {conditions}
		ORDER BY posting_date DESC, creation DESC
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
