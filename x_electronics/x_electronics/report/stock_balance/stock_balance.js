// Copyright (c) 2026, Chris and contributors
// For license information, please see license.txt

frappe.query_reports["Stock Balance"] = {
	filters: [
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

	get_datatable_options(options) {
		return Object.assign(options, {
			checkboxColumn: false,
			events: {
				onRowClick(row) {
					if (!row || !row.cells) return;

					const item = row.cells[1]?.content;
					const warehouse = row.cells[2]?.content;
					if (!item || !warehouse) return;

					const to_date =
						frappe.query_report.get_filter_value("to_date") ||
						frappe.datetime.get_today();

					frappe.set_route("query-report", "Stock Ledger", {
						item: item,
						warehouse: warehouse,
						to_date: to_date,
					});
				},
			},
		});
	},
};
