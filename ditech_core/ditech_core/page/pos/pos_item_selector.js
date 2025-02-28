import onScan from "onscan.js";

ditech.POS.ItemSelector = class {
  // eslint-disable-next-line no-unused-vars
  constructor({ frm, wrapper, events, pos_profile, settings, is_retail }) {
    this.wrapper = wrapper;
    this.events = events;
    this.pos_profile = pos_profile;
    this.hide_images = settings.hide_images;
    this.auto_add_item = settings.auto_add_item_to_cart;
    this.is_retail = is_retail;
    this.exchange_rate = settings.exchange_rate;
    this.second_currency = settings.custom_second_currency;
    this.hide_second_price = settings.custom_hide_second_price;

    this.inti_component();

    this.$component.css("display", is_retail ? "flex" : "none");
  }

  inti_component() {
    this.prepare_dom();
    this.make_search_bar();
    this.load_items_data();
    this.bind_events();
    this.attach_shortcuts();
    this.load_item_groups_data();
  }

  prepare_dom() {
    this.wrapper.append(
      `<section class="items-selector">
        <div class="actual-items-container"></div>
				<div class="filter-section">
					<div class="label">${__("All Items")}</div>
					<div class="search-field"></div>
				</div>
        <div class="item-group-container"></div>
        <div class="section-item">
				  <div class="items-container"></div>
        </div>
			</section>`
    );

    this.$component = this.wrapper.find(".items-selector");
    this.$items_container = this.$component.find(".items-container");
    this.$actual_items_container = this.$component.find(
      ".actual-items-container"
    );
    this.$item_group_container = this.$component.find(".item-group-container");
  }

  load_item_groups_data() {
    frappe.call({
      method: "ditech_core.ditech_core.pos.get_item_groups_list",
      freeze: true,
      args: {
        pos_profile: this.pos_profile,
      },
      callback: (r) => {
        if (r.message) this.render_item_group_list(r.message);
      },
    });
  }

  render_item_group_list(groups) {
    this.$item_group_container.html("");
    groups.forEach((group) => {
      const group_html = this.get_item_group_html(group);
      this.$item_group_container.append(group_html);
    });
  }

  get_item_group_html(group) {
    return `<div class="item-group-wrapper" data-group-name="${escape(
      group
    )}" title="${group}">
              <div class="group-name">
                ${frappe.ellipsis(group, 18)}
              </div>
            </div>`;
  }

  async load_items_data() {
    if (!this.item_group) {
      const res = await frappe.db.get_value(
        "Item Group",
        { lft: 1, is_group: 1 },
        "name"
      );
      this.parent_item_group = res.message.name;
    }
    if (!this.price_list) {
      const res = await frappe.db.get_value(
        "POS Profile",
        this.pos_profile,
        "selling_price_list"
      );
      this.price_list = res.message.selling_price_list;
    }

    this.is_retail &&
      this.get_items({}).then(({ message }) => {
        this.render_item_list(message.items);
        this.events.render_actual_item_list(
          message.actual_items,
          this.$actual_items_container
        );
      });
  }

  get_items({ start = 0, page_length = 40, search_term = "" }) {
    const doc = this.events.get_frm().doc;
    const price_list = (doc && doc.selling_price_list) || this.price_list;
    let { item_group, pos_profile } = this;

    !item_group && (item_group = this.parent_item_group);

    return frappe.call({
      method: "ditech_core.ditech_core.pos.get_items",
      freeze: true,
      args: {
        start,
        page_length,
        price_list,
        item_group,
        search_term,
        pos_profile,
      },
    });
  }

  render_item_list(items) {
    this.$items_container.html("");

    items.forEach((item) => {
      const item_html = this.get_item_html(item);
      this.$items_container.append(item_html);
    });
  }

  get_item_html(item) {
    const me = this;
    // eslint-disable-next-line no-unused-vars
    const {
      item_image,
      serial_no,
      batch_no,
      barcode,
      actual_qty,
      uom,
      price_list_rate,
    } = item;
    const precision = flt(price_list_rate, 2) % 1 != 0 ? 2 : 0;
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

    let second_price = "";
    if (me.second_currency && !me.hide_second_price) {
      const second_precision =
        flt(me.exchange_rate * price_list_rate || 0, 2) % 1 != 0 ? 2 : 0;
      second_price = `<div style="font-size: var(--text-md);">${format_currency(
        me.exchange_rate * price_list_rate || 0,
        me.second_currency,
        second_precision
      )}</div>`;
    }
    function get_item_image_html() {
      if (!me.hide_images && item_image) {
        return `<div class="item-qty-pill">
							<span class="indicator-pill whitespace-nowrap ${indicator_color}">${qty_to_display}</span>
						</div>
						<div class="flex items-center justify-center h-32 border-b-grey text-6xl text-grey-100">
							<img
								onerror="cur_pos.item_selector.handle_broken_image(this)"
								class="h-full item-img" src="${item_image}"
								alt="${frappe.get_abbr(item.item_name)}"
							>
						</div>`;
      } else {
        return `<div class="item-qty-pill">
							<span class="indicator-pill whitespace-nowrap ${indicator_color}">${qty_to_display}</span>
						</div>
						<div class="item-display abbr">${frappe.get_abbr(item.item_name)}</div>`;
      }
    }

    return `<div class="item-wrapper"
				data-item-code="${escape(item.item_code)}" data-serial-no="${escape(serial_no)}"
				data-batch-no="${escape(batch_no)}" data-uom="${escape(uom)}"
				data-rate="${escape(price_list_rate || 0)}"
				title="${item.item_name}">

				${get_item_image_html()}

				<div class="item-detail" style="${second_price ? 'height: 4rem;' : ''}">
					<div class="item-name">
						${frappe.ellipsis(item.item_name, 18)}
					</div>
					<div class="item-rate">${
            format_currency(price_list_rate, item.currency, precision) || 0
          } / ${uom}</div>
          ${second_price}
				</div>
			</div>`;
  }

  handle_broken_image($img) {
    const item_abbr = $($img).attr("alt");
    $($img)
      .parent()
      .replaceWith(`<div class="item-display abbr">${item_abbr}</div>`);
  }

  make_search_bar() {
    const me = this;
    const doc = me.events.get_frm().doc;
    this.$component.find(".search-field").html("");
    this.$component.find(".item-group-field").html("");

    this.search_field = frappe.ui.form.make_control({
      df: {
        label: __("Search"),
        fieldtype: "Data",
        placeholder: __("Search by item code, serial number or barcode"),
      },
      parent: this.$component.find(".search-field"),
      render_input: true,
    });
    this.search_field.toggle_label(false);

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

  bind_events() {
    const me = this;
    window.onScan = onScan;

    onScan.decodeKeyEvent = function (oEvent) {
      var iCode = this._getNormalizedKeyNum(oEvent);
      switch (true) {
        case iCode >= 48 && iCode <= 90: // numbers and letters
        case iCode >= 106 && iCode <= 111: // operations on numeric keypad (+, -, etc.)
        case (iCode >= 160 && iCode <= 164) || iCode == 170: // ^ ! # $ *
        case iCode >= 186 && iCode <= 194: // (; = , - . / `)
        case iCode >= 219 && iCode <= 222: // ([ \ ] ')
        case iCode == 32: // spacebar
          if (oEvent.key !== undefined && oEvent.key !== "") {
            return oEvent.key;
          }

          var sDecoded = String.fromCharCode(iCode);
          switch (oEvent.shiftKey) {
            case false:
              sDecoded = sDecoded.toLowerCase();
              break;
            case true:
              sDecoded = sDecoded.toUpperCase();
              break;
          }
          return sDecoded;
        case iCode >= 96 && iCode <= 105: // numbers on numeric keypad
          return 0 + (iCode - 96);
      }
      return "";
    };

    onScan.attachTo(document, {
      onScan: (sScancode) => {
        if (this.search_field && this.$component.is(":visible")) {
          this.search_field.set_focus();
          this.set_search_value(sScancode);
          this.barcode_scanned = true;
        }
      },
    });

    this.$component.on("click", ".item-wrapper", function () {
      const $item = $(this);
      const item_code = unescape($item.attr("data-item-code"));
      let batch_no = unescape($item.attr("data-batch-no"));
      let serial_no = unescape($item.attr("data-serial-no"));
      let uom = unescape($item.attr("data-uom"));
      let rate = unescape($item.attr("data-rate"));

      // escape(undefined) returns "undefined" then unescape returns "undefined"
      batch_no = batch_no === "undefined" ? undefined : batch_no;
      serial_no = serial_no === "undefined" ? undefined : serial_no;
      uom = uom === "undefined" ? undefined : uom;
      rate = rate === "undefined" ? undefined : rate;

      me.events.item_selected({
        field: "qty",
        value: "+1",
        item: { item_code, batch_no, serial_no, uom, rate },
      });
      me.search_field.set_focus();
    });

    this.search_field.$input.on("input", (e) => {
      clearTimeout(this.last_search);
      this.last_search = setTimeout(() => {
        const search_term = e.target.value;
        this.filter_items({ search_term });
      }, 300);

      this.$clear_search_btn.toggle(Boolean(this.search_field.$input.val()));
    });

    this.search_field.$input.on("focus", () => {
      this.$clear_search_btn.toggle(Boolean(this.search_field.$input.val()));
    });

    this.$component.on("click", ".item-group-wrapper", function () {
      const $group = $(this);
      let group_name = unescape($group.attr("data-group-name"));
      $group[0].scrollIntoView({
        behavior: "smooth",
        block: "center",
        inline: "center",
      });
      if ($group.hasClass("active")) {
        $group.removeClass("active");
        group_name = "";
      } else {
        $(".item-group-wrapper").removeClass("active");
        $group.addClass("active");
      }
      me.item_group = group_name;
      !me.item_group && (me.item_group = me.parent_item_group);
      me.filter_items();
    });
  }

  attach_shortcuts() {
    const ctrl_label = frappe.utils.is_mac() ? "⌘" : "Ctrl";
    this.search_field.parent.attr("title", `${ctrl_label}+I`);
    frappe.ui.keys.add_shortcut({
      shortcut: "ctrl+i",
      action: () => this.search_field.set_focus(),
      condition: () => this.$component.is(":visible"),
      description: __("Focus on search input"),
      ignore_inputs: true,
      page: cur_page.page.page,
    });

    // for selecting the last filtered item on search
    frappe.ui.keys.on("enter", () => {
      const selector_is_visible = this.$component.is(":visible");
      if (!selector_is_visible || this.search_field.get_value() === "") return;

      if (this.items.length == 1) {
        this.$items_container.find(".item-wrapper").click();
        frappe.utils.play_sound("submit");
        this.set_search_value("");
      } else if (this.items.length == 0 && this.barcode_scanned) {
        // only show alert of barcode is scanned and enter is pressed
        frappe.show_alert({
          message: __("No items found. Scan barcode again."),
          indicator: "orange",
        });
        frappe.utils.play_sound("error");
        this.barcode_scanned = false;
        this.set_search_value("");
      }
    });
  }

  filter_items({ search_term = "" } = {}) {
    if (search_term) {
      search_term = search_term.toLowerCase();

      // memoize
      this.search_index = this.search_index || {};
      if (this.search_index[search_term]) {
        const items = this.search_index[search_term];
        this.items = items;
        this.render_item_list(items);
        this.auto_add_item &&
          this.items.length == 1 &&
          this.add_filtered_item_to_cart();
        return;
      }
    }

    this.get_items({ search_term }).then(({ message }) => {
      // eslint-disable-next-line no-unused-vars
      const { items, serial_no, batch_no, barcode, actual_items } = message;
      if (search_term && !barcode) {
        this.search_index[search_term] = items;
      }
      this.items = items;
      this.render_item_list(items);
      this.auto_add_item &&
        search_term &&
        this.items.length == 1 &&
        this.add_filtered_item_to_cart();
      this.events.render_actual_item_list(
        actual_items,
        this.$actual_items_container
      );
    });
  }

  add_filtered_item_to_cart() {
    this.$items_container.find(".item-wrapper").click();
    this.set_search_value("");
  }

  resize_selector(minimize) {
    minimize
      ? this.$component
          .find(".filter-section")
          .css("grid-template-columns", "repeat(1, minmax(0, 1fr))")
      : this.$component
          .find(".filter-section")
          .css("grid-template-columns", "repeat(12, minmax(0, 1fr))");

    minimize
      ? this.$component
          .find(".search-field")
          .css("margin", "var(--margin-sm) 0px")
      : this.$component
          .find(".search-field")
          .css("margin", "0px var(--margin-sm)");

    minimize
      ? this.$component.css("grid-column", "span 2 / span 2")
      : this.$component.css("grid-column", "span 6 / span 6");

    minimize
      ? this.$items_container.css(
          "grid-template-columns",
          "repeat(1, minmax(0, 1fr))"
        )
      : this.$items_container.css(
          "grid-template-columns",
          "repeat(4, minmax(0, 1fr))"
        );
  }

  toggle_component(show) {
    show && this.set_search_value("");
    this.$component.css("display", show ? "flex" : "none");
  }
};
