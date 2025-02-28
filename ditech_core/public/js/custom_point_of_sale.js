frappe.pages["point-of-sale"].on_page_load = function (wrapper) {
    return frappe.call({
        method: "frappe.desk.desk_page.getpage",
        args: { name: "Point of Sale" },
        callback: function (r) {
            callback();
        },
        freeze: true,
    });
};
