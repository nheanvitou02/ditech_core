ditech.POS.CustomerOrderSummary = class {
  constructor({ wrapper, events, settings }) {
    this.wrapper = wrapper;
    this.events = events;
    this.exchange_rate = settings.exchange_rate;
    this.receipt = settings.custom_receipt_print_format;
    this.init_component();
  }

  init_component() {
    this.prepare_dom();
    this.bind_events();
  }

  prepare_dom() {
    this.wrapper.append(
      `<section class="customer-order-summary">
				<div class="no-summary-placeholder">
					${__("Select an order to load summary data")}
				</div>
				<div class="invoice-summary-wrapper">
					<div class="abs-container">
						<div class="upper-section"></div>
						<div class="label">${__("Items")}</div>
						<div class="items-container summary-container"></div>
            <div class="label">${__("Totals")}</div>
						<div class="totals-container summary-container"></div>
						<div class="summary-btns"></div>
					</div>
				</div>
			</section>`
    );

    this.$component = this.wrapper.find(".customer-order-summary");
    this.$summary_wrapper = this.$component.find(".invoice-summary-wrapper");
    this.$summary_container = this.$component.find(".abs-container");
    this.$upper_section = this.$summary_container.find(".upper-section");
    this.$items_container = this.$summary_container.find(".items-container");
    this.$totals_container = this.$summary_container.find(".totals-container");
    this.$summary_btns = this.$summary_container.find(".summary-btns");
  }

  get_upper_section_html(doc) {
    const { status } = doc;
    const posting_datetime = moment(
      doc.posting_date + " " + doc.posting_time
    ).format("Do MMMM, h:mma");
    let indicator_color = "";

    status === "Confirmed" && (indicator_color = "green");
    ["Rejected", "Cancelled"].includes(status) && (indicator_color = "red");
    status === "Pending" && (indicator_color = "orange");

    return `<div class="left-section">
					<div class="customer-name">${doc.customer}</div>
          ${
            doc?.table_label
              ? `<div class="cashier">${__("Table")}: ${doc.table_label}</div>`
              : ""
          }
          <div class="cashier">${posting_datetime}</div>
				</div>
				<div class="right-section">
					<div class="invoice-name">${doc.name}</div>
					<span class="indicator-pill whitespace-nowrap ${indicator_color}"><span>${
      doc.status
    }</span></span>
				</div>`;
  }

  get_item_html(doc, item_data) {
    return `<div class="item-row-wrapper">
					<div class="item-name">${item_data.item_name}</div>
					<div class="item-qty">${item_data.qty || 0} ${item_data.uom}</div>
					<div class="item-rate-disc">${get_rate_discount_html()}</div>
				</div>`;

    function get_rate_discount_html() {
      if (
        item_data.rate &&
        item_data.price_list_rate &&
        item_data.rate !== item_data.price_list_rate
      ) {
        return `<span class="item-disc">(${
          item_data.discount_percentage
        }% off)</span>
						<div class="item-rate">${format_currency(
              item_data.rate,
              doc.currency,
              flt(item_data.rate, 2) % 1 != 0 ? 2 : 0
            )}</div>`;
      } else {
        return `<div class="item-rate">${format_currency(
          item_data.price_list_rate || item_data.rate,
          doc.currency,
          flt(item_data.price_list_rate || item_data.rate, 2) % 1 != 0 ? 2 : 0
        )}</div>`;
      }
    }
  }

  bind_events() {
    this.$summary_container.on("click", ".reject-btn", () => {
      frappe.confirm("Are you sure you want to rejected?", () => {
        frappe.call({
          method: "ditech_core.ditech_core.pos.update_status_order",
          freeze: true,
          args: { name: this.doc.name, status: "Rejected" },
          callback: (res) => {
            if (res.message) {
              this.events.refresh_list();
              frappe.show_alert({
                message: __("The order rejected successfully."),
                indicator: "green",
              });
            }
          },
        });
      });
    });

    this.$summary_container.on("click", ".confirm-btn", () => {
      frappe.confirm("Are you sure you want to confirmed?", () => {
        frappe.call({
          method: "ditech_core.ditech_core.pos.update_status_order",
          freeze: true,
          args: { name: this.doc.name, status: "Confirmed" },
          callback: (res) => {
            if (res.message) {
              this.events.refresh_list();
              frappe.show_alert({
                message: __("The order confirmed successfully."),
                indicator: "green",
              });
            }
          },
        });
      });
    });
  }

  add_summary_btns(map) {
    this.$summary_btns.html("");
    map.forEach((m) => {
      if (m.condition) {
        m.visible_btns.forEach((b) => {
          const class_name = b.split(" ")[0].toLowerCase();
          const btn = __(b);
          this.$summary_btns.append(
            `<div class="summary-btn btn btn-default ${class_name}-btn">${btn}</div>`
          );
        });
      }
    });
    this.$summary_btns.children().last().removeClass("mr-4");
  }

  toggle_summary_placeholder(show) {
    if (show) {
      this.$summary_wrapper.css("display", "none");
      this.$component.find(".no-summary-placeholder").css("display", "flex");
    } else {
      this.$summary_wrapper.css("display", "flex");
      this.$component.find(".no-summary-placeholder").css("display", "none");
    }
  }

  get_condition_btn_map() {
    return [
      {
        condition: this.doc.docstatus === 0 && this.doc.status != "Rejected",
        visible_btns: ["Reject Order", "Confirm Order"],
      },
    ];
  }

  load_summary_of(doc, after_submission = false) {
    after_submission
      ? this.$component.css("grid-column", "span 10 / span 10")
      : this.$component.css("grid-column", "span 6 / span 6");

    this.toggle_summary_placeholder(false);

    this.doc = doc;

    this.attach_document_info(doc);

    this.attach_items_info(doc);

    this.attach_totals_info(doc);

    const condition_btns_map = this.get_condition_btn_map();

    this.add_summary_btns(condition_btns_map);
  }

  get_total_html(doc) {
    return `<div class="summary-row-wrapper">
					<div>${__("Total")}</div>
					<div>${format_currency(
            doc.total,
            doc.currency,
            flt(doc.total, 2) % 1 != 0 ? 2 : 0
          )}</div>
				</div>`;
  }

  async attach_document_info(doc) {
    if (this.doc.table)
      doc.table_label = await frappe.db
        .get_value("POS Table", this.doc.table, "label")
        .then(({ message }) => message.label);
    const upper_section_dom = this.get_upper_section_html(doc);
    this.$upper_section.html(upper_section_dom);
  }

  attach_items_info(doc) {
    this.$items_container.html("");
    doc.items.forEach((item) => {
      const item_dom = this.get_item_html(doc, item);
      this.$items_container.append(item_dom);
      this.set_dynamic_rate_header_width();
    });
  }

  set_dynamic_rate_header_width() {
    const rate_cols = Array.from(this.$items_container.find(".item-rate-disc"));
    this.$items_container.find(".item-rate-disc").css("width", "");
    let max_width = rate_cols.reduce((max_width, elm) => {
      if ($(elm).width() > max_width) max_width = $(elm).width();
      return max_width;
    }, 0);

    max_width += 1;
    if (max_width == 1) max_width = "";

    this.$items_container.find(".item-rate-disc").css("width", max_width);
  }

  attach_totals_info(doc) {
    this.$totals_container.html("");

    const total_dom = this.get_total_html(doc);
    this.$totals_container.append(total_dom);
  }

  toggle_component(show) {
    show
      ? this.$component.css("display", "flex")
      : this.$component.css("display", "none");
  }
};
