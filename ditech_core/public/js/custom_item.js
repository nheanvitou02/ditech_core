frappe.ui.form.on("Item", {
  refresh(frm) {
    const barcode = frm.fields_dict["barcodes"].grid;

    function togglePrintButton() {
      const selected_rows = barcode.get_selected();
      const print_button = barcode.grid_buttons.find(".btn-custom");

      if (selected_rows.length > 0) {
        print_button.show();
      } else {
        print_button.hide();
      }
    }

    barcode.add_custom_button(__("Print"), function () {
      const selected_rows = barcode.get_selected_children();
      frappe.call({
        method: "ditech_core.ditech_core.utils.render_print_template",
        args: {
          barcodes: selected_rows,
          item_code: frm.doc.item_code,
          item_name: frm.doc.item_name,
        },
        callback: function (r) {
          if (r.message) {
            var printWindow = window.open("", "_blank");
            if (!printWindow) {
              frappe.msgprint(__("Please allow popups for this site"));
              return;
            }

            printWindow.document.write(r.message);
            printWindow.document.close();
            printWindow.focus();

            printWindow.addEventListener("afterprint", function () {
              printWindow.close();
            });

            setTimeout(() => printWindow.print(), 200);

            setTimeout(function () {
              if (!printWindow.closed) {
                printWindow.close();
              }
            }, 30000);
          }
        },
      });
    });

    barcode.grid_buttons
      .find(".btn-custom")
      .removeClass("btn-default")
      .addClass("btn-primary");

    barcode.grid_buttons.find(".btn-custom").hide();

    barcode.wrapper.on("change", ".grid-row-check", togglePrintButton);
  },
});
frappe.ui.form.on("Item Barcode", {
  barcode: function (frm, cdt, cdn) {
    var row = locals[cdt][cdn];
    frappe.model.set_value(cdt, cdn, "custom_preview", row.barcode);
  },
});
