var exchange = 0;
frappe.ui.form.on("POS Closing Entry", {
  onload: (frm) => {
    if (!frm.is_new()) get_exchange(frm);
  },
  pos_profile: (frm) => {
    get_exchange(frm);
  },
  before_save(frm) {
    for (let row of frm.doc.payment_reconciliation) {
      if (row.custom_opening_amount)
        row.expected_amount += row.custom_opening_amount / exchange;
      row.difference =
        row.closing_amount +
        (row.custom_closing_amount || 0) / exchange -
        row.expected_amount;
    }
  },
  async set_opening_amounts(frm) {
    return frappe.db
      .get_doc("POS Opening Entry", frm.doc.pos_opening_entry)
      .then(({ balance_details }) => {
        balance_details.forEach((detail) => {
          frm.doc.payment_reconciliation.forEach((row) => {
            if (row.mode_of_payment === detail.mode_of_payment) {
              frappe.model.set_value(
                row.doctype,
                row.name,
                "custom_opening_amount",
                detail.custom_opening_amount
              );
              frappe.model.set_value(
                row.doctype,
                row.name,
                "expected_amount",
                detail.custom_opening_amount / exchange + row.expected_amount
              );
            }
          });
        });
      });
  },
});

frappe.ui.form.on("POS Closing Entry Detail", {
  custom_closing_amount: (frm, cdt, cdn) => {
    calculator_difference(frm, cdt, cdn);
  },
  closing_amount: (frm, cdt, cdn) => {
    calculator_difference(frm, cdt, cdn);
  },
});
function calculator_difference(frm, cdt, cdn) {
  const row = locals[cdt][cdn];
  frappe.model.set_value(
    cdt,
    cdn,
    "difference",
    flt(
      row.closing_amount +
        (row.custom_closing_amount || 0) / exchange -
        row.expected_amount
    )
  );
}

function get_exchange(frm) {
  frappe.call({
    method: "ditech_core.ditech_core.utils.get_currency_exchange",
    args: {
      from_currency: frm.doc.custom_currency,
      to_currency: frm.doc.custom_second_currency || frm.doc.custom_currency,
    },
    callback: (r) => {
      if (r.message) exchange = r.message;
    },
  });
}

function set_form_data(data, frm) {
  data.forEach((d) => {
    add_to_pos_transaction(d, frm);
    frm.doc.grand_total += flt(d.grand_total);
    frm.doc.net_total += flt(d.net_total);
    frm.doc.total_quantity += flt(d.total_qty);
    refresh_payments(d, frm);
    refresh_taxes(d, frm);
  });
}
