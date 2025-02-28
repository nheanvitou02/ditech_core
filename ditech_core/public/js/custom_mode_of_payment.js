frappe.ui.form.on("Mode of Payment", {
  setup: (frm) => {
    frm.set_query("custom_bank_account", () => {
      return {
        filters: {
          custom_mapping_bakong: 1,
        },
      };
    });
  },
  custom_bank_account: (frm) => {
    if (frm.doc.custom_bank_account)
      frappe.db.get_value(
        "Bank Account",
        frm.doc.custom_bank_account,
        "account",
        (r) => {
          if (r.account) {
            frm.doc.accounts.forEach((row) => {
              frappe.model.set_value(
                row.doctype,
                row.name,
                "default_account",
                r.account
              );
            });
            frm.refresh_field("accounts");
          }
        }
      );
  },
});
