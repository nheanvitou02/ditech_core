ditech.POS.TableSelector = class {
  constructor({
    wrapper,
    events,
    settings,
    pos_profile,
    is_service,
    is_retail,
  }) {
    this.wrapper = wrapper;
    this.events = events;
    this.pos_profile = pos_profile;
    this.settings = settings;
    this.is_service = is_service;
    this.is_retail = is_retail;

    this.init_component();

    this.$component.css("display", !is_retail ? "block" : "none");
  }

  init_component() {
    this.prepare_dom();
    this.make_search_bar();
    this.load_tables_data();
    this.bind_events();
  }

  prepare_dom() {
    this.wrapper.append(
      `<section class="table-selector">
        <div class="actual-items-container"></div>
				<div class="filter-section">
					<div class="label">${__("All Tables")}</div>
					<div class="search-field"></div>
					<div class="floor-field"></div>
					<div class="status-field"></div>
				</div>
				<div class="tables-container"></div>
			</section>`
    );

    this.$component = this.wrapper.find(".table-selector");
    this.$tables_container = this.$component.find(".tables-container");
    this.$actual_items_container = this.$component.find(
      ".actual-items-container"
    );
  }

  async load_tables_data() {
    this.get_tables({}).then(({ message }) => {
      this.render_table_list(message.tables);
      this.events.render_actual_item_list(
        message.actual_items,
        this.$actual_items_container
      );
    });
  }

  get_tables({ start = 0, page_length = 100, search_term = "" }) {
    let { floor, status, pos_profile } = this;

    return frappe.call({
      method: "ditech_core.ditech_core.pos.get_tables",
      freeze: true,
      args: { start, page_length, status, floor, search_term, pos_profile },
    });
  }

  render_table_list(tables) {
    this.$tables_container.html("");
    tables.forEach((table) => {
      const table_html = this.get_table_html(table);
      this.$tables_container.append(table_html);
    });
  }

  get_table_html(table) {
    let indicator_color =
      table.status == "Occupied" || table.status == "Merged"
        ? "occupy"
        : table.status == "Invoiced"
        ? "invoice"
        : table.status == "Paid"
        ? "paid"
        : "";
    let body_actions = "";
    let actions = [
      {
        label: __("Add/View"),
        fieldname: "add",
        icon: "icon-add",
        class: "add",
        status: ["Occupied", "Merged", "Split"],
      },
      {
        label: __("Move"),
        fieldname: "move",
        class: "move",
        icon: "icon-change",
        status: ["Occupied", "Invoiced", "Merged"],
      },
      {
        label: __("Merge"),
        fieldname: "merge",
        class: "merge",
        icon: "icon-collapse",
        status: ["Occupied", "Invoiced", "Merged"],
      },
      {
        label: __("Unmerge"),
        fieldname: "unmerge",
        class: "unmerge",
        icon: "icon-expand",
        status: ["Merged"],
      },
      {
        label: __("Split"),
        fieldname: "split",
        class: "split",
        icon: "icon-file",
        status: ["Occupied", "Invoiced", "Merged", "Split", "Split+Invoiced"],
      },
      {
        label: __("Cancel Order"),
        fieldname: "cancel",
        class: "cancel",
        icon: "icon-solid-error",
        status: ["Occupied", "Merged", "Split"],
      },
      {
        label: __("Payment"),
        fieldname: "payment",
        class: "payment",
        icon: "icon-solid-success",
        status: ["Occupied", "Invoiced", "Merged", "Split", "Split+Invoiced"],
      },
      {
        label: __("Available"),
        fieldname: "available",
        class: "available",
        icon: "icon-solid-success",
        status: ["Paid"],
      },
    ];
    actions.forEach((ac) => {
      let status = table.status;
      if (table.invoice_split && status == "Invoiced") status = "Split+Invoiced";
      else if (table.invoice_split) status = "Split";
      if (ac.status.includes(status)) {
        body_actions += `<li>
							<a class="grey-link dropdown-item ${
                ac.class
              }" href="#" onclick="return false;" data-invoice-name="${escape(
          table.pos_invoice || ""
        )}" data-table-name="${escape(table.name)}" data-table-label="${escape(
          table.label
        )}">
								<span class="menu-item-icon"><svg class="icon  icon-md" style="" aria-hidden="true">
										<use class="" href="#${ac.icon}"></use>
									</svg></span>
								<span class="menu-item-label" data-label="${__(ac.label)}">
								<span>${__(ac.label)}</span></span>
							</a>
						</li>`;
      }
    });
    let action = "";
    if (body_actions && !this.is_service)
      action = `
				<button type="button" class="btn btn-default btn-lg btn-block ellipsis table-wrapper ${indicator_color}"
						data-toggle="dropdown" aria-expanded="true" data-table-name="${escape(
              table.name
            )}" title="${table.label}">
						${frappe.ellipsis(table.label, 18)}
				</button>
				<ul class="dropdown-menu" role="menu" x-placement="bottom-start"
						style="position: absolute; transform: translate3d(274px, 28px, 0px); top: 0px; left: 0px; will-change: transform;">
						${body_actions}
				</ul>`;
    else
      action = `
				<button type="button" class="btn btn-default btn-lg btn-block ellipsis table-wrapper tb-click ${indicator_color}"
				data-table-name="${escape(table.name)}" data-invoice-name="${escape(
        table.pos_invoice || ""
      )}" title="${table.label}">
						${frappe.ellipsis(table.label, 18)}
				</button>`;

    return `<div class="custom-btn-group">${action}</div>`;
  }

  make_search_bar() {
    const me = this;
    this.$component.find(".search-field").html("");
    this.$component.find(".floor-field").html("");
    this.$component.find(".status-field").html("");
    this.search_field = frappe.ui.form.make_control({
      df: {
        label: __("Search"),
        fieldtype: "Data",
        placeholder: __("Search by label"),
      },
      parent: this.$component.find(".search-field"),
      render_input: true,
    });
    this.floor_field = frappe.ui.form.make_control({
      df: {
        label: __("Floor"),
        fieldtype: "Link",
        options: "POS Floor",
        placeholder: __("Select floor"),
        onchange: function () {
          me.floor = this.value;
          !me.floor;
          me.filter_tables();
        },
        get_query: function () {
          return {
            filters: {
              pos_profile: me.settings.name,
            },
          };
        },
      },
      parent: this.$component.find(".floor-field"),
      render_input: true,
    });
    this.status_field = frappe.ui.form.make_control({
      df: {
        label: __("Status"),
        fieldtype: "Select",
        options: ["", "Opened", "Occupied", "Invoiced", "Merged"],
        placeholder: __("Select status"),
        onchange: function () {
          me.status = this.value;
          !me.status;
          me.filter_tables();
        },
      },
      parent: this.$component.find(".status-field"),
      render_input: true,
    });
    this.search_field.toggle_label(false);
    this.floor_field.toggle_label(false);
    this.status_field.toggle_label(false);

    this.attach_clear_btn();
  }

  attach_clear_btn() {
    this.search_field.$wrapper.find(".control-input").append(
      `<span class="link-btn">
				<a class="btn-open no-decoration" title="${__("Clear")}">
					${frappe.utils.icon("close", "sm")}
				</a>
			</span>`
    );

    this.$clear_search_btn = this.search_field.$wrapper.find(".link-btn");

    this.$clear_search_btn.on("click", "a", () => {
      this.set_search_value("");
      this.search_field.set_focus();
    });
  }

  set_search_value(value) {
    $(this.search_field.$input[0]).val(value).trigger("input");
  }
  filter_tables({ search_term = "" } = {}) {
    if (search_term) {
      search_term = search_term.toLowerCase();

      // memoize
      this.search_index = this.search_index || {};
      if (this.search_index[search_term]) {
        const tables = this.search_index[search_term];
        this.tables = tables;
        this.render_table_list(tables);
        return;
      }
    }

    this.get_tables({ search_term }).then(({ message }) => {
      // eslint-disable-next-line no-unused-vars
      const { tables, actual_items } = message;
      this.tables = tables;
      this.render_table_list(tables);
      this.events.render_actual_item_list(
        actual_items,
        this.$actual_items_container
      );
    });
  }

  bind_events() {
    const me = this;

    this.$component.on("click", ".tb-click", function () {
      const $table = $(this);
      const table_name = unescape($table.attr("data-table-name"));
      const invoice_name = unescape($table.attr("data-invoice-name"));

      me.is_service && invoice_name
        ? me.events.add_view(invoice_name)
        : me.events.table_selector(table_name);
    });

    this.$component.on("click", ".add", function () {
      const $table = $(this);
      const invoice_name = unescape($table.attr("data-invoice-name"));
      me.events.add_view(invoice_name);
    });
    this.$component.on("click", ".move", function () {
      const $table = $(this);
      const table_name = unescape($table.attr("data-table-name"));
      me.move_items(table_name);
    });
    this.$component.on("click", ".merge", function () {
      const $table = $(this);
      const invoice_name = unescape($table.attr("data-invoice-name"));
      const table_name = unescape($table.attr("data-table-name"));
      const lable_label = unescape($table.attr("data-table-label"));
      me.merge_table(invoice_name, table_name, lable_label);
    });

    this.$component.on("click", ".unmerge", function () {
      const $table = $(this);
      const table_name = unescape($table.attr("data-table-name"));
      me.unmerge_table(table_name);
    });

    this.$component.on("click", ".split", function () {
      const $table = $(this);
      const invoice = unescape($table.attr("data-invoice-name"));
      const table = unescape($table.attr("data-table-name"));
      me.split_invoice(invoice, table);
    });

    this.$component.on("click", ".cancel", function () {
      const $table = $(this);
      const invoice = unescape($table.attr("data-invoice-name"));
      const table = unescape($table.attr("data-table-name"));
      me.cancel(invoice, table);
    });

    this.$component.on("click", ".available", function () {
      const $table = $(this);
      const table = unescape($table.attr("data-table-name"));
      const lable_label = unescape($table.attr("data-table-label"));
      frappe.confirm(
        __("Available table <strong>{0}</strong>?", [lable_label]),
        () => {
          frappe.call({
            method: "ditech_core.ditech_core.pos.available_table",
            freeze: true,
            args: { table: table },
            callback: () => {
              me.set_search_value("");
            },
          });
        }
      );
    });
    this.$component.on("click", ".payment", function () {
      const $table = $(this);
      const invoice_name = unescape($table.attr("data-invoice-name"));
      me.events.payment(invoice_name);
      me.toggle_component(false);
    });

    this.search_field.$input.on("input", (e) => {
      clearTimeout(this.last_search);
      this.last_search = setTimeout(() => {
        const search_term = e.target.value;
        this.filter_tables({ search_term });
      }, 300);

      this.$clear_search_btn.toggle(Boolean(this.search_field.$input.val()));
    });

    this.search_field.$input.on("focus", () => {
      this.$clear_search_btn.toggle(Boolean(this.search_field.$input.val()));
    });
  }
  merge_table(invoice, table, label) {
    const me = this;
    frappe.db.get_doc("DocType", "POS Table Detail").then(() => {
      const dialog = new frappe.ui.Dialog({
        title: __("Merge <b>{0}</b> with:", [label]),
        fields: [
          {
            label: __("Table"),
            fieldtype: "Table MultiSelect",
            options: "POS Table Detail",
            fieldname: "tables",
            reqd: 1,
            get_query: () => {
              return {
                filters: {
                  name: ["!=", table],
                  pos_profile: this.pos_profile,
                  status: ["in", "Occupied", "Invoiced"],
                },
              };
            },
          },
          {
            fieldname: "action",
            fieldtype: "HTML",
            label: "Content",
          },
        ],
      });
      dialog.fields_dict.action.$wrapper.html(`
          <div class="flex merge-btn" style="justify-content: end;">
              <div class="save-btn">
                ${__("Save")}
              </div>
          </div>
        `);
      dialog.show();
      dialog.fields_dict.action.$wrapper.on("click", ".save-btn", () => {
        let tb = dialog.get_value("tables");
        if (tb.length == 0) {
          frappe.msgprint("Table is not empty!");
          return;
        }
        frappe.call({
          method: "ditech_core.ditech_core.pos.merge_table",
          freeze: true,
          args: {
            invoice_name: invoice,
            table1: table,
            table2: tb,
          },
          callback: () => {
            me.set_search_value("");
            dialog.hide();
          },
        });
      });
    });
  }
  unmerge_table(table_name) {
    let me = this;
    frappe.confirm(__("Are you sure you want to unmerge the table?"), () => {
      frappe.call({
        method: "ditech_core.ditech_core.pos.unmerge_table",
        freeze: true,
        args: { table_name },
        callback: () => {
          me.set_search_value("");
        },
      });
    });
  }
  move_items(table) {
    const currency = this.settings.currency;
    const me = this;
    var first_table_items = [];
    var second_table_items = [];
    var default_table = table;
    let old_second_table = "";
    var dialog = new frappe.ui.Dialog({
      title: __("Move or Transfer Items"),
      size: "extra-large",
      fields: [
        {
          fieldname: "first_table",
          fieldtype: "Link",
          options: "POS Table",
          label: "Table",
          default: default_table,
          change: async () => {
            await on_change_first_table();
            dialog.get_value("second_table") &&
              dialog.set_value("second_table", "");
          },
          get_query: () => {
            return {
              filters: {
                pos_profile: this.pos_profile,
              },
            };
          },
        },
        {
          fieldname: "column_break_1",
          fieldtype: "Column Break",
        },
        {
          fieldname: "second_table",
          fieldtype: "Link",
          options: "POS Table",
          label: "Table",
          change: async () => {
            let table_name = dialog.get_value("second_table");
            if (table_name != old_second_table) {
              old_second_table = table_name;
              let items = await get_items_table(table_name);
              second_table_items = items;
              get_items_second_table(items);
              on_change_first_table();
            }
          },
          get_query: () => {
            return {
              filters: {
                name: ["!=", default_table],
                pos_profile: this.pos_profile,
              },
            };
          },
        },
        {
          fieldname: "section_break_1",
          fieldtype: "Section Break",
          hide_border: 1,
        },
        {
          fieldname: "content_item",
          fieldtype: "HTML",
          label: "Content",
        },
      ],
    });

    dialog.set_value("first_table", default_table);

    dialog.$wrapper.find(".modal-dialog").css({ width: "992px" });

    dialog.fields_dict.content_item.$wrapper.html(`
      <div class="dialog-move-items">
        <div class="dialog-item-container">
          <div class="abs-item-container">
            <div class="items-section items-first-table"></div>
          </div>
          <div class="actions-item-container">
            <div class="btn right-btn">
              <svg class="icon icon-md" style="" aria-hidden="true">
                  <use class="" href="#icon-right"></use>
              </svg>
            </div>
            <div class="btn rights-btn">
              <svg class="icon icon-md" style="" aria-hidden="true">
                  <use class="" href="#icon-sidebar-expand"></use>
              </svg>
            </div>
            <div class="btn lefts-btn">
              <svg class="icon icon-md" style="" aria-hidden="true">
                  <use class="" href="#icon-sidebar-collapse"></use>
              </svg>
            </div>
            <div class="btn left-btn">
              <svg class="icon icon-md" style="" aria-hidden="true">
                  <use class="" href="#icon-left"></use>
              </svg>
            </div>
          </div>
          <div class="abs-item-container">
            <div class="items-section items-second-table"></div>
          </div>
        </div>
        <div class="actions-dialog">
            <div class="btn-actions reset-btn">
              ${__("Reset")}
            </div>
            <div class="btn-actions save-btn">
              ${__("Save")}
            </div>
        </div>
      </div>
      `);

    dialog.show();
    var first_items_wrapper =
      dialog.fields_dict.content_item.$wrapper.find(".items-first-table");
    var second_items_wrapper = dialog.fields_dict.content_item.$wrapper.find(
      ".items-second-table"
    );
    var actions_items = dialog.fields_dict.content_item.$wrapper.find(
      ".actions-item-container"
    );
    var actions_dialog =
      dialog.fields_dict.content_item.$wrapper.find(".actions-dialog");

    async function on_change_first_table() {
      let table_name = dialog.get_value("first_table");
      default_table = table_name;
      let items = await get_items_table(table_name);
      first_table_items = items;
      get_items_first_table(items);
    }

    first_items_wrapper.on("change", ".checkbox-input", function () {
      var itemWrapper = $(this).next(".item-wrapper");
      let qty = Number(itemWrapper.attr("data-row-qty"));
      if (qty > 1 && $(this).is(":checked")) {
        var d = new frappe.ui.Dialog({
          title: __("How many quantities?"),
          size: "small",
          static: false,
          fields: [
            {
              fieldname: "qty",
              fieldtype: "Int",
              label: __("Quantity"),
              reqd: 1,
            },
          ],
          primary_action_label: "Save",
          primary_action(values) {
            itemWrapper.attr(
              "data-row-qtyget",
              values.qty >= qty ? qty : values.qty
            );
            d.hide();
          },
        });
        d.$wrapper.find(".modal-dialog").css("width", "auto");
        d.show();
      }
    });

    actions_items.find(".btn").on("click", async function () {
      let tables = dialog.get_values();
      if (!tables.first_table || !tables.second_table) {
        frappe.msgprint(__("Please select the table."));
        return;
      }

      if ($(this).hasClass("right-btn")) {
        let itemsToMove = getCheckedItems(first_items_wrapper);
        if (itemsToMove.length == 0) {
          frappe.msgprint(__("Please select items."));
          return;
        }

        await moveItems(first_table_items, second_table_items, itemsToMove);

        get_items_first_table(first_table_items);
        get_items_second_table(second_table_items);
      } else if ($(this).hasClass("rights-btn")) {
        let new_items = [...second_table_items, ...first_table_items];
        second_table_items = new_items;
        first_table_items = [];

        get_items_first_table(first_table_items);
        get_items_second_table(new_items);
      } else if ($(this).hasClass("lefts-btn")) {
        let new_items = [...first_table_items, ...second_table_items];
        first_table_items = new_items;
        second_table_items = [];

        get_items_first_table(new_items);
        get_items_second_table(second_table_items);
      } else if ($(this).hasClass("left-btn")) {
        let itemsToMove = getCheckedItems(second_items_wrapper);
        if (itemsToMove.length == 0) {
          frappe.msgprint(__("Please select items."));
          return;
        }

        await moveItems(second_table_items, first_table_items, itemsToMove);
        get_items_first_table(first_table_items);
        get_items_second_table(second_table_items);
      }
    });
    actions_dialog.find(".btn-actions").on("click", async function () {
      if ($(this).hasClass("reset-btn")) {
        let tables = dialog.get_values();
        let items = await get_items_table(default_table);
        first_table_items = items;
        get_items_first_table(items);
        if (default_table == tables.second_table) {
          dialog.set_value("second_table", "");
        } else {
          if (!tables.second_table) return;
          let items = await get_items_table(tables.second_table);
          second_table_items = items;
          get_items_second_table(items);
        }
      } else if ($(this).hasClass("save-btn")) {
        let tables = dialog.get_values();
        if (!tables.first_table || !tables.second_table) {
          frappe.msgprint(__("Please select the table."));
          return;
        }
        let data = [];
        if (first_table_items.length > 0) {
          data = [
            {
              table: tables.second_table,
              items: second_table_items,
            },
            {
              table: tables.first_table,
              items: first_table_items,
            },
          ];
        } else if (second_table_items.length > 0) {
          data = [
            {
              table: tables.first_table,
              items: first_table_items,
            },
            {
              table: tables.second_table,
              items: second_table_items,
            },
          ];
        }

        frappe.call({
          method: "ditech_core.ditech_core.pos.move_items",
          freeze: true,
          args: {
            data: data,
          },
          callback: () => {
            me.set_search_value("");
            dialog.hide();
          },
        });
      }
    });

    function getCheckedItems($wrapper) {
      const checkedItems = $wrapper
        .find(".checkbox-input:checked")
        .map(function () {
          const $itemWrapper = $(this)
            .closest(".item-wrappe-group")
            .find(".item-wrapper");
          return {
            name: $itemWrapper.attr("data-row-name"),
            qty: Number($itemWrapper.attr("data-row-qtyget")),
          };
        })
        .get();

      return checkedItems;
    }

    async function moveItems(sourceList, destinationList, itemsToMove) {
      await itemsToMove.forEach((item) => {
        let index = sourceList.findIndex((i) => i.name === item.name);
        if (index !== -1 && sourceList[index].qty >= item.qty) {
          const { rate } = sourceList[index];
          const amount = item.qty * rate;

          let existingItemIndex = destinationList.findIndex(
            (i) => i.name === item.name
          );
          if (existingItemIndex !== -1) {
            destinationList[existingItemIndex].qty += item.qty;
            destinationList[existingItemIndex].amount += amount;
          } else {
            destinationList.push({
              ...sourceList[index],
              qty: item.qty,
              amount: amount,
            });
          }
          sourceList[index].qty -= item.qty;
          sourceList[index].amount -= amount;
          if (sourceList[index].qty === 0) {
            sourceList.splice(index, 1);
          }
        }
      });
    }

    async function get_items_first_table(items) {
      load_items(items, first_items_wrapper);
    }
    async function get_items_second_table(items) {
      load_items(items, second_items_wrapper);
    }

    async function get_items_table(table_name) {
      let data = [];
      await frappe.call({
        method: "ditech_core.ditech_core.pos.get_items_table",
        freeze: true,
        args: {
          table_name: table_name,
        },
        callback: (r) => {
          data = r.message;
        },
      });
      return data;
    }

    function load_items(items, $wrapper) {
      $wrapper.html("");
      if (items.length) {
        items.forEach((item) => {
          render_item(item, $wrapper);
        });
      }
    }

    function render_item(item_data, $wrapper) {
      $wrapper.append(
        `<label class="item-wrappe-group">
          <input type="checkbox" class="checkbox-input" />
          <div class="item-wrapper"
           data-row-name="${escape(item_data.name)}"
           data-row-qty="${escape(item_data.qty)}"
           data-row-qtyget="${escape(item_data.qty)}"
          ></div>
        </label>
          <div class="seperator"></div>`
      );
      let $item_to_update = get_item(item_data, $wrapper);

      $item_to_update.html(
        `${get_item_image_html()}
        <div class="item-name-desc">
          <div class="item-name">
            ${item_data.item_name}
          </div>
          ${get_description_html()}
        </div>
        ${get_rate_discount_html()}`
      );

      function get_rate_discount_html() {
        if (
          item_data.rate &&
          item_data.amount &&
          item_data.rate !== item_data.amount
        ) {
          return `
            <div class="item-qty-rate">
              <div class="item-qty"><span>${item_data.qty || 0} ${
            item_data.uom
          }</span></div>
              <div class="item-rate-amount">
                <div class="item-rate">${format_currency(
                  item_data.amount,
                  currency
                )}</div>
                <div class="item-amount">${format_currency(
                  item_data.rate,
                  currency
                )}</div>
              </div>
            </div>`;
        } else {
          return `
            <div class="item-qty-rate">
              <div class="item-qty"><span>${item_data.qty || 0} ${
            item_data.uom
          }</span></div>
              <div class="item-rate-amount">
                <div class="item-rate">${format_currency(
                  item_data.rate,
                  currency
                )}</div>
              </div>
            </div>`;
        }
      }

      function get_description_html() {
        if (item_data.description) {
          if (item_data.description.indexOf("<div>") != -1) {
            try {
              item_data.description = $(item_data.description).text();
            } catch (error) {
              item_data.description = item_data.description
                .replace(/<div>/g, " ")
                .replace(/<\/div>/g, " ")
                .replace(/ +/g, " ");
            }
          }
          item_data.description = frappe.ellipsis(item_data.description, 45);
          return `<div class="item-desc">${item_data.description}</div>`;
        }
        return ``;
      }

      function get_item_image_html() {
        const { image, item_name } = item_data;
        if (!me.hide_images && image) {
          return `
            <div class="item-image">
              <img
                onerror="cur_pos.cart.handle_broken_image(this)"
                src="${image}" alt="${frappe.get_abbr(item_name)}"">
            </div>`;
        } else {
          return `<div class="item-image item-abbr">${frappe.get_abbr(
            item_name
          )}</div>`;
        }
      }
    }
    function get_item({ name }, $wrapper) {
      const item_selector = `.item-wrapper[data-row-name="${escape(name)}"]`;
      return $wrapper.find(item_selector);
    }
  }
  async split_invoice(invoice, table) {
    const currency = this.settings.currency;
    const me = this;
    var filters = [];
    await get_filters();
    var items = [];
    let old_inv = "";
    var dialog = new frappe.ui.Dialog({
      title: __("Split Invoice"),
      fields: [
        {
          fieldname: "pos_invoice",
          fieldtype: "Link",
          options: "POS Invoice",
          label: __("POS Invoice"),
          placeholder: __("Select POS Invoice"),
          change: () => {
            let invoice = dialog.get_value("pos_invoice");
            if (invoice != old_inv) {
              old_inv = invoice;
              handle_change(invoice);
            }
          },
          get_query: () => {
            return {
              filters: {
                name: ["in", filters],
              },
            };
          },
        },
        {
          fieldname: "column_break_1",
          fieldtype: "Column Break",
        },
        {
          fieldname: "actions_dialog",
          fieldtype: "HTML",
          label: "Actions Dialog",
        },
        {
          fieldname: "section_break_1",
          fieldtype: "Section Break",
          hide_border: 1,
        },
        {
          fieldname: "content_item",
          fieldtype: "HTML",
          label: "Content",
        },
      ],
    });

    dialog.set_value("pos_invoice", invoice);
    dialog.fields_dict.pos_invoice.toggle_label(false);
    dialog.fields_dict.content_item.$wrapper.html(`
       <div class="dialog-split-invoice">
        <div class="dialog-item-container">
            <div class="items-section"></div>
        </div>
       </div>
         `);
    dialog.fields_dict.actions_dialog.$wrapper.html(`
       <div class="dialog-split-invoice">
          <div class="actions-dialog">
              <div class="btn-actions unsplit-btn" style="color: var(--gray-300)">
                ${__("Unsplit")}
              </div>
              <div class="btn-actions split-btn">
                ${__("Split")}
              </div>
          </div> 
        </div>`);

    dialog.show();
    var items_wrapper =
      dialog.fields_dict.content_item.$wrapper.find(".items-section");
    var actions_dialog =
      dialog.fields_dict.actions_dialog.$wrapper.find(".actions-dialog");

    actions_dialog.find(".btn-actions").on("click", async function () {
      if ($(this).hasClass("unsplit-btn")) {
        if ($(this).attr("style").indexOf("--gray-700") == -1) return;
        frappe.call({
          method: "ditech_core.ditech_core.pos.unsplit_invoice",
          freeze: true,
          args: {
            table: table,
          },
          callback: async () => {
            await get_filters();
            handle_change(invoice);
            me.set_search_value("");
          },
        });
      } else if ($(this).hasClass("split-btn")) {
        let itemsRemove = getCheckedItems(items_wrapper);
        if (itemsRemove.length == 0) {
          frappe.msgprint(__("Please select items!"));
          return;
        }

        let removedItems = [];
        let new_items = [];
        items.forEach((item) => {
          let itemToRemove = itemsRemove.find((rem) => rem.name === item.name);
          let item_qty = item.qty;
          if (itemToRemove) {
            let removedQty = Math.min(item.qty, itemToRemove.qty);

            removedItems.push({ ...item, qty: removedQty });

            item_qty -= removedQty;
          }
          if (item_qty > 0) new_items.push({ ...item, qty: item_qty });
        });

        if (new_items.length == 0) {
          frappe.msgprint(__("Cannot select all items!"));
          return;
        }

        frappe.call({
          method: "ditech_core.ditech_core.pos.split_invoice",
          freeze: true,
          args: {
            main_invoice: dialog.get_value("pos_invoice"),
            main_items: new_items,
            items: removedItems,
          },
          callback: async () => {
            await get_filters();
            handle_change(old_inv || invoice);
            me.set_search_value("");
          },
        });
      }
    });
    items_wrapper.on("change", ".checkbox-input", function () {
      var itemWrapper = $(this).next(".item-wrapper");
      let qty = Number(itemWrapper.attr("data-row-qty"));
      if (qty > 1 && $(this).is(":checked")) {
        var d = new frappe.ui.Dialog({
          title: __("How many quantities?"),
          size: "small",
          static: false,
          fields: [
            {
              fieldname: "qty",
              fieldtype: "Int",
              label: "Quantity",
              reqd: 1,
            },
          ],
          primary_action_label: "Save",
          primary_action(values) {
            itemWrapper.attr(
              "data-row-qtyget",
              values.qty >= qty ? qty : values.qty
            );
            d.hide();
          },
        });
        d.show();
      }
    });
    function getCheckedItems() {
      const checkedItems = items_wrapper
        .find(".checkbox-input:checked")
        .map(function () {
          const $itemWrapper = $(this)
            .closest(".item-wrappe-group")
            .find(".item-wrapper");
          return {
            name: $itemWrapper.attr("data-row-name"),
            qty: Number($itemWrapper.attr("data-row-qtyget")),
          };
        })
        .get();

      return checkedItems;
    }

    function handle_change(invoice) {
      if (!filters.includes(invoice) && invoice != "")
        dialog.set_value("pos_invoice", "");
      get_items(invoice);
    }

    function get_items(invoice) {
      frappe.call({
        method: "ditech_core.ditech_core.pos.get_items_invoice",
        freeze: true,
        args: {
          invoice: invoice,
        },
        callback: (r) => {
          items = r.message;
          load_items(items);

          actions_dialog.find(".unsplit-btn").css({
            color: filters.length > 1 ? "var(--gray-700)" : "var(--gray-300)",
          });
        },
      });
    }
    async function get_filters() {
      await frappe.db
        .get_value("POS Table", table, ["pos_invoice", "invoice_split"])
        .then((r) => {
          let res = r.message;
          filters = res.invoice_split
            ? res.invoice_split.split(" , ")
            : [res.pos_invoice];
        });
    }

    function load_items(items) {
      items_wrapper.html("");
      if (items.length) {
        items.forEach((item) => {
          render_item(item);
        });
      }
    }

    function render_item(item_data) {
      items_wrapper.append(
        `<label class="item-wrappe-group">
          <input type="checkbox" class="checkbox-input" />
          <div class="item-wrapper"
           data-row-name="${escape(item_data.name)}"
           data-row-qty="${escape(item_data.qty)}"
           data-row-qtyget="${escape(item_data.qty)}"
          ></div>
        </label>
          <div class="seperator"></div>`
      );
      let $item_to_update = get_item(item_data);

      $item_to_update.html(
        `${get_item_image_html()}
        <div class="item-name-desc">
          <div class="item-name">
            ${item_data.item_name}
          </div>
          ${get_description_html()}
        </div>
        ${get_rate_discount_html()}`
      );

      function get_rate_discount_html() {
        if (
          item_data.rate &&
          item_data.amount &&
          item_data.rate !== item_data.amount
        ) {
          return `
            <div class="item-qty-rate">
              <div class="item-qty"><span>${item_data.qty || 0} ${
            item_data.uom
          }</span></div>
              <div class="item-rate-amount">
                <div class="item-rate">${format_currency(
                  item_data.amount,
                  currency
                )}</div>
                <div class="item-amount">${format_currency(
                  item_data.rate,
                  currency
                )}</div>
              </div>
            </div>`;
        } else {
          return `
            <div class="item-qty-rate">
              <div class="item-qty"><span>${item_data.qty || 0} ${
            item_data.uom
          }</span></div>
              <div class="item-rate-amount">
                <div class="item-rate">${format_currency(
                  item_data.rate,
                  currency
                )}</div>
              </div>
            </div>`;
        }
      }

      function get_description_html() {
        if (item_data.description) {
          if (item_data.description.indexOf("<div>") != -1) {
            try {
              item_data.description = $(item_data.description).text();
            } catch (error) {
              item_data.description = item_data.description
                .replace(/<div>/g, " ")
                .replace(/<\/div>/g, " ")
                .replace(/ +/g, " ");
            }
          }
          item_data.description = frappe.ellipsis(item_data.description, 45);
          return `<div class="item-desc">${item_data.description}</div>`;
        }
        return ``;
      }

      function get_item_image_html() {
        const { image, item_name } = item_data;
        if (!me.hide_images && image) {
          return `
            <div class="item-image">
              <img
                onerror="cur_pos.cart.handle_broken_image(this)"
                src="${image}" alt="${frappe.get_abbr(item_name)}"">
            </div>`;
        } else {
          return `<div class="item-image item-abbr">${frappe.get_abbr(
            item_name
          )}</div>`;
        }
      }
    }
    function get_item({ name }) {
      const item_selector = `.item-wrapper[data-row-name="${escape(name)}"]`;
      return items_wrapper.find(item_selector);
    }
  }
  async cancel(invoice, table) {
    const currency = this.settings.currency;
    const me = this;
    var filters = [];
    await get_filters();
    var items = [];
    let old_inv = "";
    var dialog = new frappe.ui.Dialog({
      title: __("Cancel order or delete items"),
      size: "large",
      fields: [
        {
          fieldname: "pos_invoice",
          fieldtype: "Link",
          options: "POS Invoice",
          label: __("POS Invoice"),
          placeholder: __("Select POS Invoice"),
          change: () => {
            let invoice = dialog.get_value("pos_invoice");
            if (invoice != old_inv) {
              old_inv = invoice;
              handle_change(invoice);
            }
          },
          get_query: () => {
            return {
              filters: {
                name: ["in", filters],
              },
            };
          },
        },
        {
          fieldname: "column_break_1",
          fieldtype: "Column Break",
        },
        {
          fieldname: "actions_dialog",
          fieldtype: "HTML",
          label: "Actions Dialog",
        },
        {
          fieldname: "section_break_1",
          fieldtype: "Section Break",
          hide_border: 1,
        },
        {
          fieldname: "content_item",
          fieldtype: "HTML",
          label: "Content",
        },
      ],
    });

    dialog.set_value("pos_invoice", invoice);
    dialog.fields_dict.pos_invoice.toggle_label(false);
    dialog.fields_dict.content_item.$wrapper.html(`
       <div class="dialog-cancel-invoice">
        <div class="dialog-item-container">
            <div class="items-section"></div>
        </div>
       </div>
         `);
    dialog.fields_dict.actions_dialog.$wrapper.html(`
       <div class="dialog-cancel-invoice">
          <div class="actions-dialog">
              <div class="btn-actions del-btn" style="color: var(--gray-700)">
                ${__("Detele")}
              </div>
              <div class="btn-actions cancel-btn">
                ${__("Cancel")}
              </div>
          </div> 
        </div>`);

    dialog.show();

    var items_wrapper =
      dialog.fields_dict.content_item.$wrapper.find(".items-section");
    var actions_dialog =
      dialog.fields_dict.actions_dialog.$wrapper.find(".actions-dialog");

    actions_dialog.find(".btn-actions").on("click", async function () {
      if ($(this).hasClass("del-btn")) {
        let itemsRemove = getCheckedItems(items_wrapper);
        if (itemsRemove.length == 0) {
          frappe.msgprint(__("Please select items!"));
          return;
        }

        let removedItems = [];
        let new_items = [];
        items.forEach((item) => {
          let itemToRemove = itemsRemove.find((rem) => rem.name === item.name);
          let item_qty = item.qty;
          if (itemToRemove) {
            let removedQty = Math.min(item.qty, itemToRemove.qty);

            removedItems.push({ ...item, qty: removedQty });

            item_qty -= removedQty;
          }
          if (item_qty > 0) new_items.push({ ...item, qty: item_qty });
        });

        if (new_items.length == 0) {
          frappe.msgprint(__("Cannot select all items!"));
          return;
        }
        let d = new frappe.ui.Dialog({
          title: __("Why you want to remove items?"),
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
              method: "ditech_core.ditech_core.pos.delete_items",
              freeze: true,
              args: {
                items: removedItems,
                invoice: dialog.get_value("pos_invoice"),
                reason: values.reason,
              },
              callback: async () => {
                d.hide();
                await get_filters();
                handle_change(old_inv || invoice);
                me.set_search_value("");
              },
            });
          },
        });
        d.show();
      } else if ($(this).hasClass("cancel-btn")) {
        if(items.find(item=> item.custom_pos_status == "Done")){
          frappe.msgprint(__("You cannot cancel the order for completed items!"));
          return
        }
        let d = new frappe.ui.Dialog({
          title: __("Why you want to cancel order <b>{0}</b>?", [
            dialog.get_value("pos_invoice"),
          ]),
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
                invoice: dialog.get_value("pos_invoice"),
                reason: values.reason,
              },
              callback: async () => {
                d.hide();
                await get_filters();
                handle_change(old_inv || invoice);
                me.set_search_value("");
              },
            });
          },
        });
        d.show();
      }
    });
    items_wrapper.on("change", ".checkbox-input", function () {
      var itemWrapper = $(this).next(".item-wrapper");
      let qty = Number(itemWrapper.attr("data-row-qty"));
      if (qty > 1 && $(this).is(":checked")) {
        var d = new frappe.ui.Dialog({
          title: __("How many quantities?"),
          size: "small",
          static: false,
          fields: [
            {
              fieldname: "qty",
              fieldtype: "Int",
              label: "Quantity",
              reqd: 1,
            },
          ],
          primary_action_label: "Save",
          primary_action(values) {
            itemWrapper.attr(
              "data-row-qtyget",
              values.qty >= qty ? qty : values.qty
            );
            d.hide();
          },
        });
        d.show();
      }
    });
    function getCheckedItems() {
      const checkedItems = items_wrapper
        .find(".checkbox-input:checked")
        .map(function () {
          const $itemWrapper = $(this)
            .closest(".item-wrappe-group")
            .find(".item-wrapper");
          return {
            name: $itemWrapper.attr("data-row-name"),
            qty: Number($itemWrapper.attr("data-row-qtyget")),
          };
        })
        .get();

      return checkedItems;
    }

    function handle_change(invoice) {
      if (!filters.includes(invoice) && invoice != "")
        dialog.set_value("pos_invoice", "");
      get_items(invoice);
    }

    function get_items(invoice) {
      frappe.call({
        method: "ditech_core.ditech_core.pos.get_items_invoice",
        freeze: true,
        args: {
          invoice: invoice,
        },
        callback: (r) => {
          items = r.message;
          load_items(items);
        },
      });
    }
    async function get_filters() {
      await frappe.db
        .get_value("POS Table", table, ["pos_invoice", "invoice_split"])
        .then((r) => {
          let res = r.message;
          filters = res.invoice_split
            ? res.invoice_split.split(" , ")
            : [res.pos_invoice];
        });
    }

    function load_items(items) {
      items_wrapper.html("");
      if (items.length) {
        items.forEach((item) => {
          render_item(item);
        });
      }
    }

    function render_item(item_data) {
      items_wrapper.append(
        `<label class="item-wrappe-group">
          <input type="checkbox" class="checkbox-input" ${
            item_data.custom_pos_status == "Done" ? "disabled" : ""
          }/>
          <div class="item-wrapper"
           data-row-name="${escape(item_data.name)}"
           data-row-qty="${escape(item_data.qty)}"
           data-row-qtyget="${escape(item_data.qty)}"
          ></div>
        </label>
          <div class="seperator"></div>`
      );
      let $item_to_update = get_item(item_data);

      $item_to_update.html(
        `${get_item_image_html()}
        <div class="item-name-desc">
          <div class="item-name">
            ${item_data.item_name}
          </div>
          ${get_description_html()}
        </div>
        ${get_rate_discount_html()}`
      );

      function get_rate_discount_html() {
        if (
          item_data.rate &&
          item_data.amount &&
          item_data.rate !== item_data.amount
        ) {
          return `
            <div class="item-qty-rate">
              <div class="item-qty">${
                item_data.custom_pos_status == "Done"
                  ? `<span class="mr-2"><svg class="es-icon es-line icon-sm" style="" aria-hidden="true">
          <use class="" href="#icon-solid-success"></use></svg></span>`
                  : ""
              }<span>${item_data.qty || 0} ${item_data.uom}</span></div>
              <div class="item-rate-amount">
                <div class="item-rate">${format_currency(
                  item_data.amount,
                  currency
                )}</div>
                <div class="item-amount">${format_currency(
                  item_data.rate,
                  currency
                )}</div>
              </div>
            </div>`;
        } else {
          return `
            <div class="item-qty-rate">
              <div class="item-qty">${
                item_data.custom_pos_status == "Done"
                  ? `<span class="mr-2"><svg class="es-icon es-line icon-sm" style="" aria-hidden="true">
          <use class="" href="#icon-solid-success"></use></svg></span>`
                  : ""
              }<span>${item_data.qty || 0} ${item_data.uom}</span></div>
              <div class="item-rate-amount">
                <div class="item-rate">${format_currency(
                  item_data.rate,
                  currency
                )}</div>
              </div>
            </div>`;
        }
      }

      function get_description_html() {
        if (item_data.description) {
          if (item_data.description.indexOf("<div>") != -1) {
            try {
              item_data.description = $(item_data.description).text();
            } catch (error) {
              item_data.description = item_data.description
                .replace(/<div>/g, " ")
                .replace(/<\/div>/g, " ")
                .replace(/ +/g, " ");
            }
          }
          item_data.description = frappe.ellipsis(item_data.description, 45);
          return `<div class="item-desc">${item_data.description}</div>`;
        }
        return ``;
      }

      function get_item_image_html() {
        const { image, item_name } = item_data;
        if (!me.hide_images && image) {
          return `
            <div class="item-image">
              <img
                onerror="cur_pos.cart.handle_broken_image(this)"
                src="${image}" alt="${frappe.get_abbr(item_name)}"">
            </div>`;
        } else {
          return `<div class="item-image item-abbr">${frappe.get_abbr(
            item_name
          )}</div>`;
        }
      }
    }
    function get_item({ name }) {
      const item_selector = `.item-wrapper[data-row-name="${escape(name)}"]`;
      return items_wrapper.find(item_selector);
    }
  }
  toggle_component(show) {
    this.$component.css("display", show ? "block" : "none");
    if (show) {
      let frm = this.events.get_frm();
      frm = undefined;
    }
  }
};
