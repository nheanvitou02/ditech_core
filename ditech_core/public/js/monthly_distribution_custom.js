frappe.ui.form.on('Monthly Distribution', {
    refresh: function(frm) {
        set_default_percentage_allocation_amount(frm);
        
    },
});

function set_default_percentage_allocation_amount(frm) {
    if (frm.is_new()) {
        const percentages =frm.doc.percentages;
        frm.doc.percentages = percentages.map(p => {
            p.percentage_allocation_amount = 8.333333333333334;
            return p;
        });
    }
}