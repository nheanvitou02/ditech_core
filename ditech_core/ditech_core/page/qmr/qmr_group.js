frappe.provide("ditech");

ditech.QMRGroup = class QMRGroup {
  constructor(opts) {
    $.extend(this, opts);
    this.make();
  }

  make() {
    this.content = $(frappe.render_template("qmr")).appendTo(
      this.parent
    );
    this.group = this.content.find(".qmr-group");

    const me = this;
    this.content.on("click", ".group-container .item-group", function () {
      const items = me.group.find(".item-group");
      const container = me.group.find("#group-container");
      const item = $(this);

      var group = $(this).text();
      me.event.get_items(group)

      items.removeClass("active");
      item.addClass("active");
      const itemCenterPosition = item.offset().left + item.outerWidth() / 2;
      const containerCenterPosition =
        container.offset().left + container.width() / 2;

      const scrollLeft =
        container.scrollLeft() + (itemCenterPosition - containerCenterPosition);

      container.animate(
        {
          scrollLeft: scrollLeft,
        },
        500
      );
    });
  }

  refresh() {
    if (this.before_refresh) {
      this.before_refresh();
    }

    var me = this;
    frappe.call({
      method: this.method,
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
      this.group.empty();
    }

    if (data.length > 0) {
      this.content.find(".qmr-group").css("text-align", "unset");
      this.group.html(
        frappe.render_template(this.template, {
          data: data,
          row: data.length <= 6 ? "1fr" : "repeat(2, 1fr)",
        })
      );
    } else {
      var message = __("No Item Group");
      this.content.find(".qmr-group").css("text-align", "center");

      $(`<div class='text-muted' style='margin: 20px 5px;'>
				${message} </div>`).appendTo(this.group);
    }
  }
};
