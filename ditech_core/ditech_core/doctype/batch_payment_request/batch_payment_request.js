// Copyright (c) 2024, tech@ditech.software and contributors
// For license information, please see license.txt

frappe.ui.form.on("Batch Payment Request", {
    validate(frm) {
        if( frm.doc.request_amount > frm.doc.outstanding_amount ){
            frappe.throw(`Request amount ${frm.doc.currency} ${frm.doc.request_amount} cannot be bigger than ${frm.doc.currency} ${frm.doc.outstanding_amount}`)
        }
        frm.events.validate_references(frm);
    },
	refresh(frm) {
        frm.trigger('make_payment_entry_btn')
        frm.set_query(
            'party_type',
            () => {
                return {
                    filters: {
                        'name': ['in', ['Customer', 'Supplier']]
                    }
                }
            }
        )

        frm.set_df_property('references', 'cannot_add_rows', true);
	},
    party_type: (frm) => {
        if ( frm.doc.party_type == "Customer" ) {
            frm.set_value("payment_request_type", "Inward")
            frm.set_value("payment_type", "Receive")
        }
        else if ( frm.doc.party_type == "Supplier" ) {
            frm.set_value("payment_request_type", "Outward")
            frm.set_value("payment_type", "Pay")
        }
        frm.set_value('party','')
        frm.refresh_field("payment_request_type") 
        frm.refresh_field("payment_type")
    },
    party: (frm) => {
        if( frm.doc.docstatus == 0 ){
            frappe.call({
                method: "get_payment_references",
                type: "POST",
                doc: frm.doc,
                freeze: true,
                freeze_message: __(`Fetching payment reference from ${frm.doc.party_type} - ${frm.doc.party}`),
                callback: (r) => {
                    if( !r.exc ){
                        let total_amount = 0
                        let outstanding_amount = 0
                        frm.clear_table('references')
                        if ( r.message ){
                            let data = r.message 
                            for( let d of data ) {
                                // let payment_schedule = d.payment_schedule
                                // for( let p of payment_schedule ){
                                    let row = frm.add_child('references')
                                    row.reference_doctype  = d.doctype
                                    row.reference_name     = d.name
                                    row.outstanding_amount = d.outstanding_amount
                                    row.allocated_amount   = d.outstanding_amount
                                    row.due_date           = d.due_date
                                    row.payment_term       = d.payment_term

                                    row.total_amount       = d.grand_total
                                    if ( "Sales Invoice" == d.doctype ){
                                        row.account = d.debit_to
                                        console.log(`account: ${d.debit_to}`)
                                    }
                                    if ( "Purchase Invoice" == d.doctype ){
                                        row.account = d.credit_to
                                        console.log(`account: ${d.credit_to}`)
                                    }
                                    // row.account            = d.debit_to
                                    total_amount          += row.allocated_amount
                                    outstanding_amount    += row.outstanding_amount
                                // }
                                // total_amount += d.grand_total
                                // console.log(`payment_schedule: ${JSON.parse(payment_schedule)}`)
                            }
                            frm.set_value('request_amount', total_amount)
                            frm.set_value('outstanding_amount', outstanding_amount)
                            frm.refresh_field('request_amount')
                            frm.refresh_field('outstanding_amount')
                            frm.refresh_field('references')
                        }
                    }
                }
            })
        }
    },
    set_request_amount: (frm) => {
        let request_amount = 0
        let rows = frm.doc.references
        rows.forEach( (r, idx) => {
            request_amount += r.allocated_amount
        })
        
        frm.set_value('request_amount', request_amount)
        frm.refresh_field('request_amount')
    },
    make_payment_entry_btn: (frm) => {
        if ( frm.doc.docstatus == 1 ){
            frm.add_custom_button('Payment Entry', ()=>{
                frm.trigger("create_payment_entry")
            }, __("Create"))
        }
        if ( Boolean(frm.doc.payment_entry) ){
            frm.clear_custom_button()
        }
    },
    create_payment_entry: (frm) => {
        let params = {
            "payment_type": frm.doc.payment_type,
            "mode_of_payment": frm.doc.mode_of_payment,
            "company": frm.doc.company,
            "custom_batch_payment_request": frm.doc.name
        }

        frappe.new_doc(
            "Payment Entry",
            params
        )
    },
    validate_references: (frm) => {
        let items = frm.doc.references 
        items.forEach( (r, idx) => {
            if( r.allocated_amount > r.outstanding_amount ){
                frappe.throw("Please check your references, allocated amount cannot be bigger than outstanding amount.")
            }
        })
    },
    set_request_amount: (frm) => {
        let total_outstanding = 0
        let request_amount = 0
        let rows = frm.doc.references
        for ( let r of rows ){
            request_amount += r.allocated_amount
            total_outstanding += r.outstanding_amount
        }
        console.log(`total outstanding: ${total_outstanding}`)
        
        frm.set_value('request_amount', request_amount)
        frm.set_value('outstanding_amount', total_outstanding)
        frm.refresh_field('request_amount')
        frm.refresh_field('outstanding_amount')
    }
});
frappe.ui.form.on('Batch Payment Request References', {
    form_render: (frm, cdt, cdn)=>{
        console.log('form render')
    },
    references_remove: (frm, cdt, cdn)=>{
        console.log('item remove')
        frm.events.set_request_amount(frm)
    }
});

frappe.ui.form.on('Batch Payment Request References', 'allocated_amount', (frm, cdt, cdn)=>{
    let item = locals[cdt][cdn]; 
    if ( item.allocated_amount > item.outstanding_amount ){
        frappe.throw(`Allocated amount cannot be bigger than outstanding amount ${item.outstanding_amount}.`)
    }

    frm.events.set_request_amount(frm)
});

