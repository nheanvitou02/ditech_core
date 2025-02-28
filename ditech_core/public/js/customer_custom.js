frappe.ui.form.on("Customer", {
    show_accounts_receivable: (frm) => {
			cur_frm.add_custom_button(
				__("Accounts Receivable"),
				function () {
					frappe.route_options = {
                        party: frm.doc.name,
                        party_type: frm.doctype,
                        company: frm.doc.company,
					};
					frappe.set_route("query-report", "Accounts Receivable");
				},
				__("View")
			);
	},
    refresh(frm) {
        frm.events.show_accounts_receivable(frm);
    }
})