// Copyright (c) 2024, tech@ditech.software and contributors
// For license information, please see license.txt

var doctype = "";

frappe.ui.form.on("E Filing", {
    refresh(frm) {
        frm.set_query("ref_doc", function () {
            return {
                filters: {
                    name: ["in", ["Sales Invoice", "Purchase Invoice", "POS Invoice", "Employee"]]
                }
            };
        });
        if(!frm.is_new()){
            frm.add_custom_button(__('Export'), function () {
                if (frm.doc.ref_doc && frm.doc.from_date && frm.doc.to_date) {
                    frappe.call({
                        method: 'ditech_core.ditech_core.doctype.e_filing.e_filing.export_e_filing_data',
                        args: {
                            doctype: frm.doc.ref_doc,
                            from_date: frm.doc.from_date,
                            to_date: frm.doc.to_date
                        },
                        freeze: true,
                        callback: function (r) {
                            if (r.message) {
                                if (frm.doc.ref_doc == "Sales Invoice" || frm.doc.ref_doc == "POS Invoice") {
                                    const a = document.createElement('a');
                                    a.href = r.message.file_url;
                                    a.download = 'e-Filing-Sale.xlsx';
                                    a.click();
                                }
                                if (frm.doc.ref_doc == "Purchase Invoice"){
                                    const a = document.createElement('a');
                                    a.href = r.message.file_url;
                                    a.download = 'e-Filing-Purchase.xlsx';
                                    a.click();
                                }
                            }
                            
                        }
                    });
                } else {
                    frappe.msgprint(__('Please select Reference Document, From Date, and To Date'));
                }
            }
        )}   
    },

    ref_doc(frm) {
        if (doctype != frm.doc.ref_doc) {
            frm.trigger('get_data');
            doctype = frm.doc.ref_doc;
        }
    },

    from_date(frm) {
        frm.trigger('get_data');
    },

    to_date(frm) {
        frm.trigger('get_data');
    },

    get_data(frm) {
        if (frm.doc.ref_doc && frm.doc.from_date && frm.doc.to_date) {
            frappe.call({
                method: 'ditech_core.ditech_core.doctype.e_filing.e_filing.get_data_e_filing',
                args: {
                    doctype: frm.doc.ref_doc,
                    from_date: frm.doc.from_date,
                    to_date: frm.doc.to_date
                },
                freeze: true,
                callback: function (r) {
                    if (r.message) {
                        frm.clear_table("e_filing_detail"); 

                        r.message.forEach(row => {
                            frm.add_child("e_filing_detail", {
                                reference_type: frm.doc.ref_doc,
                                id: row.name, 
                                document_reference: row.name_reference,
                                posting_date: row.posting_date,
                                customer: row.customer,
                                supplier: row.supplier,
                                company_tax_id: row.company_tax_id,
                                customer_tax_id: row.tax_id,
                                total_amount: row.grand_total,
                            });
                        });

                        frm.refresh_field("e_filing_detail"); 
                    }
                }
            });
        }
    }
});

