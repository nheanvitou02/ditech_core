ditech.POS.Controller = class {
  constructor(wrapper) {
    this.wrapper = $(wrapper).find(".layout-main-section");
    this.page = wrapper.page;
    this.load_display = null;
    this.check_opening_entry();
  }

  fetch_opening_entry() {
    return frappe.call("ditech_core.ditech_core.pos.check_opening_entry", {
      user: frappe.session.user,
    });
  }

  check_opening_entry() {
    this.fetch_opening_entry().then((r) => {
      if (r.message.length) {
        this.prepare_app_defaults(r.message[0]);
      } else {
        this.create_opening_voucher();
      }
    });
  }

  create_opening_voucher() {
    const me = this;
    const table_fields = [
      {
        fieldname: "mode_of_payment",
        fieldtype: "Link",
        in_list_view: 1,
        label: "Mode of Payment",
        options: "Mode of Payment",
        reqd: 1,
        columns: 4,
      },
      {
        fieldname: "opening_amount",
        fieldtype: "Float",
        in_list_view: 1,
        label: __("Amount"),
        columns: 3,
        precision: 2,
        change: function () {
          dialog.fields_dict.balance_details.df.data.some((d) => {
            if (d.idx == this.doc.idx) {
              d.opening_amount = this.value;
              dialog.fields_dict.balance_details.grid.refresh();
              return true;
            }
          });
        },
      },
      {
        fieldname: "custom_opening_amount",
        fieldtype: "Float",
        in_list_view: 1,
        label: __("Second Amount"),
        columns: 3,
        precision: 2,
        change: function () {
          dialog.fields_dict.balance_details.df.data.some((d) => {
            if (d.idx == this.doc.idx) {
              d.custom_opening_amount = this.value;
              dialog.fields_dict.balance_details.grid.refresh();
              return true;
            }
          });
        },
      },
    ];
    const fetch_pos_payment_methods = () => {
      const pos_profile = dialog.fields_dict.pos_profile.get_value();
      if (!pos_profile) return;
      frappe.db
        .get_doc("POS Profile", pos_profile)
        .then(({ payments, currency, custom_second_currency }) => {
          let child_table = dialog.fields_dict["balance_details"].grid;
          child_table.fields_map.opening_amount.label = `${__("Amount ({0})", [
            currency,
          ])}`;
          child_table.fields_map.custom_opening_amount.read_only = !Boolean(
            custom_second_currency
          );
          child_table.refresh();
          if (Boolean(custom_second_currency))
            child_table.fields_map.custom_opening_amount.label = `${__(
              "Amount ({0})",
              [custom_second_currency]
            )}`;
          dialog.fields_dict.balance_details.df.data = [];
          payments.forEach((pay) => {
            if (pay.default) {
              const { mode_of_payment } = pay;
              dialog.fields_dict.balance_details.df.data.push({
                mode_of_payment,
                opening_amount: 0.0,
                custom_opening_amount: 0.0,
              });
            }
          });
          dialog.fields_dict.balance_details.grid.refresh();
        });
    };
    const dialog = new frappe.ui.Dialog({
      title: __("Create POS Opening Entry"),
      static: true,
      size: "large",
      fields: [
        {
          fieldtype: "Link",
          label: __("Company"),
          default: frappe.defaults.get_default("company"),
          options: "Company",
          fieldname: "company",
          reqd: 1,
        },
        {
          fieldtype: "Link",
          label: __("POS Profile"),
          options: "POS Profile",
          fieldname: "pos_profile",
          reqd: 1,
          get_query: () => pos_profile_query(),
          onchange: () => fetch_pos_payment_methods(),
        },
        {
          fieldname: "balance_details",
          fieldtype: "Table",
          label: "Opening Balance Details",
          cannot_add_rows: false,
          in_place_edit: true,
          reqd: 1,
          data: [],
          fields: table_fields,
        },
      ],
      primary_action: async function ({
        company,
        pos_profile,
        balance_details,
      }) {
        if (!balance_details.length) {
          frappe.show_alert({
            message: __(
              "Please add Mode of payments and opening balance details."
            ),
            indicator: "red",
          });
          return frappe.utils.play_sound("error");
        }

        // filter balance details for empty rows
        balance_details = balance_details.filter((d) => d.mode_of_payment);

        const method = "ditech_core.ditech_core.pos.create_opening_voucher";
        const res = await frappe.call({
          method,
          args: { pos_profile, company, balance_details },
          freeze: true,
        });
        !res.exc && me.prepare_app_defaults(res.message);
        dialog.hide();
      },
      primary_action_label: __("Submit"),
    });
    dialog.show();
    const pos_profile_query = () => {
      return {
        query:
          "erpnext.accounts.doctype.pos_profile.pos_profile.pos_profile_query",
        filters: { company: dialog.fields_dict.company.get_value() },
      };
    };
  }

  async prepare_app_defaults(data) {
    this.pos_opening = data.name;
    this.company = data.company;
    this.pos_profile = data.pos_profile;
    this.pos_opening_time = data.period_start_date;
    this.item_stock_map = {};
    this.settings = {};
    this.key = data.pos_profile + "-" + data.name;
    this.is_service = data.is_service;

    frappe.db
      .get_value("Stock Settings", undefined, "allow_negative_stock")
      .then(({ message }) => {
        this.allow_negative_stock = flt(message.allow_negative_stock) || false;
      });

    frappe.call({
      method: "ditech_core.ditech_core.pos.get_pos_profile_data",
      args: { pos_profile: this.pos_profile },
      callback: (res) => {
        const profile = res.message;
        Object.assign(this.settings, profile);
        this.settings.customer_groups = profile.customer_groups.map(
          (group) => group.name
        );
        this.is_retail = this.settings.business_type == "Retail";
        this.make_app();
      },
    });
  }

  set_opening_entry_status() {
    this.page.set_title_sub(
      `<span class="indicator orange">
				<a class="text-muted" href="#Form/POS%20Opening%20Entry/${this.pos_opening}">
					Opened at ${moment(this.pos_opening_time).format("Do MMMM, h:mma")}
				</a>
			</span>`
    );
  }

  make_app() {
    this.prepare_dom();
    this.prepare_components();
    this.prepare_menu();
    this.is_retail && this.make_new_invoice();
    this.set_pos_profile_status();
    this.prepare_noti();
    this.load_clear_display();
  }

  prepare_dom() {
    this.wrapper.append(`<div class="pos-app"></div>`);
    this.$components_wrapper = this.wrapper.find(".pos-app");
  }

  prepare_components() {
    this.init_table_selector();
    this.init_item_selector();
    this.init_item_details();
    this.init_item_cart();
    this.init_payments();
    this.init_recent_order_list();
    this.init_order_summary();
    this.init_customer_order_list();
    this.init_customer_order_summary();
    this.init_item_kitchen();
    this.bind_events();
  }

  prepare_noti() {
    this.page.clear_inner_toolbar();
    this.page.add_inner_button(
      `<span class="noti-order-icon" title="${__("List Items Order")}"></span>`,
      () => {
        this.toggle_customer_order();
      }
    );
    this.load_noti_order();
    if (!this.is_retail) {
      this.page.add_inner_button(
        `<span class="noti-icon" title="${__("List Items Done")}"></span>`,
        () => {
          this.list_items();
        }
      );
      this.load_noti();
    }
    this.page.add_inner_button(
      `<span title="${__("Full Screen")}">
      <svg class="es-icon es-line icon-md" viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg">
        <g id="SVGRepo_bgCarrier" stroke-width="0"></g>
        <g id="SVGRepo_tracerCarrier" stroke-linecap="round" stroke-linejoin="round"></g>
        <g id="SVGRepo_iconCarrier">
          <path stroke='currentColor' d="m160 96.064 192 .192a32 32 0 0 1 0 64l-192-.192V352a32 32 0 0 1-64 0V96h64v.064zm0 831.872V928H96V672a32 32 0 1 1 64 0v191.936l192-.192a32 32 0 1 1 0 64l-192 .192zM864 96.064V96h64v256a32 32 0 1 1-64 0V160.064l-192 .192a32 32 0 1 1 0-64l192-.192zm0 831.872-192-.192a32 32 0 0 1 0-64l192 .192V672a32 32 0 1 1 64 0v256h-64v-.064z"></path>
        </g>
      </svg></span>`,
      () => {
        if (!document.fullscreenElement) {
          if (document.documentElement.requestFullscreen) {
            document.documentElement.requestFullscreen();
          } else if (document.documentElement.mozRequestFullScreen) {
            // Firefox
            document.documentElement.mozRequestFullScreen();
          } else if (document.documentElement.webkitRequestFullscreen) {
            // Chrome, Safari, Opera
            document.documentElement.webkitRequestFullscreen();
          } else if (document.documentElement.msRequestFullscreen) {
            // IE/Edge
            document.documentElement.msRequestFullscreen();
          }
        } else {
          if (document.exitFullscreen) {
            document.exitFullscreen();
          } else if (document.mozCancelFullScreen) {
            // Firefox
            document.mozCancelFullScreen();
          } else if (document.webkitExitFullscreen) {
            // Chrome, Safari, Opera
            document.webkitExitFullscreen();
          } else if (document.msExitFullscreen) {
            // IE/Edge
            document.msExitFullscreen();
          }
        }
      }
    );
  }

  load_noti_order(unseen = false) {
    let $button_noti_order = this.page.wrapper.find(
      ".page-actions .noti-order-icon"
    );
    $button_noti_order.html("");
    if (unseen) {
      $button_noti_order.html(
        `<span style="position: relative;"><div style="
                background: var(--red-500);
                height: 6px;
                width: 6px;
                border-radius: 50%;
                position: absolute;
                top: 0;
                right: 0;
            "></div>
            <svg class="icon icon-sm" aria-hidden="true">
          <use class="" href="#icon-assets"></use></svg></span>`
      );
    } else {
      $button_noti_order.html(
        `<span><svg class="icon icon-sm" aria-hidden="true">
          <use class="" href="#icon-assets"></use></svg></span>`
      );
    }
  }

  load_noti() {
    this.items_noti = [];
    let items_noti = JSON.parse(localStorage.getItem("items_noti"));
    let $button_noti = this.page.wrapper.find(".page-actions .noti-icon");
    $button_noti.html("");
    if (items_noti && items_noti.length > 0) {
      this.items_noti = items_noti;
      $button_noti.html(
        `<span style="position: relative;"><div style="
                background: var(--red-500);
                height: 6px;
                width: 6px;
                border-radius: 50%;
                position: absolute;
                top: 0;
                right: 0;
            "></div>
            <svg class="es-icon es-line icon-md" aria-hidden="true">
          <use class="" href="#icon-solid-success"></use></svg></span>`
      );
    } else {
      $button_noti.html(
        `<span><svg class="es-icon es-line icon-md" aria-hidden="true">
          <use class="" href="#icon-solid-success"></use></svg></span>`
      );
    }
  }

  list_items() {
    let me = this;
    let d = new frappe.ui.Dialog({
      title: "List Items Done",
      size: "large",
      fields: [
        {
          label: __("Items"),
          fieldname: "items",
          fieldtype: "Table",
          in_place_edit: true,
          cannot_add_rows: false,
          cannot_delete_rows: true,
          data: this.items_noti,
          fields: [
            {
              label: __("Table"),
              fieldname: "table",
              fieldtype: "Data",
              read_only: 1,
              in_list_view: 1,
            },
            {
              label: __("Item"),
              fieldname: "item_name",
              fieldtype: "Data",
              read_only: 1,
              in_list_view: 1,
            },
            {
              label: __("Qty"),
              fieldname: "qty",
              fieldtype: "Int",
              read_only: 1,
              in_list_view: 1,
            },
            {
              label: __("UOM"),
              fieldname: "uom",
              fieldtype: "Data",
              read_only: 1,
              in_list_view: 1,
            },
          ],
        },
      ],
      primary_action_label: __("Confirm"),
      primary_action() {
        d.hide();
        me.items_noti = [];
        localStorage.setItem("items_noti", JSON.stringify(me.items_noti));
        me.load_noti();
      },
    });
    d.wrapper
      .find(
        ".row-check, .grid-footer, [data-fieldname='items'] .grid-field > .control-label"
      )
      .hide();
    d.$wrapper.find(".modal-header, .modal-footer").css({ border: "none" });
    d.$wrapper
      .find(".modal-body")
      .css({ "padding-top": 0, "padding-bottom": 0 });
    d.show();
  }

  prepare_menu() {
    this.page.clear_menu();

    this.page.add_menu_item(
      __("Home"),
      () => frappe.set_route("/"),
      false,
      "Ctrl+H"
    );

    this.page.add_menu_item(
      __("Refresh"),
      () => location.reload(),
      false,
      "Ctrl+R"
    );

    !this.is_retail &&
      this.page.add_menu_item(
        __("Bar/Kitchen"),
        this.toggle_kitchen.bind(this),
        false,
        "Ctrl+B"
      );

    if (!this.is_service) {
      this.page.add_menu_item(
        __("Customer Facing Display"),
        this.show_second_display.bind(this),
        false,
        "Ctrl+D"
      );

      this.page.add_menu_item(
        __("Toggle Recent Orders"),
        this.toggle_recent_order.bind(this),
        false,
        "Ctrl+O"
      );

      this.is_retail &&
        this.page.add_menu_item(
          __("Open Form View"),
          this.open_form_view.bind(this),
          false,
          "Ctrl+F"
        );

      this.is_retail &&
        this.page.add_menu_item(
          __("Save as Draft"),
          this.save_draft_invoice.bind(this),
          false,
          "Ctrl+S"
        );

      this.page.add_menu_item(
        __("Close the POS"),
        this.close_pos.bind(this),
        false,
        "Shift+Ctrl+C"
      );
    }
  }

  open_form_view() {
    frappe.model.sync(this.frm.doc);
    frappe.set_route("Form", this.frm.doc.doctype, this.frm.doc.name);
  }

  toggle_recent_order() {
    const show = this.recent_order_list.$component.is(":hidden");
    if (this.is_retail && !show) {
      this.toggle_table(false);
      this.recent_order_list.toggle_component(show);
      this.order_summary.toggle_component(show);
      this.cart.toggle_checkout_btn(true);
    } else this.toggle_recent_order_list(show);
  }

  toggle_customer_order() {
    const show = this.customer_order_list.$component.is(":hidden");
    if (this.is_retail && !show) {
      this.toggle_table(false);
      this.customer_order_list.toggle_component(show);
      this.customer_order_summary.toggle_component(show);
      this.cart.toggle_checkout_btn(true);
    } else this.toggle_customer_order_list(show);
  }

  toggle_kitchen() {
    const show = this.item_kitchen.$component.is(":hidden");
    this.toggle_item_kitchen(show);
  }

  async save_draft_invoice() {
    if (!this.$components_wrapper.is(":visible")) return;

    if (this.frm.doc.items.length == 0) {
      frappe.show_alert({
        message: __("You must add atleast one item to save it as draft."),
        indicator: "red",
      });
      frappe.utils.play_sound("error");
      return;
    }

    this.frm.doc.payments.forEach((payment) => {
      payment.amount = 0;
      payment.base_amount = 0;
    });

    // await this.set_packed_items();

    this.frm
      .save(undefined, undefined, undefined, () => {
        frappe.show_alert({
          message: __("There was an error saving the document."),
          indicator: "red",
        });
        frappe.utils.play_sound("error");
      })
      .then(() => {
        frappe.run_serially([
          () => frappe.dom.freeze(),
          () => this.is_retail && this.make_new_invoice(),
          () => {
            if (this.is_retail) {
              this.cart.toggle_checkout_btn(true);
              this.toggle_table(false);
            } else {
              this.toggle_table(true);
              this.load_clear_display();
            }
          },
          () => frappe.dom.unfreeze(),
        ]);
      });
  }

  close_pos() {
    if (!this.$components_wrapper.is(":visible")) return;

    let voucher = frappe.model.get_new_doc("POS Closing Entry");
    voucher.pos_profile = this.pos_profile;
    voucher.user = frappe.session.user;
    voucher.company = this.company;
    voucher.pos_opening_entry = this.pos_opening;
    voucher.period_end_date = frappe.datetime.now_datetime();
    voucher.posting_date = frappe.datetime.now_date();
    voucher.posting_time = frappe.datetime.now_time();
    frappe.set_route("Form", "POS Closing Entry", voucher.name);
  }

  init_table_selector() {
    this.table_selector = new ditech.POS.TableSelector({
      wrapper: this.$components_wrapper,
      pos_profile: this.pos_profile,
      settings: this.settings,
      is_service: this.is_service,
      is_retail: this.is_retail,
      events: {
        table_selector: async (table_name) => {
          await this.make_new_invoice();
          this.frm.doc.custom_pos_table = table_name;
          this.cart.load_table();
          this.cart.toggle_checkout_btn(true);
          this.toggle_table(false);
        },
        add_view: (name) => {
          this.view_pos_inv(name);
        },
        render_actual_item_list: (items, $wrapper) =>
          this.render_actual_item_list(items, $wrapper),
        payment: async (name) => {
          this.frm = undefined;
          await this.make_new_invoice();
          this.get_payment(name);
        },
        get_frm: () => this.frm || {},
      },
    });
  }
  init_item_selector() {
    this.item_selector = new ditech.POS.ItemSelector({
      wrapper: this.$components_wrapper,
      pos_profile: this.pos_profile,
      settings: this.settings,
      is_retail: this.is_retail,
      events: {
        item_selected: (args) => {
          if (this.frm.doc.custom_is_invoice) return;
          if (
            this.settings.custom_guest_count &&
            this.frm.doc.custom_guest_number == 0
          ) {
            this.set_guest_number(args, 1);
            return;
          }
          this.on_cart_update(args);
          this.cart.last_item(args.item.item_code);
        },
        render_actual_item_list: (items, $wrapper) =>
          this.render_actual_item_list(items, $wrapper),
        get_frm: () => this.frm || {},
      },
    });
  }

  init_item_cart() {
    this.cart = new ditech.POS.ItemCart({
      wrapper: this.$components_wrapper,
      settings: this.settings,
      is_service: this.is_service,
      is_retail: this.is_retail,
      events: {
        get_frm: () => this.frm,

        table_selector: () => this.toggle_table(true),
        load_data_display: (data) => this.load_data_display(data),
        load_clear_display: () => this.load_clear_display(),
        set_guest_number: () =>
          this.set_guest_number(null, this.frm.doc.custom_guest_number),

        cart_item_clicked: (item) => {
          const item_row = this.get_item_from_frm(item);
          this.item_details.toggle_item_details_section(item_row);
        },

        load_doc: async (name) => {
          this.frm = undefined;
          await this.make_new_invoice();
          if (this.payment.$component.is(":hidden"))
            frappe.db.get_doc("POS Invoice", name).then((doc) => {
              frappe.run_serially([
                () => this.frm.refresh(name),
                () => this.frm.call("reset_mode_of_payments"),
                () => this.cart.load_invoice(),
                () => this.cart.toggle_checkout_btn(true),
              ]);
            });
          else this.get_payment(name);
        },

        numpad_event: (value, action) => this.update_item_field(value, action),

        checkout: () => this.save_and_checkout(),

        save_draft_invoice: () => this.save_draft_invoice(),

        edit_cart: () => this.payment.edit_cart(),

        customer_details_updated: (details) => {
          this.customer_details = details;
          // will add/remove LP payment method
          this.payment.render_loyalty_points_payment_mode();
        },
      },
    });
  }

  init_item_details() {
    this.item_details = new ditech.POS.ItemDetails({
      wrapper: this.$components_wrapper,
      settings: this.settings,
      is_service: this.is_service,
      is_retail: this.is_retail,
      events: {
        get_frm: () => this.frm,

        toggle_item_selector: (minimize) => {
          this.item_selector.resize_selector(minimize);
          this.cart.toggle_numpad(minimize);
        },

        get_packed_item: (item_code) => this.get_packed_item(item_code),

        form_updated: (item, field, value) => {
          const item_row = frappe.model.get_doc(item.doctype, item.name);
          if (item_row && item_row[field] != value) {
            const args = {
              field,
              value,
              item: this.item_details.current_item,
            };
            return this.on_cart_update(args);
          }

          return Promise.resolve();
        },

        highlight_cart_item: (item) => {
          const cart_item = this.cart.get_cart_item(item);
          this.cart.toggle_item_highlight(cart_item);
        },

        item_field_focused: (fieldname) => {
          this.cart.toggle_numpad_field_edit(fieldname);
        },
        set_value_in_current_cart_item: (selector, value) => {
          this.cart.update_selector_value_in_cart_item(
            selector,
            value,
            this.item_details.current_item
          );
        },
        clone_new_batch_item_in_frm: (batch_serial_map, item) => {
          // called if serial nos are 'auto_selected' and if those serial nos belongs to multiple batches
          // for each unique batch new item row is added in the form & cart
          Object.keys(batch_serial_map).forEach((batch) => {
            const item_to_clone = this.frm.doc.items.find(
              (i) => i.name == item.name
            );
            const new_row = this.frm.add_child("items", { ...item_to_clone });
            // update new serialno and batch
            new_row.batch_no = batch;
            new_row.serial_no = batch_serial_map[batch].join(`\n`);
            new_row.qty = batch_serial_map[batch].length;
            this.frm.doc.items.forEach((row) => {
              if (item.item_code === row.item_code) {
                this.update_cart_html(row);
              }
            });
          });
        },
        remove_item_from_cart: () => this.remove_item_from_cart(),
        get_item_stock_map: () => this.item_stock_map,
        close_item_details: () => this.close_item_details(),
        get_available_stock: (item_code, warehouse) =>
          this.get_available_stock(item_code, warehouse),
      },
    });
  }

  init_payments() {
    this.payment = new ditech.POS.Payment({
      wrapper: this.$components_wrapper,
      settings: this.settings,
      is_retail: this.is_retail,
      key: this.key,
      events: {
        get_frm: () => this.frm || {},

        get_customer_details: () => this.customer_details || {},

        toggle_other_sections: (show) => {
          if (show) {
            this.item_details.$component.is(":visible")
              ? this.item_details.$component.css("display", "none")
              : "";
            this.item_selector.toggle_component(false);
          } else {
            this.item_selector.toggle_component(true);
          }
        },

        load_after_invoice: () => {
          this.cart.load_invoice();
          this.cart.toggle_checkout_btn(false);
        },

        save_and_invoice: () => this.save_and_invoice(),

        submit_invoice: () => {
          this.frm.doc.custom_is_move = 0;
          this.frm.doc.custom_is_merge = 0;
          this.frm.doc.custom_is_split = 0;
          this.frm.save("Submit", null, null, null).then(async () => {
            this.load_clear_display();
            if (this.settings.custom_receipt_print_format)
              frappe.utils.print(
                this.frm.doc.doctype,
                this.frm.doc.name,
                this.settings.custom_receipt_print_format,
                this.frm.doc.letter_head,
                this.frm.doc.language || frappe.boot.lang
              );
            frappe.show_alert({
              indicator: "green",
              message: __("POS invoice {0} submitted successfully", [
                this.frm.doc.name,
              ]),
            });
            if (this.is_retail) {
              await this.make_new_invoice();
              this.toggle_components(false);
              this.cart.toggle_checkout_btn(true);
            }
            this.toggle_table(!this.is_retail);
          });
        },
      },
    });
  }

  init_recent_order_list() {
    this.recent_order_list = new ditech.POS.PastOrderList({
      wrapper: this.$components_wrapper,
      settings: this.settings,
      events: {
        open_invoice_data: (name) => {
          frappe.db.get_doc("POS Invoice", name).then((doc) => {
            this.order_summary.load_summary_of(doc);
          });
        },
        reset_summary: () =>
          this.order_summary.toggle_summary_placeholder(true),
      },
    });
  }

  init_order_summary() {
    this.order_summary = new ditech.POS.PastOrderSummary({
      wrapper: this.$components_wrapper,
      settings: this.settings,
      events: {
        get_frm: () => this.frm,
        process_return: (name) => {
          this.recent_order_list.toggle_component(false);
          frappe.db.get_doc("POS Invoice", name).then((doc) => {
            frappe.run_serially([
              () => this.make_return_invoice(doc),
              () => this.cart.load_invoice(),
              () => this.item_selector.toggle_component(true),
              () => this.cart.toggle_component(true),
            ]);
          });
        },
        edit_order: async (name) => {
          this.recent_order_list.toggle_component(false);
          this.view_pos_inv(name);
        },
        cencel_order: (name) => this.cencel_order(name),
        new_order: () => {
          frappe.run_serially([
            () => frappe.dom.freeze(),
            () => this.make_new_invoice(),
            () => {
              if (this.is_retail) {
                this.cart.toggle_checkout_btn(true);
                this.toggle_table(false);
              } else this.toggle_table(true);
            },
            () => frappe.dom.unfreeze(),
          ]);
        },
      },
    });
  }
  init_customer_order_list() {
    this.customer_order_list = new ditech.POS.CustomerOrderList({
      wrapper: this.$components_wrapper,
      settings: this.settings,
      events: {
        open_customer_invoice_data: (name) => {
          frappe.db.get_doc("Customer Order", name).then((doc) => {
            this.customer_order_summary.load_summary_of(doc);
          });
        },
        reset_summary: () =>
          this.customer_order_summary.toggle_summary_placeholder(true),
      },
    });
  }

  init_customer_order_summary() {
    this.customer_order_summary = new ditech.POS.CustomerOrderSummary({
      wrapper: this.$components_wrapper,
      settings: this.settings,
      events: {
        get_frm: () => this.frm,

        refresh_list: () => this.customer_order_list.refresh_list(),

        process_return: (name) => {
          this.recent_order_list.toggle_component(false);
          frappe.db.get_doc("Customer Order", name).then((doc) => {
            frappe.run_serially([
              () => this.make_return_invoice(doc),
              () => this.cart.load_invoice(),
              () => this.item_selector.toggle_component(true),
              () => this.cart.toggle_component(true),
            ]);
          });
        },
        edit_order: async (name) => {
          this.recent_order_list.toggle_component(false);
          this.view_pos_inv(name);
        },
        cencel_order: (name) => this.cencel_order(name),
        new_order: () => {
          frappe.run_serially([
            () => frappe.dom.freeze(),
            () => this.make_new_invoice(),
            () => {
              if (this.is_retail) {
                this.cart.toggle_checkout_btn(true);
                this.toggle_table(false);
              } else this.toggle_table(true);
            },
            () => frappe.dom.unfreeze(),
          ]);
        },
      },
    });
  }
  init_item_kitchen() {
    this.item_kitchen = new ditech.POS.ItemKitchen({
      wrapper: this.$components_wrapper,
      pos_profile: this.pos_profile,
      settings: this.settings,
      events: {},
    });
  }
  close_item_details() {
    this.item_details.toggle_item_details_section(null);
    this.cart.prev_action = null;
    this.cart.toggle_item_highlight();
  }
  get_payment(name) {
    frappe.db.get_doc("POS Invoice", name).then((doc) => {
      frappe.run_serially([
        () => this.frm.refresh(name),
        () => this.frm.call("reset_mode_of_payments"),
        () => this.cart.load_invoice(),
        () => this.cart.load_table(),
        () => this.cart.toggle_component(true),
        () => this.cart.toggle_checkout_btn(false),
        () => this.payment.checkout(),
      ]);
    });
  }

  bind_events() {
    this.page.$title_area.on("click", ".title-text", () => {
      !this.is_retail && this.toggle_table(true);
    });
    frappe.realtime.on(this.pos_profile, async (res) => {
      switch (res.type) {
        case "Refresh CO":
          const hide = this.customer_order_list.$component.is(":hidden");
          hide && this.load_noti_order(true);
          !hide && this.customer_order_list.refresh_list();
          frappe.show_alert(
            {
              indicator: "green",
              message: __("Customer ordered!"),
            },
            5
          );
          frappe.utils.play_sound("alert");
          break;
        case "Refresh Table":
          this.table_selector.set_search_value("");
          break;
        case "Refresh Kitchen":
          this.item_kitchen.load_items_data();
          if (res.data && res.data.is_noti && !this.is_retail) {
            this.items_noti.push(res.data);
            localStorage.setItem("items_noti", JSON.stringify(this.items_noti));
            this.load_noti();
            frappe.show_alert(
              {
                indicator: "green",
                message: __(
                  "The item <b>{0}</b> in <b>{1}</b> has been completed.",
                  [res.data.item_name, res.data.table]
                ),
              },
              5
            );
            frappe.utils.play_sound("alert");
          }
          break;
        default:
          break;
      }
    });
  }
  cencel_order(name) {
    let me = this;
    let d = new frappe.ui.Dialog({
      title: __("Why you want to cancel order <b>{0}</b>?", [name]),
      size: "small",
      static: false,
      fields: [
        {
          fieldname: "reason",
          options: "POS Reason",
          fieldtype: "Link",
          label: __("Reason"),
          reqd: 1,
          get_query: function () {
            return {
              filters: {
                disabled: 0,
              },
            };
          },
        },
      ],
      primary_action_label: "Save",
      primary_action(values) {
        frappe.call({
          method: "ditech_core.ditech_core.pos.cancel_invoice",
          freeze: true,
          args: {
            invoice: name,
            reason: values.reason,
          },
          callback: async () => {
            me.table_selector.set_search_value("");
            me.recent_order_list.refresh_list();
            d.hide();
          },
        });
      },
    });
    d.show();
  }

  toggle_item_kitchen(show) {
    this.toggle_components(!show);
    this.item_kitchen.toggle_component(show);
    this.table_selector.toggle_component(!show);
    this.recent_order_list.toggle_component(false);
    this.order_summary.toggle_component(false);
    this.customer_order_list.toggle_component(false);
    this.customer_order_summary.toggle_component(false);
  }
  toggle_recent_order_list(show) {
    this.toggle_components(!show);
    this.recent_order_list.toggle_component(show);
    this.order_summary.toggle_component(show);
    this.table_selector.toggle_component(!show);
    this.item_kitchen.toggle_component(false);
    this.customer_order_list.toggle_component(false);
    this.customer_order_summary.toggle_component(false);
  }
  toggle_customer_order_list(show) {
    show && this.load_noti_order();
    this.toggle_components(!show);
    this.customer_order_list.toggle_component(show);
    this.customer_order_summary.toggle_component(show);
    this.table_selector.toggle_component(!show);
    this.item_kitchen.toggle_component(false);
    this.recent_order_list.toggle_component(false);
    this.order_summary.toggle_component(false);
  }
  toggle_table(show) {
    this.toggle_components(!show);
    this.item_selector.toggle_component(!show);
    this.cart.toggle_component(!show);
    this.table_selector.toggle_component(show);
    if (show) {
      this.item_kitchen.toggle_component(false);
      this.recent_order_list.toggle_component(false);
      this.order_summary.toggle_component(false);
      this.customer_order_list.toggle_component(false);
      this.customer_order_summary.toggle_component(false);
    }
  }
  toggle_components(show) {
    if (!show) {
      this.cart.toggle_customer_info(false);
      this.close_item_details();
    }
    !show
      ? this.item_details.toggle_component(false) ||
        this.payment.toggle_component(false) ||
        this.cart.toggle_component(false) ||
        this.item_selector.toggle_component(false)
      : "";
  }

  make_new_invoice() {
    return frappe.run_serially([
      () => frappe.dom.freeze(),
      () => this.make_sales_invoice_frm(),
      () => this.set_pos_profile_data(),
      () => this.cart.load_invoice(),
      () => frappe.dom.unfreeze(),
    ]);
  }

  make_sales_invoice_frm() {
    const doctype = "POS Invoice";
    return new Promise((resolve) => {
      if (this.frm) {
        this.frm = this.get_new_frm(this.frm);
        this.frm.doc.items = [];
        this.frm.doc.is_pos = 1;
        this.frm.doc.pos_profile = this.pos_profile;
        resolve();
      } else {
        frappe.model.with_doctype(doctype, () => {
          this.frm = this.get_new_frm();
          this.frm.doc.items = [];
          this.frm.doc.is_pos = 1;
          this.frm.doc.pos_profile = this.pos_profile;
          resolve();
        });
      }
    });
  }

  get_new_frm(_frm) {
    const doctype = "POS Invoice";
    const page = $("<div>");
    const frm = _frm || new frappe.ui.form.Form(doctype, page, false);
    const name = frappe.model.make_new_doc_and_get_name(doctype, true);
    frm.refresh(name);

    return frm;
  }

  async make_return_invoice(doc) {
    frappe.dom.freeze();
    this.frm = this.get_new_frm(this.frm);
    this.frm.doc.items = [];
    return frappe.call({
      method:
        "erpnext.accounts.doctype.pos_invoice.pos_invoice.make_sales_return",
      args: {
        source_name: doc.name,
        target_doc: this.frm.doc,
      },
      callback: (r) => {
        frappe.model.sync(r.message);
        frappe.get_doc(
          r.message.doctype,
          r.message.name
        ).__run_link_triggers = false;
        this.set_pos_profile_data().then(() => {
          frappe.dom.unfreeze();
        });
      },
    });
  }

  set_pos_profile_data() {
    if (this.company && !this.frm.doc.company)
      this.frm.doc.company = this.company;
    if (
      (this.pos_profile && !this.frm.doc.pos_profile) |
      (this.frm.doc.is_return && this.pos_profile != this.frm.doc.pos_profile)
    ) {
      this.frm.doc.pos_profile = this.pos_profile;
    }

    if (!this.frm.doc.company) return;

    return this.frm.trigger("set_pos_data");
  }

  set_pos_profile_status() {
    this.page.set_indicator(this.pos_profile, "blue");
  }

  async on_cart_update(args) {
    frappe.dom.freeze();
    let item_row = undefined;
    try {
      let { field, value, item } = args;
      item_row = this.get_item_from_frm(item);
      const item_row_exists = !$.isEmptyObject(item_row);

      const from_selector = field === "qty" && value === "+1";
      if (from_selector) value = flt(item_row.stock_qty) + flt(value);

      if (item_row_exists) {
        if (field === "qty") value = flt(value);

        if (
          ["qty", "conversion_factor"].includes(field) &&
          value > 0 &&
          !this.allow_negative_stock
        ) {
          const qty_needed =
            field === "qty"
              ? value * item_row.conversion_factor
              : item_row.qty * value;
          await this.check_stock_availability(
            item_row,
            qty_needed,
            this.frm.doc.set_warehouse || this.settings.warehouse
          );
        }

        if (this.is_current_item_being_edited(item_row) || from_selector) {
          await frappe.model.set_value(
            item_row.doctype,
            item_row.name,
            field,
            value
          );
          this.update_cart_html(item_row);
        }
      } else {
        if (!this.frm.doc.customer)
          return this.raise_customer_selection_alert();

        const { item_code, batch_no, serial_no, rate, uom } = item;

        if (!item_code) return;

        const new_item = { item_code, batch_no, rate, uom, [field]: value };

        if (serial_no) {
          await this.check_serial_no_availablilty(
            item_code,
            this.frm.doc.set_warehouse || this.settings.warehouse,
            serial_no
          );
          new_item["serial_no"] = serial_no;
        }

        new_item["use_serial_batch_fields"] = 1;
        if (field === "serial_no")
          new_item["qty"] = value.split(`\n`).length || 0;

        item_row = this.frm.add_child("items", new_item);

        if (field === "qty" && value !== 0 && !this.allow_negative_stock) {
          const qty_needed = value * item_row.conversion_factor;
          await this.check_stock_availability(
            item_row,
            qty_needed,
            this.frm.doc.set_warehouse || this.settings.warehouse
          );
        }

        await this.trigger_new_item_events(item_row);

        this.update_cart_html(item_row);

        if (this.item_details.$component.is(":visible"))
          this.edit_item_details_of(item_row);

        if (
          this.check_serial_batch_selection_needed(item_row) &&
          !this.item_details.$component.is(":visible")
        )
          this.edit_item_details_of(item_row);
      }
    } catch (error) {
      console.log(error);
    } finally {
      frappe.dom.unfreeze();
      return item_row; // eslint-disable-line no-unsafe-finally
    }
  }

  raise_customer_selection_alert() {
    frappe.dom.unfreeze();
    frappe.show_alert({
      message: __("You must select a customer before adding an item."),
      indicator: "orange",
    });
    frappe.utils.play_sound("error");
  }

  get_item_from_frm({ name, item_code, batch_no, uom, rate }) {
    let item_row = null;
    if (name) {
      item_row = this.frm.doc.items.find((i) => i.name == name);
    } else {
      // if item is clicked twice from item selector
      // then "item_code, batch_no, uom, rate" will help in getting the exact item
      // to increase the qty by one
      const has_batch_no = batch_no !== "null" && batch_no !== null;
      item_row = this.frm.doc.items.find(
        (i) =>
          i.item_code === item_code &&
          (!has_batch_no || (has_batch_no && i.batch_no === batch_no)) &&
          i.uom === uom &&
          i.rate === flt(rate) &&
          i.__islocal
      );
    }

    return item_row || {};
  }

  edit_item_details_of(item_row) {
    this.item_details.toggle_item_details_section(item_row);
  }

  is_current_item_being_edited(item_row) {
    return item_row.name == this.item_details.current_item.name;
  }

  update_cart_html(item_row, remove_item) {
    this.cart.update_item_html(item_row, remove_item);
    this.cart.update_totals_section(this.frm);
  }

  check_serial_batch_selection_needed(item_row) {
    // right now item details is shown for every type of item.
    // if item details is not shown for every item then this fn will be needed
    const serialized = item_row.has_serial_no;
    const batched = item_row.has_batch_no;
    const no_serial_selected = !item_row.serial_no;
    const no_batch_selected = !item_row.batch_no;

    if (
      (serialized && no_serial_selected) ||
      (batched && no_batch_selected) ||
      (serialized && batched && (no_batch_selected || no_serial_selected))
    ) {
      return true;
    }
    return false;
  }

  async trigger_new_item_events(item_row) {
    await this.frm.script_manager.trigger(
      "item_code",
      item_row.doctype,
      item_row.name
    );
    await this.frm.script_manager.trigger(
      "qty",
      item_row.doctype,
      item_row.name
    );
  }

  async check_stock_availability(item_row, qty_needed, warehouse) {
    const resp = (await this.get_available_stock(item_row.item_code, warehouse))
      .message;
    const available_qty = resp[0];
    const is_stock_item = resp[1];

    frappe.dom.unfreeze();
    const bold_uom = item_row.uom.bold();
    const bold_item_code = item_row.item_code.bold();
    const bold_warehouse = warehouse.bold();
    const bold_available_qty = available_qty.toString().bold();
    if (!(available_qty > 0)) {
      if (is_stock_item) {
        frappe.model.clear_doc(item_row.doctype, item_row.name);
        frappe.throw({
          title: __("Not Available"),
          message: __("Item Code: {0} is not available under warehouse {1}.", [
            bold_item_code,
            bold_warehouse,
          ]),
        });
      } else {
        return;
      }
    } else if (is_stock_item && available_qty < qty_needed) {
      frappe.throw({
        message: __(
          "Stock quantity not enough for Item Code: {0} under warehouse {1}. Available quantity {2} {3}.",
          [bold_item_code, bold_warehouse, bold_available_qty, bold_uom]
        ),
        indicator: "orange",
      });
      frappe.utils.play_sound("error");
    }
    frappe.dom.freeze();
  }

  async check_serial_no_availablilty(item_code, warehouse, serial_no) {
    const method =
      "erpnext.stock.doctype.serial_no.serial_no.get_pos_reserved_serial_nos";
    const args = { filters: { item_code, warehouse } };
    const res = await frappe.call({ method, args });

    if (res.message.includes(serial_no)) {
      frappe.throw({
        title: __("Not Available"),
        message: __(
          "Serial No: {0} has already been transacted into another POS Invoice.",
          [serial_no.bold()]
        ),
      });
    }
  }

  get_available_stock(item_code, warehouse) {
    const me = this;
    return frappe.call({
      method:
        "erpnext.accounts.doctype.pos_invoice.pos_invoice.get_stock_availability",
      args: {
        item_code: item_code,
        warehouse: warehouse,
      },
      callback(res) {
        if (!me.item_stock_map[item_code]) me.item_stock_map[item_code] = {};
        me.item_stock_map[item_code][warehouse] = res.message;
      },
    });
  }

  update_item_field(value, field_or_action) {
    if (field_or_action === "checkout") {
      this.item_details.toggle_item_details_section(null);
    } else if (field_or_action === "remove") {
      this.remove_item_from_cart();
    } else {
      const field_control = this.item_details[`${field_or_action}_control`];
      if (!field_control) return;
      field_control.set_focus();
      value != "" &&
        !field_control?.df.read_only &&
        field_control.set_value(value);
    }
  }

  remove_item_from_cart() {
    const me = this;
    const { doctype, name, current_item, item_row } = me.item_details;
    const doc = me.frm.doc;
    const items = doc.items.filter((item) => !item.__islocal);
    if (
      !item_row.__islocal &&
      items.length == 1 &&
      item_row.qty == 1 &&
      !this.is_retail
    ) {
      frappe.show_alert({
        indicator: "red",
        message: __("Cannot item empty"),
      });
      frappe.utils.play_sound("error");
      return;
    }
    if (
      item_row.custom_pos_status == "Done" ||
      (!item_row.__islocal && !this.is_retail)
    )
      return;

    frappe.dom.freeze();
    return frappe.model
      .set_value(doctype, name, "qty", 0)
      .then(() => {
        frappe.model.clear_doc(doctype, name);
        me.update_cart_html(current_item, true);
        me.item_details.toggle_item_details_section(null);
        frappe.dom.unfreeze();
      })
      .catch((e) => console.log(e));
  }

  async save_and_checkout() {
    if (this.frm.is_dirty()) {
      let save_error = false;

      this.frm.doc.payments.forEach((payment) => {
        payment.amount = 0;
        payment.base_amount = 0;
      });

      // await this.set_packed_items();

      await this.frm.save(null, null, null, () => (save_error = true));
      // only move to payment section if save is successful
      !save_error && this.payment.checkout();
      // show checkout button on error
      save_error &&
        setTimeout(() => {
          this.cart.toggle_checkout_btn(true);
        }, 300); // wait for save to finish
    } else {
      this.payment.checkout();
    }
  }
  async save_and_invoice() {
    if (this.frm.is_dirty()) {
      await this.frm.save(null, null, null, null);
      setTimeout(() => {
        return;
      }, 300);
    }
    return;
  }
  get_packed_item(item_code) {
    return frappe.call({
      method: "ditech_core.ditech_core.pos.get_packed_item",
      freeze: true,
      args: {
        item_code: item_code,
      },
    });
  }
  async set_packed_items() {
    let packed_items = [];
    for (const item of this.frm.doc.items) {
      if (item.packed_items) {
        packed_items = [...packed_items, ...item.packed_items];
      } else {
        let packed = await this.get_packed_item(item.item_code).then(
          (r) => r.message || []
        );
        packed_items = [...packed_items, ...packed];
      }
    }
    this.frm.doc.packed_items = packed_items;
  }
  async view_pos_inv(name) {
    this.frm = undefined;
    await this.make_new_invoice();
    this.get_pos_inv(name);
  }
  get_pos_inv(name) {
    frappe.db.get_doc("POS Invoice", name).then((doc) => {
      frappe.run_serially([
        () => this.frm.refresh(name),
        () => this.frm.call("reset_mode_of_payments"),
        () => this.cart.load_invoice(),
        () => !this.is_retail && this.cart.load_table(),
        () => this.cart.toggle_checkout_btn(true),
        () => this.toggle_table(false),
      ]);
    });
  }
  show_second_display() {
    const url = `${window.location.origin}/customer_facing_display?key=${this.pos_profile}`;
    window.open(
      url,
      "New Window",
      `toolbar=no, location=no, directories=no, status=no, menubar=no, scrollbars=no, resizable=no, fullscreen=yes`
    );
  }
  load_data_display(data) {
    if (!this.is_service) {
      let me = this;
      clearTimeout(me.load_display);
      me.load_display = setTimeout(
        () =>
          frappe.call({
            method: "ditech_core.ditech_core.pos.load_data_display",
            args: {
              data: data,
            },
          }),
        300
      );
    }
  }
  load_clear_display() {
    let data = {
      items: [],
      total_item_qty: 0,
      net_total: 0,
      grand_total: 0,
      change_amount: 0,
      taxes: [],
      image: "",
      currency: this.settings.currency,
      second_currency: this.settings.custom_second_currency,
      exchange_rate: this.settings.exchange_rate,
      timeleft: 0,
    };
    if (!this.is_service) {
      clearTimeout(this.load_display);
      this.load_display = setTimeout(
        () =>
          frappe.call({
            method: "ditech_core.ditech_core.pos.load_data_display",
            args: {
              data: data,
            },
          }),
        300
      );
    }
  }
  render_actual_item_list(items, $wrapper) {
    $wrapper.css({
      display: items.length > 0 ? "flex" : "none",
    });
    $wrapper.html("");
    items.forEach((item) => {
      const item_html = this.get_actual_item_html(item);
      $wrapper.append(item_html);
    });
  }

  get_actual_item_html(item) {
    const me = this;
    const { actual_qty, uom } = item;
    let indicator_color;
    let qty_to_display = actual_qty;

    if (item.is_stock_item) {
      indicator_color =
        actual_qty > 10 ? "green" : actual_qty <= 0 ? "red" : "orange";

      if (Math.round(qty_to_display) > 999) {
        qty_to_display = Math.round(qty_to_display) / 1000;
        qty_to_display = qty_to_display.toFixed(1) + "K";
      }
    } else {
      indicator_color = "";
      qty_to_display = "";
    }

    return `<div class="actual-item-wrapper" data-item-code="${escape(
      item.item_code
    )}" title="${item.item_name}">
          <div class="item-detail">
            <div class="item-name">
              ${frappe.ellipsis(item.item_name, 18)}
            </div>
          </div>
          <div>
							<span class="indicator-pill whitespace-nowrap ${indicator_color}">${qty_to_display}</span>
					</div>
        </div>`;
  }
  set_guest_number(args = null, guest_number) {
    const frm = this.frm;
    const me = this;
    var d = new frappe.ui.Dialog({
      title: __("How many guests?"),
      size: "small",
      static: false,
      fields: [
        {
          fieldname: "guest",
          fieldtype: "Int",
          label: __("Guest Number"),
          reqd: 1,
          default: guest_number,
        },
      ],
      primary_action_label: "Save",
      primary_action(values) {
        if (values.guest == 0) {
          frappe.msgprint("Guest Number cannot be 0!");
          return;
        }
        frm.set_value("custom_guest_number", values.guest);
        me.cart.update_customer_section();
        args && me.on_cart_update(args);
        me.cart.toggle_customer_info(false);
        d.hide();
      },
    });
    d.fields_dict.guest.toggle_label(false);
    d.$wrapper.find(".modal-dialog").css("width", "auto");
    d.$wrapper.find(".modal-header, .modal-footer").css({ border: "none" });
    d.$wrapper
      .find(".modal-body")
      .css({ "padding-top": "2px", "padding-bottom": 0 });
    d.show();
  }
};
