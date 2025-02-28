frappe.provide("ditech.BarKitchen");

frappe.pages["bar-kitchen"].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Bar/Kitchen"),
		single_column: true,
	});

	frappe.require("bk.bundle.js", function () {
		wrapper.bk = new ditech.BarKitchen.Controller(wrapper);
		window.cur_pos = wrapper.bk;
	});
};

frappe.pages["bar-kitchen"].refresh = function (wrapper) {
	if (document.scannerDetectionData) {
		onScan.detachFrom(document);
		wrapper.bk.wrapper.html("");
		wrapper.bk.check_opening_entry();
	}
}