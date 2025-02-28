frappe.ui.form.on("Overtime Request", {
    from_time: function (frm) {
        calculate_overtime_hours(frm);
    },
    till_time: function (frm) {
        calculate_overtime_hours(frm);
    }
});

function calculate_overtime_hours(frm) {
    if (frm.doc.from_time && frm.doc.till_time) {
        const from_time = frappe.datetime.str_to_obj(frm.doc.from_time);
        const till_time = frappe.datetime.str_to_obj(frm.doc.till_time);

        if (from_time && till_time) {
            const diff_in_seconds = (till_time - from_time) / 1000; // Difference in seconds
            const diff_in_hours = diff_in_seconds / 3600; // Convert seconds to hours
            frm.set_value("overtime_hours", diff_in_hours);
        }
    }
}
