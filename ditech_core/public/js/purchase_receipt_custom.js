frappe.ui.form.on("Purchase Receipt", {
    table_html(frm){
        frappe.call({
            method:'ditech_core.utils.get_connection',
            args:{
                doctype: frm.doc.doctype,
                name: frm.doc.name,
            },
            callback: (r) => {
                let res = r.message
                $(res).appendTo(frm.fields_dict.custom_pr_html.$wrapper.empty());
            }
        })
    },
    setup(frm){
        if(!frm.is_new()){
            frm.trigger('table_html')
        }
    },
    refresh(frm){
        if(!frm.is_new()){
            frm.trigger('table_html')
        }
        if(frm.is_new()){
            frm.set_df_property('custom_connection_doctype', 'hidden', 1);
        }else{
            frm.set_df_property('custom_connection_doctype', 'hidden', 0);
        }
    },
});