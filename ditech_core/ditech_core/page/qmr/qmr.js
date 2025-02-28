frappe.pages["qmr"].on_page_load = async function (wrapper) {
  var page = frappe.ui.make_app_page({
    parent: wrapper,
    title: "Quick Material Request",
    single_column: true,
  });
  page.pos_profile = {
    warehouse: "",
    cost_center: "",
  };
  await frappe.call({
    method: "ditech_core.ditech_core.qmr.get_pos_profile",
    freeze: true,
    callback: function (r) {
      if (r.message) page.pos_profile = r.message;
    },
  });

  page.start = 0;
  page.request_button = page.set_primary_action(__("View/Request"), () => {
    let items = page.mr_item.items;
    localStorage.setItem("qmr_items", JSON.stringify(items));
    if (items && items.length > 0) {
      page.mr_item.request(items);
      return;
    }
    frappe.show_alert({
      indicator: "yellow",
      message: __("Item is not empty!"),
    });
    frappe.utils.play_sound("error");
  });

  frappe.require("qmr.bundle.js", function () {
    page.mr_group = new ditech.QMRGroup({
      parent: page.main,
      event: {
        get_items: (item_group) => {
          page.mr_item.item_group = item_group;
          page.mr_item.start = 0;
          page.mr_item.refresh();
        },
      },
      method: "ditech_core.ditech_core.qmr.get_item_group",
      template: "qmr_group_list",
    });

    page.mr_group.refresh();
    page.mr_item = new ditech.QMRItem({
      parent: page.main,
      page_length: 20,
      pos_profile: page.pos_profile,
      method: "ditech_core.ditech_core.qmr.get_data",
      template: "qmr_list",
    });

    page.mr_item.items = JSON.parse(localStorage.getItem("qmr_items")) || [];

    page.main.find(".page-form").css({ display: "none" });

    var setup_click = function (doctype) {
      page.main.on(
        "click",
        'a[data-type="' + doctype.toLowerCase() + '"]',
        function () {
          var name = $(this).attr("data-name");
          var field = page[doctype.toLowerCase() + "_field"];
          if (field.get_value() === name) {
            frappe.set_route("Form", doctype, name);
          } else {
            field.set_input(name);
            page.item_dashboard.refresh();
          }
        }
      );
    };

    setup_click("Item");
    setup_click("Warehouse");
  });
};
