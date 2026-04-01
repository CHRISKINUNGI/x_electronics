// Copyright (c) 2026, Chris and contributors
// For license information, please see license.txt

frappe.ui.form.on("Stock Entry", {
	setup(frm) {
		frm.set_query("source_warehouse", "items", () => ({
			filters: { is_group: 0 },
		}));
		frm.set_query("target_warehouse", "items", () => ({
			filters: { is_group: 0 },
		}));
	},

	refresh(frm) {
		toggle_warehouse_columns(frm);
		set_type_indicator(frm);
	},

	stock_entry_type(frm) {
		toggle_warehouse_columns(frm);
		clear_warehouses(frm);
		set_type_indicator(frm);
	},
});

frappe.ui.form.on("Stock Entry Detail", {
	item(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (row.item) {
			frappe.db.get_value("Item", row.item, "valuation_rate", (r) => {
				if (r && r.valuation_rate) {
					frappe.model.set_value(cdt, cdn, "basic_rate", r.valuation_rate);
				}
			});
		}
	},

	quantity(frm, cdt, cdn) {
		calculate_amount(frm, cdt, cdn);
	},

	basic_rate(frm, cdt, cdn) {
		calculate_amount(frm, cdt, cdn);
	},
});

function toggle_warehouse_columns(frm) {
	const type = frm.doc.stock_entry_type;

	const show_source = type === "Consume" || type === "Transfer";
	const show_target = type === "Receipt" || type === "Transfer";

	const grid = frm.fields_dict.items.grid;

	grid.update_docfield_property("source_warehouse", "hidden", show_source ? 0 : 1);
	grid.update_docfield_property("source_warehouse", "in_list_view", show_source ? 1 : 0);
	grid.update_docfield_property("source_warehouse", "reqd", show_source ? 1 : 0);

	grid.update_docfield_property("target_warehouse", "hidden", show_target ? 0 : 1);
	grid.update_docfield_property("target_warehouse", "in_list_view", show_target ? 1 : 0);
	grid.update_docfield_property("target_warehouse", "reqd", show_target ? 1 : 0);

	grid.visible_columns = undefined;
	grid.setup_visible_columns();
	grid.refresh();
}

function clear_warehouses(frm) {
	(frm.doc.items || []).forEach((row) => {
		if (frm.doc.stock_entry_type === "Receipt") {
			frappe.model.set_value(row.doctype, row.name, "source_warehouse", "");
		} else if (frm.doc.stock_entry_type === "Consume") {
			frappe.model.set_value(row.doctype, row.name, "target_warehouse", "");
		}
	});
}

function calculate_amount(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	frappe.model.set_value(cdt, cdn, "amount", flt(row.quantity) * flt(row.basic_rate));
}

function set_type_indicator(frm) {
	const type = frm.doc.stock_entry_type;
	const colors = { Receipt: "green", Consume: "red", Transfer: "blue" };
	if (type && colors[type]) {
		frm.page.set_indicator(__(type), colors[type]);
	}
}
