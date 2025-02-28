ditech.BarKitchen.BarKitchen = class {
  constructor({ wrapper, events, settings, pos_profile }) {
    this.wrapper = wrapper;
    this.events = events;
    this.pos_profile = pos_profile;
    this.settings = settings;
    this.first_load = true;
    this.init_component();
    this.columns = [
      {
        label: __("Table"),
        dataIndex: "table",
      },
      {
        label: __("Item"),
        dataIndex: "item_name",
        default: true,
      },
      {
        label: __("Note"),
        dataIndex: "note",
        column: 2,
        default: true,
      },
      {
        label: __("Qty"),
        dataIndex: "qty",
        textAlign: "right",
        default: true,
      },
      {
        label: __("UOM"),
        dataIndex: "uom",
      },
    ];
  }

  init_component() {
    this.prepare_dom();
    this.load_items_data();
    this.bind_events();
  }

  prepare_dom() {
    this.wrapper.append(
      `<section class="bar-kitchen" style="display: flex;">
            <div class="result">
              <div class="label">${__("List Ordered")}</div>
              <header class="level list-row-head text-muted">
                  <div class="level-left list-header-subject"></div>
                  <div class="level-right">
                      <span class="list-count">${__("Actions")}</span>
                  </div>
              </header>
              <div class="list-row-body"></div>
          </div>
      </section>`
    );

    this.$component = this.wrapper.find(".bar-kitchen");
  }

  load_items_data() {
    this.get_items({}).then(({ message }) => {
      if (this.first_load) {
        this.items_length = message.length;
        this.first_load = false;
      } else if (this.items_length < message.length) {
        frappe.utils.play_sound("alert");
        this.items_length = message.length;
      } else if (this.items_length > message.length) {
        this.items_length = message.length;
      }
      this.render_item_list(message);
    });
  }

  get_items({ start = 0, page_length = 40, search_term = "" }) {
    let { floor, status, pos_profile } = this;

    return frappe.call({
      method: "ditech_core.ditech_core.pos.get_bar_kitchen",
      freeze: true,
      args: { start, page_length, status, floor, search_term, pos_profile },
    });
  }

  render_item_list(items) {
    this.$component.find(".list-header-subject").html("");
    this.columns.forEach((col) => {
      const item_header_html = this.get_header_html(col);
      this.$component.find(".list-header-subject").append(item_header_html);
    });

    this.$component.find(".list-row-body").html("");
    items.forEach((item, index) => {
      const item_html = this.get_item_html(
        { ...item, no: index + 1 },
        this.columns
      );
      this.$component.find(".list-row-body").append(item_html);
    });

    setInterval(() => {
      if (!this.$component.find(".modified").is(":hidden")) {
        this.$component.find(".modified").each(function () {
          var timestamp = $(this).data("timestamp");
          $(this).html(frappe.datetime.comment_when(timestamp, true));
        });
      }
    }, 1000);
  }

  get_header_html(col) {
    const me = this;
    return `<div class="list-row-col ellipsis pl-2 text-${col?.textAlign} ${
      !col?.default && "hidden-xs"
    }" style="flex: ${col?.column};"><span>${col.label}</span></div>`;
  }
  get_item_html(item) {
    const me = this;
    const left_row = me.columns
      .map(
        (col) => `<div class="list-row-col ellipsis pl-2 text-${
          col?.textAlign
        } ${!col?.default && "hidden-xs"}" style="flex: ${col?.column};">
                    <span class="ellipsis" title="${
                      col.dataIndex == "note"
                        ? item[col.dataIndex].join(", ")
                        : item[col.dataIndex]
                    }">
                        ${
                          col.dataIndex == "note"
                            ? item[col.dataIndex].join(", ")
                            : item[col.dataIndex]
                        }
                    </span>
                </div>`
      )
      .join("");
    return `<div class="list-row-container">
              <div class="level list-row">
                  <div class="level-left ellipsis">
                      ${left_row}
                  </div>
                  <div class="level-right text-muted ellipsis">
                      <div class="level-item list-row-activity">
                          <span class="modified" data-timestamp="${
                            item.order_time
                          }"></span>
                          <span class="comment-count d-flex align-items-center">
                              <button class="btn btn-primary btn-sm done-btn" data-name="${escape(
                                item.name
                              )}" 
                            data-item_name="${escape(item.item_name)}"
                            data-table="${escape(item.table)}" 
                            data-qty="${escape(item.qty)}"
                            data-uom="${escape(item.uom)}"
                             data-label="${__("Done")}">${__("Done")}</button>
                          </span>
                      </div>
                    </div>
                  </div>
              <div class="list-row-border"></div>
          </div>`;
  }

  bind_events() {
    const me = this;
    this.$component.on("click", ".done-btn", function () {
      const $item = $(this);
      const name = unescape($item.attr("data-name"));
      const item_name = unescape($item.attr("data-item_name"));
      const table = unescape($item.attr("data-table"));
      const qty = unescape($item.attr("data-qty"));
      const uom = unescape($item.attr("data-uom"));
      let data = {
        name: name,
        item_name: item_name,
        table: table,
        qty: qty,
        uom: uom,
      };
      frappe.confirm(
        __("Are you sure want to done of <b>{0}</b>?", [item_name]),
        () => {
          frappe.call({
            method: "ditech_core.ditech_core.pos.confirm_done",
            freeze: true,
            args: { data: data },
            callback: () => {
              me.load_items_data();
            },
          });
        }
      );
    });
  }

  toggle_component(show) {
    show
      ? this.$component.css("display", "block") && this.load_items_data()
      : this.$component.css("display", "none");
  }
};
