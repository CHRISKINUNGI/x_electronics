// Copyright (c) 2026, Chris and contributors
// For license information, please see license.txt

frappe.ui.form.on("Stock Ledger Entry", {
	refresh(frm) {
		// SLE should not be created manually — it is created by Stock Entry
		if (frm.is_new()) {
			frm.set_intro(
				__("Stock Ledger Entries are created automatically when a Stock Entry is submitted."),
				"blue"
			);
		}

		// Make all fields read-only on submitted docs
		if (frm.doc.docstatus === 1) {
			frm.disable_form();
		}
	},
});
