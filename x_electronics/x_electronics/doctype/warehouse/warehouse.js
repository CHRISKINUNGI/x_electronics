// Copyright (c) 2026, Chris and contributors
// For license information, please see license.txt

frappe.ui.form.on("Warehouse", {
	refresh(frm) {
		if (!frm.is_new() && !frm.doc.is_group) {
			frm.add_custom_button(__("Stock Balance"), () => {
				frappe.set_route("query-report", "Stock Balance", {
					warehouse: frm.doc.name,
				});
			});

			frm.add_custom_button(__("Stock Ledger"), () => {
				frappe.set_route("query-report", "Stock Ledger", {
					warehouse: frm.doc.name,
				});
			});
		}

		// Only allow selecting group warehouses as parent
		frm.set_query("parent_warehouse", () => ({
			filters: { is_group: 1 },
		}));
	},
});
