frappe.ui.form.on("POS Profile", {
  setup: (frm) => {
    frm.set_query("custom_receipt_print_format", function () {
      return {
        filters: [["Print Format", "doc_type", "=", "POS Invoice"]],
      };
    });
  },
  onload: (frm) => {
    frm.trigger("check_business_type");
  },
  before_save: function (frm) {
    let value = frm.doc.custom_prefix_invoice_number;
    if (value && !/\d{7}$/.test(value)) {
      frappe.msgprint({
        title: __("Prefix Invoice Number"),
        message: __(
          "The last 7 characters must be numbers."
        ),
        indicator: "red",
      });
      frm.set_value("custom_prefix_invoice_number", "");
    }
  },
  custom_business_type: (frm) => {
    frm.trigger("check_business_type");
  },
  check_business_type: (frm) => {
    [
      "custom_auto_av_table",
      "print_format",
      "custom_barkitchen_s",
      "custom_user_service_section",
    ].forEach((field) => {
      frm.set_df_property(
        field,
        "hidden",
        frm.doc.custom_business_type == "Retail"
      );
    });
  },
});
