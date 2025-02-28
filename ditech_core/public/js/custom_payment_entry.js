frappe.ui.form.on("Payment Entry", { 
    refresh: (frm) => {
        frm.set_df_property('company','hidden', 0)
        if( frm.is_new() && frm.doc.custom_batch_payment_request ){
            frm.trigger("custom_batch_payment_request")
        }
    },
    custom_batch_payment_request: (frm) => {
        frm.trigger('fetch_batch_payment_request')
    },
    fetch_batch_payment_request: (frm) => {
        frappe.call({
            method: "frappe.client.get",
            args: {
                doctype: "Batch Payment Request",
                name: frm.doc.custom_batch_payment_request,
            },
            callback: function (r) {
                if( !r.exc ){
                    let data = r.message
                    if(Boolean(data)){
                        frappe.run_serially([
                            () => frm.set_value('payment_type', data.payment_type),
                            () => frm.set_value('party_type', data.party_type),
                            () => frm.set_value('party', data.party),
                            () => {
                                if( frm.doc.payment_type == "Pay" ) {
                                    frm.set_value('paid_from', data.paid_to_from_account)
                                    frm.trigger('paid_from')
                                }
                                if( frm.doc.payment_type == "Receive" ) {
                                    frm.set_value('paid_to', data.paid_to_from_account)
                                    frm.trigger('paid_to')
                                }
                            },
                            () => frm.set_value('paid_amount', data.request_amount),
                            () => {
                                if( data.references.length > 0 ){
                                frappe.model.clear_table(frm.doc, "references")
                                for( let d of data.references ){
                                    let row = frappe.model.add_child(frm.doc, 'references')
                                    row.reference_doctype  = d.reference_doctype
                                    row.reference_name     = d.reference_name
                                    row.outstanding_amount = d.outstanding_amount
                                    row.allocated_amount   = d.allocated_amount
                                    row.total_amount       = d.total_amount
                                    row.due_date           = d.due_date
                                    row.payment_term       = d.payment_term
                                }
                                frm.refresh_field('references')
                            }
                            }
                        ])
                        // frm.set_value('unallocated_amount', data.request_amount)
                            // () => frm.set_df_property('party_type', 'read_only', 1),
                            // () => frm.set_df_property('party', 'read_only', 1),
                            // () => frm.set_df_property('paid_amount', 'read_only', 1),
                            // () => frm.set_df_property('received_amount', 'read_only', 1)
                    }
                }
            },
        })
    }
})