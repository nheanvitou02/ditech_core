frappe.ui.form.on('Opportunity',{
    refresh(frm){
        frm.events.set_sales_person(frm)
    },
    set_sales_person(frm){
        if(frm.is_new()){
            frappe.call({
                method:'ditech_core.utils.set_sales_person',
                callback: (r) => {
                    if(r.message != 'false'){
                        frm.set_value('sales_person', r.message)
                    }
                }
            })
        }
    }
})