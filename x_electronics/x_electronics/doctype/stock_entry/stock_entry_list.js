// Copyright (c) 2026, Chris and contributors
// For license information, please see license.txt

frappe.listview_settings["Stock Entry"] = {
	get_indicator(doc) {
		const colors = {
			Receipt: [__("Receipt"), "green", "stock_entry_type,=,Receipt"],
			Consume: [__("Consume"), "red", "stock_entry_type,=,Consume"],
			Transfer: [__("Transfer"), "blue", "stock_entry_type,=,Transfer"],
		};

		if (doc.docstatus === 0) {
			return [__("Draft"), "grey", "docstatus,=,0"];
		}
		if (doc.docstatus === 2) {
			return [__("Cancelled"), "red", "docstatus,=,2"];
		}

		return colors[doc.stock_entry_type] || [__("Submitted"), "blue", "docstatus,=,1"];
	},
};
