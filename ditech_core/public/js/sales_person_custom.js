frappe.ui.form.on('Sales Person', {
    refresh: function(frm) {
        filter_doctypes(frm);
        child_table_refresh(frm);
        validation_distribution_type(frm);
    },
    before_save: function(frm) {
        order_target_team(frm);
    },
    distribution_type: function(frm) {
        validation_distribution_type(frm);
    }
});

function filter_doctypes(frm) {
    frm.fields_dict.target_team.grid.get_field('item_group').get_query = () => ({
        filters: [['DocType', 'name', 'in', ['Lead', 'Opportunity', 'Quotation', 'Sales Order', 'Sales Invoice']]]
    });
    frm.fields_dict.target_team_monthly.grid.get_field('target_group').get_query = () => ({
        filters: [['DocType', 'name', 'in', ['Lead', 'Opportunity', 'Quotation', 'Sales Order', 'Sales Invoice']]]
    });
}

function child_table_refresh(frm) {
    frappe.ui.form.on('Target Doc', {
        item_group: function(frm, cdt, cdn) {
            validation_doctypes_year(frm);
        },
        fiscal_year: function(frm, cdt, cdn) {
            validation_doctypes_year(frm);
        }
    });
    frappe.ui.form.on('Target Doc Monthly', {
        target_group: function(frm, cdt, cdn) {
            create_new_row_target_doc_monthly(frm, cdt, cdn);
        validation_doctypes_year_monthly(frm);
        },
        fiscal_year: function(frm, cdt, cdn) {
            auto_fill_fiscal_year_target_team_monthly(frm, cdt, cdn);
            validation_doctypes_year_monthly(frm);
        }
    });
}

function create_new_row_target_doc_monthly(frm, cdt, cdn) {
    const months = [
        'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'
    ];
    const current_row = locals[cdt][cdn];
    const current_target_group = current_row.target_group;
    if (current_target_group) {
        current_row.months = "January";
        current_row.target_qty = 0;
        current_row.target__amount = 0;
        const rows = frm.doc.target_team_monthly || [];
        const currentRowIndex = rows.findIndex(row => row.name === current_row.name);
         if (currentRowIndex + 11 >= rows.length) {
            $.each(months, function(index, month) {
                const child = frappe.model.add_child(frm.doc, cdt, 'target_team_monthly');
                child.target_group = current_target_group;
                frappe.model.set_value(child.doctype, child.name, 'months', month);
            });
         }

        frm.refresh_field('target_team_monthly');
    }
}

function validation_doctypes_year(frm) {
    const target_team = frm.doc.target_team;
    const seen = {};

    $.each(target_team, function(index, row) {
        const { item_group, fiscal_year } = row;
        const key = item_group + ' ' + fiscal_year;
        if (seen[key]) {
            row.fiscal_year = null;
            frappe.msgprint({
                message: __('Row {0}: Duplicate Item Group and Fiscal Year', [index + 1]),
                title: __('Error'),
                indicator: 'orange'
            });
        } else {
            seen[key] = true;
        }
    });

    frm.refresh_field('target_team');
}

function order_target_team(frm) {
    const itemGroupOrder = ['Lead', 'Opportunity', 'Quotation', 'Sales Order', 'Sales Invoice'];

    frm.set_value('target_team', frm.doc.target_team.sort((a, b) => {
        if (a.fiscal_year !== b.fiscal_year) {
            return new Date(b.fiscal_year) - new Date(a.fiscal_year);
        }
        return itemGroupOrder.indexOf(a.item_group) - itemGroupOrder.indexOf(b.item_group);
    }));
}

function validation_distribution_type(frm) {
    const distribution_type = frm.doc.distribution_type;
    if (distribution_type === 'By Year') {
        frm.set_df_property('target_team_monthly', 'hidden', 1);
    } else {
        frm.set_df_property('target_team_monthly', 'hidden', 0);
    }
}

function auto_fill_fiscal_year_target_team_monthly(frm, cdt, cdn) {
    const currentRow = locals[cdt][cdn];
    const fiscalYear = parseInt(currentRow.fiscal_year);

    if (!fiscalYear || isNaN(fiscalYear)) {
        frappe.msgprint(__('Please enter a valid fiscal year.'));
        return;
    }

    let rowIndex = frm.doc.target_team_monthly.findIndex(row => row.name === currentRow.name);

    for (let i = 0; i < 11; i++) {
        rowIndex++;
        if (rowIndex >= frm.doc.target_team_monthly.length) break;

        const nextRow = frm.doc.target_team_monthly[rowIndex];
        nextRow.fiscal_year = fiscalYear.toString();
    }

    frm.refresh_field('target_team_monthly');
}

function validation_doctypes_year_monthly(frm) {
    const target_team_monthly = frm.doc.target_team_monthly;
    const seen = {}; 
    
    $.each(target_team_monthly, function(index, row) {
        const { target_group, months, fiscal_year } = row;  
        const key = target_group + ' ' + months + ' ' + fiscal_year; 
        
        if (seen[key]) {
            row.fiscal_year = null; 
            frappe.msgprint({
                message: __('Row {0}: Duplicate Month and Fiscal Year', [index + 1]),
                title: __('Error'),
                indicator: 'orange'
            });
        } else {
            seen[key] = true; 
        }
    });

    frm.refresh_field('target_team_monthly'); 
}