// Copyright (c) 2026, Chris and contributors
// For license information, please see license.txt

frappe.query_reports["Stock Ledger"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
		},
		{
			fieldname: "item",
			label: __("Item"),
			fieldtype: "Link",
			options: "Item",
		},
		{
			fieldname: "warehouse",
			label: __("Warehouse"),
			fieldtype: "Link",
			options: "Warehouse",
		},
	],

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname === "qty" && data) {
			if (data.qty > 0) {
				value = `<span style="color: green; font-weight: bold;">${value}</span>`;
			} else if (data.qty < 0) {
				value = `<span style="color: red; font-weight: bold;">${value}</span>`;
			}
		}

		return value;
	},
};
