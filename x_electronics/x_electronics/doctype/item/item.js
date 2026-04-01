// Copyright (c) 2026, Chris and contributors
// For license information, please see license.txt

frappe.ui.form.on("Item", {
	refresh(frm) {
		if (!frm.is_new()) {
			// Show stock balance dashboard on existing items
			frm.add_custom_button(__("Stock Balance"), () => {
				frappe.set_route("query-report", "Stock Balance", {
					item: frm.doc.name,
				});
			});

			frm.add_custom_button(__("Stock Ledger"), () => {
				frappe.set_route("query-report", "Stock Ledger", {
					item: frm.doc.name,
				});
			});
		}
	},
});
