// Copyright (c) 2025, tech@ditech.software and contributors
// For license information, please see license.txt

frappe.ui.form.on("Sales Person Target", {
	refresh(frm) {
        filter_doctypes(frm);
        child_table_refresh(frm);
        $("button[data-label='Save']").hide();

	},
    before_save: function(frm) {
        order_target_team(frm);
    },
});

function filter_doctypes(frm) {
    frm.fields_dict.target_team.grid.get_field('item_group').get_query = () => ({
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
