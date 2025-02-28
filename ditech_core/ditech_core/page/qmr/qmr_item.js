frappe.provide("ditech");

ditech.QMRItem = class QMRItem {
  constructor(opts) {
    $.extend(this, opts);
    this.make();
  }
  make() {
    var me = this;
    this.start = 0;
    if (!this.sort_by) {
      this.sort_by = "projected_qty";
      this.sort_order = "asc";
    }

    this.content = this.parent.find(".qmr-item");
    this.result = this.parent.find(".result");

    this.content.on("click", ".btn-left", function () {
      handle_left_right($(this), "Left");
    });

    this.content.on("click", ".btn-right", function () {
      handle_left_right($(this), "Right");
    });
    this.content.on("input", ".item-qty .current-page-number", function () {
      setTimeout(() => {
        const element = $(this).closest(".item-action");
        let item_code = unescape(element.attr("data-item"));
        let uom = unescape(element.attr("data-uom"));
        let total_actual_qty = unescape(element.attr("data-total_actual_qty"));
        let actual_qty = unescape(element.attr("data-actual_qty"));
        let val = parseInt($(this).val()) || 0;
        if (val <= 0) {
          $(this).val(0);
          val = 0;
        }
        setItems(val, item_code, uom, total_actual_qty, actual_qty);
      }, 300);
    });
    function handle_left_right(me, action) {
      const element = me.closest(".item-action");
      let item_code = unescape(element.attr("data-item"));
      let uom = unescape(element.attr("data-uom"));
      let total_actual_qty = unescape(element.attr("data-total_actual_qty"));
      let actual_qty = unescape(element.attr("data-actual_qty"));
      const $input = element.find(".current-page-number");
      let currentValue = parseInt($input.val()) || 0;
      let val = 0;
      if (action == "Left") {
        if (currentValue > 0) {
          val = currentValue - 1;
        } else val = 0;
      }

      if (action == "Right") {
        val = currentValue + 1;
      }
      $input.val(val);
      setItems(val, item_code, uom, total_actual_qty, actual_qty);
    }

    function setItems(val, item_code, uom, total_actual_qty, actual_qty) {
      let existItem = me.items.find((i) => i.item_code == item_code);
      if (existItem) {
        if (val == 0)
          me.items = me.items.filter((i) => i.item_code != item_code);
        else existItem["qty"] = val;
      } else if (val > 0)
        me.items.push({
          item_code: item_code,
          qty: 1,
          stock_uom: uom,
          total_actual_qty: total_actual_qty,
          actual_qty: actual_qty,
        });
    }

    this.content.find(".btn-more").on("click", function () {
      me.start += me.page_length;
      me.refresh();
    });
  }
  refresh() {
    if (this.before_refresh) {
      this.before_refresh();
    }

    let args = {
      item_code: this.item_code,
      cache_items: this.items,
      warehouse: this.warehouse,
      parent_warehouse: this.parent_warehouse,
      item_group: this.item_group,
      company: this.company,
      start: this.start,
      sort_by: this.sort_by,
      sort_order: this.sort_order,
    };

    var me = this;
    frappe.call({
      method: this.method,
      args: args,
      callback: function (r) {
        me.render(r.message);
        if (me.after_refresh) {
          me.after_refresh();
        }
      },
    });
  }
  render(data) {
    if (this.start === 0) {
      this.max_count = 0;
      this.result.empty();
    }

    let context = "";
    if (this.page_name === "warehouse-capacity-summary") {
      context = this.get_capacity_dashboard_data(data);
    } else {
      context = this.get_qmr_page_data(data, this.max_count, true);
    }

    // show more button
    if (data && data.length === this.page_length + 1) {
      this.content.find(".more").removeClass("hidden");

      // remove the last element
      data.splice(-1);
    } else {
      this.content.find(".more").addClass("hidden");
    }

    // If not any stock in any warehouses provide a message to end user
    if (context.data.length > 0) {
      this.content.find(".result").css("text-align", "unset");
      $(frappe.render_template(this.template, context)).appendTo(this.result);
    } else {
      var message = __("No Stock Available Currently");
      this.content.find(".result").css("text-align", "center");

      $(`<div class='text-muted' style='margin: 20px 5px;'>
				${message} </div>`).appendTo(this.result);
    }
  }

  get_qmr_page_data(data, max_count, show_item) {
    if (!max_count) max_count = 0;
    if (!data) data = [];

    data.forEach(function (d) {
      d.actual_or_pending =
        d.projected_qty +
        d.reserved_qty +
        d.reserved_qty_for_production +
        d.reserved_qty_for_sub_contract;
      d.pending_qty = 0;
      d.total_reserved =
        d.reserved_qty +
        d.reserved_qty_for_production +
        d.reserved_qty_for_sub_contract;
      if (d.actual_or_pending > d.actual_qty) {
        d.pending_qty = d.actual_or_pending - d.actual_qty;
      }

      max_count = Math.max(
        d.actual_or_pending,
        d.actual_qty,
        d.total_reserved,
        max_count
      );
    });

    let can_write = 0;
    if (frappe.boot.user.can_write.indexOf("Stock Entry") >= 0) {
      can_write = 1;
    }

    return {
      data: data,
      max_count: max_count,
      can_write: can_write,
      show_item: show_item || false,
    };
  }

  get_capacity_dashboard_data(data) {
    if (!data) data = [];

    data.forEach(function (d) {
      d.color = d.percent_occupied >= 80 ? "#f8814f" : "#2490ef";
    });

    let can_write = 0;
    if (frappe.boot.user.can_write.indexOf("Putaway Rule") >= 0) {
      can_write = 1;
    }

    return {
      data: data,
      can_write: can_write,
    };
  }
  request(items) {
    const me = this;
    var dialog = new frappe.ui.Dialog({
      title: __("View/Request"),
      size: "extra-large",
      fields: [
        {
          fieldname: "schedule_date",
          label: __("Required By"),
          fieldtype: "Date",
          default: frappe.datetime.get_today(),
        },
        {
          fieldname: "material_request_type",
          label: __("Purpose"),
          fieldtype: "Select",
          default: "Purchase",
          options: [
            "Purchase",
            "Material Transfer",
            "Material Issue",
            "Manufacture",
            "Customer Provided",
          ],
          reqd: 1,
          change: () => {
            let material_request_type = dialog.get_value(
              "material_request_type"
            );
            dialog.get_field("set_from_warehouse").df.hidden =
              material_request_type != "Material Transfer";
            dialog.get_field("set_from_warehouse").refresh();
          },
        },
        {
          fieldname: "column_break_1",
          fieldtype: "Column Break",
        },
        {
          fieldname: "cost_center",
          label: __("Cost Center"),
          fieldtype: "Link",
          options: "Cost Center",
          default: me.pos_profile.cost_center || "",
        },
        {
          fieldname: "warehouse_section",
          label: __("Items"),
          fieldtype: "Section Break",
        },
        {
          fieldname: "set_from_warehouse",
          label: __("Set Source Warehouse"),
          fieldtype: "Link",
          options: "Warehouse",
          hidden: 1,
        },
        {
          fieldname: "column_break_2",
          fieldtype: "Column Break",
        },
        {
          fieldname: "set_warehouse",
          label: __("Set Target Warehouse"),
          fieldtype: "Link",
          options: "Warehouse",
          default: me.pos_profile.warehouse || ''
        },
        {
          fieldname: "items_section",
          fieldtype: "Section Break",
        },
        {
          fieldname: "items",
          label: __("Items"),
          fieldtype: "Table",
          cannot_add_rows: true,
          in_place_edit: true,
          cannot_delete_rows: true,
          data: items,
          fields: [
            {
              fieldname: "item_code",
              label: __("Item Code"),
              fieldtype: "Link",
              in_list_view: 1,
              reqd: 1,
              options: "Item",
              read_only: 1,
            },
            {
              fieldname: "item_name",
              label: __("Item Name"),
              fieldtype: "Data",
            },
            {
              fieldname: "qty",
              label: __("Quantity"),
              fieldtype: "Float",
              in_list_view: 1,
              reqd: 1,
            },
            {
              fieldname: "column_break_21",
              fieldtype: "Column Break",
            },
            {
              fieldname: "stock_uom",
              label: __("UOM"),
              fieldtype: "Link",
              in_list_view: 1,
              options: "UOM",
              read_only: 1,
            },
            {
              fieldname: "total_actual_qty",
              label: __("Total Actual Qty"),
              fieldtype: "Float",
              in_list_view: 1,
              read_only: 1,
            },
            {
              fieldname: "actual_qty",
              label: __("Actual Qty"),
              fieldtype: "Float",
              in_list_view: 1,
              read_only: 1,
            },
          ],
        },
      ],
    });
    dialog.fields_dict.items.$wrapper.find(".row-check").remove();
    dialog.fields_dict.items.$wrapper.find(".col-xs-2 ").css({
      flex: "1 0 20%",
      "max-width": "20%",
    });
    dialog.show();
    dialog.set_primary_action(__("Request"), function (value) {
      frappe.call({
        method: "ditech_core.ditech_core.qmr.make_material_request",
        freeze: true,
        args: value,
        callback: (r) => {
          if (r.message) {
            localStorage.removeItem("qmr_items");
            me.start = 0;
            me.items = [];
            me.refresh();
            frappe.show_alert({
              indicator: "green",
              message: __("Requested Successfully"),
            });
            frappe.utils.play_sound("submit");
            dialog.hide();
          }
        },
      });
    });
  }
};
