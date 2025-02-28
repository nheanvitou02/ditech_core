// Copyright (c) 2024, tech@ditech.software and contributors
// For license information, please see license.txt

frappe.ui.form.on("Menu QR Code", {
  refresh(frm) {
    var template = "";
    if (frm.doc.__islocal) {
      template = '<img src="" />';
      frm.set_df_property(
        "qr_preview",
        "options",
        frappe.render_template(template)
      );
      frm.refresh_field("qr_preview");
    } else {
      template = '<img src="' + frm.doc.qr_code + '" width="240px"/>';
      frm.set_df_property(
        "qr_preview",
        "options",
        frappe.render_template(template)
      );
      frm.refresh_field("qr_preview");
    }
  },
  onload(frm) {
    var template = "";
    if (frm.doc.__islocal) {
      template = '<img src="" />';
      frm.set_df_property(
        "qr_preview",
        "options",
        frappe.render_template(template)
      );
      frm.refresh_field("qr_preview");
    } else {
      template = '<img src="' + frm.doc.qr_code + '" width="240px"/>';
      frm.set_df_property(
        "qr_preview",
        "options",
        frappe.render_template(template)
      );
      frm.refresh_field("qr_preview");
    }
  },
});


frappe.ui.form.on("Menu Category Item", {
  item_code: async (frm, cdt, cdn) => {
    let row = locals[cdt][cdn];
    if (row.item_code) {
      let item = await frappe.db
        .get_value("Item", row.item_code, [
          "item_name",
          "stock_uom",
          "image",
          "description",
        ])
        .then((r) => r.message);
      frappe.model.set_value(cdt, cdn, "item_name", item.item_name);
      frappe.model.set_value(cdt, cdn, "image", item.image);
      frappe.model.set_value(cdt, cdn, "uom", item.stock_uom);
      frappe.model.set_value(cdt, cdn, "description", item.description);
    }
  },
});