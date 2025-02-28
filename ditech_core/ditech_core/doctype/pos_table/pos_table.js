// Copyright (c) 2024, tech@ditech.software and contributors
// For license information, please see license.txt

frappe.ui.form.on("POS Table", {
    refresh(frm) {
        var template = "";
        if (frm.doc.__islocal && frm.doc.menu_qr_code) {
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
        if (frm.doc.__islocal && frm.doc.menu_qr_code) {
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
