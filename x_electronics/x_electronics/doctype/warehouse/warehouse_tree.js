// Copyright (c) 2026, Chris and contributors
// For license information, please see license.txt

frappe.treeview_settings["Warehouse"] = {
	breadcrumb: "X Electronics",
	title: __("Warehouse"),
	get_tree_root: false,
	filters: [
		{
			fieldname: "warehouse",
			fieldtype: "Link",
			options: "Warehouse",
			label: __("Warehouse"),
			get_query: () => ({
				filters: { is_group: 1 },
			}),
		},
	],
};
