/* eslint-disable no-unused-vars */
ditech.POS.Payment = class {
  constructor({ events, wrapper, settings, is_retail, key }) {
    this.wrapper = wrapper;
    this.events = events;
    this.is_retail = is_retail;
    this.exchange_rate = settings.exchange_rate;
    this.invoice = settings.print_format;
    this.init_component();
  }

  init_component() {
    this.prepare_dom();
    // this.make_invoice_bar();
    this.initialize_numpad();
    this.bind_events();
    this.attach_shortcuts();
  }

  prepare_dom() {
    this.wrapper.append(
      `<section class="payment-container">
        <div class="disable-payment">
          <div class="section-label"><span>${__(
            "Invoice required before Payment!"
          )}</span></div>
        </div>
        <div class="section-label">
				  <div class="payment-section">${__("Payment Method")}</div>
				  <div class="invoice-section"></div>
        </div>
				<div class="payment-modes"></div>
				<div class="fields-numpad-container">
					<div class="fields-section">
						<div class="section-label">${__("Additional Information")}</div>
						<div class="invoice-fields"></div>
					</div>
					<div class="number-pad"></div>
				</div>
				<div class="totals-section">
					<div class="totals"></div>
				</div>
				<div class="actions">
					${
            !this.is_retail
              ? `<div class="invoice-order-btn">${__("Invoice")}</div>`
              : ""
          }
					<div class="submit-order-btn" style="${
            this.is_retail
              ? "grid-column: span 10 / span 10"
              : "grid-column: span 6 / span 6"
          }">${__("Payment")}</div>
				</div>
			</section>`
    );
    this.$component = this.wrapper.find(".payment-container");
    this.$payment_modes = this.$component.find(".payment-modes");
    this.$totals_section = this.$component.find(".totals-section");
    this.$totals = this.$component.find(".totals");
    this.$numpad = this.$component.find(".number-pad");
    this.$invoice_fields_section = this.$component.find(".fields-section");
  }

  make_invoice_fields_control() {
    frappe.db.get_doc("POS Settings", undefined).then((doc) => {
      const fields = doc.invoice_fields;
      if (!fields.length) return;

      this.$invoice_fields =
        this.$invoice_fields_section.find(".invoice-fields");
      this.$invoice_fields.html("");
      const frm = this.events.get_frm();

      fields.forEach((df) => {
        this.$invoice_fields.append(
          `<div class="invoice_detail_field ${df.fieldname}-field" data-fieldname="${df.fieldname}"></div>`
        );
        let df_events = {
          onchange: function () {
            frm.set_value(this.df.fieldname, this.get_value());
          },
        };
        if (df.fieldtype == "Button") {
          df_events = {
            click: function () {
              if (
                frm.script_manager.has_handlers(df.fieldname, frm.doc.doctype)
              ) {
                frm.script_manager.trigger(
                  df.fieldname,
                  frm.doc.doctype,
                  frm.doc.docname
                );
              }
            },
          };
        }

        this[`${df.fieldname}_field`] = frappe.ui.form.make_control({
          df: {
            ...df,
            ...df_events,
          },
          parent: this.$invoice_fields.find(`.${df.fieldname}-field`),
          render_input: true,
        });
        this[`${df.fieldname}_field`].set_value(frm.doc[df.fieldname]);
      });
    });
  }
  initialize_numpad() {
    const me = this;
    this.number_pad = new ditech.POS.NumberPad({
      wrapper: this.$numpad,
      events: {
        numpad_event: function ($btn) {
          me.on_numpad_clicked($btn);
        },
      },
      cols: 3,
      keys: [
        [1, 2, 3],
        [4, 5, 6],
        [7, 8, 9],
        [".", 0, "Delete"],
      ],
    });

    this.numpad_value = "";
  }

  on_numpad_clicked($btn) {
    const button_value = $btn.attr("data-button-value");

    highlight_numpad_btn($btn);
    this.numpad_value =
      button_value === "delete"
        ? String(this.numpad_value).slice(0, -1)
        : this.numpad_value + button_value;
    this.selected_mode.$input.get(0).focus();
    this.selected_mode.set_value(this.numpad_value);

    function highlight_numpad_btn($btn) {
      $btn.addClass("shadow-base-inner bg-selected");
      setTimeout(() => {
        $btn.removeClass("shadow-base-inner bg-selected");
      }, 100);
    }
  }

  bind_events() {
    const me = this;

    this.$payment_modes.on("click", ".mode-of-payment", function (e) {
      const mode_clicked = $(this);
      const mode = mode_clicked.attr("data-mode");
      const mode_of_payment = unescape(
        mode_clicked.attr("data-mode_of_payment")
      );
      if (
        mode_clicked.find(`.${mode} .primary-currency input:focus`).length > 0
      ) {
        me.selected_mode = me[`${mode}_control`];
        me.selected_mode && me.selected_mode.$input?.get(0).focus();
      }
      if (
        mode_clicked.find(`.${mode} .second-currency input:focus`).length > 0
      ) {
        me.selected_mode = me[`${mode}_second_control`];
        me.selected_mode && me.selected_mode.$input?.get(0).focus();
      }
      me.numpad_value = me.selected_mode?.get_value() || 0;

      // if clicked element doesn't have .mode-of-payment class then return
      if (!$(e.target).is(mode_clicked)) return;
      const scrollLeft =
        mode_clicked.offset().left -
        me.$payment_modes.offset().left +
        me.$payment_modes.scrollLeft() -
        me.$payment_modes.width() / 2 +
        mode_clicked.outerWidth() / 2;
      me.$payment_modes.animate({ scrollLeft });

      // hide all control fields and shortcuts
      $(`.mode-of-payment-control`).css("display", "none");
      $(`.cash-shortcuts`).css("display", "none");
      me.$payment_modes.find(`.pay-amount`).css("display", "inline");
      me.$payment_modes.find(`.loyalty-amount-name`).css("display", "none");

      // remove highlight from all mode-of-payments
      $(".mode-of-payment").removeClass("border-primary");
      $(".mode-of-payment").parent().css({
        "min-width": "40%",
      });
      me.$payment_modes.find(`.payment-qrcode`).html("");

      if (mode_clicked.hasClass("border-primary")) {
        // clicked one is selected then unselect it

        mode_clicked.removeClass("border-primary");
        me.selected_mode = "";
      } else {
        // clicked one is not selected then select it
        const second_currency = me.events.get_frm().doc.custom_second_currency;
        mode_clicked.parent().css({
          "min-width": second_currency ? "55%" : "40%",
        });
        mode_clicked.addClass("border-primary");
        mode_clicked.find(".mode-of-payment-control").css("display", "flex");
        mode_clicked.find(".cash-shortcuts").css("display", "grid");
        me.$payment_modes.find(`.${mode}-amount`).css("display", "none");
        me.$payment_modes.find(`.${mode}-name`).css("display", "inline");

        me.selected_mode = me[`${mode}_control`];
        me.selected_mode && me.selected_mode.$input.get(0).focus();

        me.numpad_value = me.selected_mode?.get_value() || 0;

        frappe.db.get_value(
          "Mode of Payment",
          mode_of_payment,
          "custom_bank_account",
          (r) => {
            if (r.custom_bank_account) {
              mode_clicked
                .find(`.payment-qrcode`)
                .html(
                  `<button class="btn btn-xs btn-secondary btn-qrcode" data-bank_account="${escape(
                    r.custom_bank_account
                  )}">${__("QR Code")}</button>`
                );
            }
          }
        );
      }
    });

    frappe.ui.form.on("POS Invoice", "contact_mobile", (frm) => {
      const contact = frm.doc.contact_mobile;
      const request_button = $(this.request_for_payment_field?.$input[0]);
      if (contact) {
        request_button.removeClass("btn-default").addClass("btn-primary");
      } else {
        request_button.removeClass("btn-primary").addClass("btn-default");
      }
    });

    frappe.ui.form.on("POS Invoice", "coupon_code", (frm) => {
      if (frm.doc.coupon_code && !frm.applying_pos_coupon_code) {
        if (!frm.doc.ignore_pricing_rule) {
          frm.applying_pos_coupon_code = true;
          frappe.run_serially([
            () => (frm.doc.ignore_pricing_rule = 1),
            () => frm.trigger("ignore_pricing_rule"),
            () => (frm.doc.ignore_pricing_rule = 0),
            () => frm.trigger("apply_pricing_rule"),
            () => frm.save(),
            () => this.update_totals_section(frm.doc),
            () => (frm.applying_pos_coupon_code = false),
          ]);
        } else if (frm.doc.ignore_pricing_rule) {
          frappe.show_alert({
            message: __(
              "Ignore Pricing Rule is enabled. Cannot apply coupon code."
            ),
            indicator: "orange",
          });
        }
      }
    });

    this.setup_listener_for_payments();

    this.$payment_modes.on("click", ".btn-qrcode", function () {
      const bank_account = unescape($(this).attr("data-bank_account"));
      const mode = $(this).closest(".mode-of-payment").attr("data-mode");
      me.get_payment_qrcode(bank_account, mode);
    });

    this.$payment_modes.on("click", ".shortcut", function () {
      const value = $(this).attr("data-value");
      me.selected_mode.set_value(value);
    });

    this.$component.on("click", ".invoice-order-btn", () => {
      const doc = this.events.get_frm().doc;
      const items = doc.items;

      if (!items.length) {
        const message = __("You cannot invoice empty order.");
        frappe.show_alert({ message, indicator: "orange" });
        frappe.utils.play_sound("error");
        return;
      }
      this.print_invoice();
    });
    this.$component.on("click", ".submit-order-btn", () => {
      const doc = this.events.get_frm().doc;
      const paid_amount = doc.paid_amount;
      const grand_total = doc.grand_total;
      const items = doc.items;

      if (paid_amount == 0 || !items.length) {
        const message = items.length
          ? __("You cannot submit the order without payment.")
          : __("You cannot submit empty order.");
        frappe.show_alert({ message, indicator: "orange" });
        frappe.utils.play_sound("error");
        return;
      }

      if (paid_amount < grand_total) {
        const message = __("Payment cannot be less than the grand total.");
        frappe.show_alert({ message, indicator: "orange" });
        frappe.utils.play_sound("error");
        return;
      }

      if (!doc.custom_is_invoice && !this.is_retail) {
        return;
      }

      this.events.submit_invoice();
    });

    frappe.ui.form.on("POS Invoice", "loyalty_amount", (frm) => {
      const formatted_currency = format_currency(frm.doc.loyalty_amount);
      this.$payment_modes
        .find(`.loyalty-amount-amount`)
        .html(formatted_currency);
    });
  }

  get_payment_qrcode(bank_account, mode) {
    const frm = this.events.get_frm();
    this.selected_mode = this[`${mode}_control`];
    this.selected_mode && this.selected_mode.$input.get(0).focus();
    const timeout = 60000;
    let timeLeft = timeout / 1000;

    let data = {
      bank_account: bank_account,
      cashier: frappe.session.user,
      ref_doc: frm.doctype,
      ref_no: frm.doc.name,
      currency: frm.doc.currency,
      amount: frm.doc.grand_total,
      party_type: "Customer",
      party: frm.doc.customer,
      timeout: timeout,
    };

    frappe.call({
      method: "ditech_core.ditech_core.pos.get_payment_qrcode",
      frezze: true,
      args: {
        data: data,
      },
      callback: (r) => {
        if (r?.message) {
          let countdown;
          let dialog = new frappe.ui.Dialog({
            title: __("Waiting for Payment"),
            static: true,
            size: "small",
            fields: [
              {
                fieldtype: "HTML",
                fieldname: "timer_payment",
              },
            ],
            secondary_action_label: __("Cancel"),
            secondary_action: () => {
              frappe.call({
                method: "ditech_core.ditech_core.pos.clear_payment_qr",
                freeze: true,
                callback: () => {
                  if (countdown) clearInterval(countdown);
                  dialog.hide();
                },
              });
            },
          });
          dialog.show();

          const timer_payment = dialog.fields_dict.timer_payment.$wrapper;
          timer_payment.html(timer_payment_html(timeLeft));
          countdown = setInterval(function () {
            timeLeft--;
            timer_payment.find(".timer").text(timeLeft);
            if (!Boolean(timeLeft % 2))
              frappe.call({
                method:
                  "ditech_core.ditech_core.pos.check_transaction_payment_job",
                args: {
                  data: { ...data, ...r.message },
                },
                callback: (r) => {
                  if (r?.message) {
                    clearInterval(countdown);
                    this.selected_mode.set_value(data.amount);
                    this.events.submit_invoice();
                    dialog.hide();
                  }
                },
              });
            if (timeLeft <= 0) {
              clearInterval(countdown);
              dialog.hide();
            }
          }, 1000);
        }
      },
    });

    function timer_payment_html(time) {
      return `<div class="timer" style="text-align: center;font-size: var(--text-10xl);font-weight: var(--weight-semibold);">${time}</div>`;
    }
  }

  setup_listener_for_payments() {
    frappe.realtime.on("process_phone_payment", (data) => {
      const doc = this.events.get_frm().doc;
      const { response, amount, success, failure_message } = data;
      let message, title;

      if (success) {
        title = __("Payment Received");
        const grand_total = cint(frappe.sys_defaults.disable_rounded_total)
          ? doc.grand_total
          : doc.rounded_total;
        if (amount >= grand_total) {
          frappe.dom.unfreeze();
          message = __("Payment of {0} received successfully.", [
            format_currency(amount, doc.currency),
          ]);
          this.events.submit_invoice();
          cur_frm.reload_doc();
        } else {
          message = __(
            "Payment of {0} received successfully. Waiting for other requests to complete...",
            [format_currency(amount, doc.currency)]
          );
        }
      } else if (failure_message) {
        message = failure_message;
        title = __("Payment Failed");
      }

      frappe.msgprint({ message: message, title: title });
    });
  }

  attach_shortcuts() {
    const ctrl_label = frappe.utils.is_mac() ? "⌘" : "Ctrl";
    this.$component
      .find(".submit-order-btn")
      .attr("title", `${ctrl_label}+Enter`);
    frappe.ui.keys.on("ctrl+enter", () => {
      const payment_is_visible = this.$component.is(":visible");
      const active_mode = this.$payment_modes.find(".border-primary");
      if (payment_is_visible && active_mode.length) {
        this.$component.find(".submit-order-btn").click();
      }
    });

    frappe.ui.keys.add_shortcut({
      shortcut: "tab",
      action: () => {
        const payment_is_visible = this.$component.is(":visible");
        let active_mode = this.$payment_modes.find(".border-primary");
        active_mode = active_mode.length
          ? active_mode.attr("data-mode")
          : undefined;

        if (!active_mode) return;

        const mode_of_payments = Array.from(
          this.$payment_modes.find(".mode-of-payment")
        ).map((m) => $(m).attr("data-mode"));
        const mode_index = mode_of_payments.indexOf(active_mode);
        const next_mode_index = (mode_index + 1) % mode_of_payments.length;
        const next_mode_to_be_clicked = this.$payment_modes.find(
          `.mode-of-payment[data-mode="${mode_of_payments[next_mode_index]}"]`
        );

        if (payment_is_visible && mode_index != next_mode_index) {
          next_mode_to_be_clicked.click();
        }
      },
      condition: () =>
        this.$component.is(":visible") &&
        this.$payment_modes.find(".border-primary").length,
      description: __("Switch Between Payment Modes"),
      ignore_inputs: true,
      page: cur_page.page.page,
    });
  }
  
  async print_invoice() {
    const frm = this.events.get_frm();
    await this.events.save_and_invoice();
    if (!frm.doc.custom_is_invoice) {
      await this.update_status_invoice(frm);
    }
    if (this.invoice)
      frappe.utils.print(
        frm.doc.doctype,
        frm.doc.name,
        this.invoice,
        frm.doc.letter_head,
        frm.doc.language || frappe.boot.lang
      );
  }

  async update_status_invoice(frm) {
    await frappe.call({
      method: "ditech_core.ditech_core.pos.update_table_invoice",
      args: {
        name: frm.doc.name,
        table_name: frm.doc.custom_pos_table,
      },
      frezze: true,
    });
    await frm.reload_doc();
    this.checkout();
    this.events.load_after_invoice();
    this.$component.find(".submit-order-btn").css({
      "background-color": frm.doc.custom_is_invoice
        ? "var(--blue-500)"
        : "var(--blue-200)",
    });
    this.$component
      .find(".payment-section, .payment-modes, .fields-numpad-container")
      .css({
        visibility: frm.doc.custom_is_invoice ? "visible" : "hidden",
      });
    this.$component.find(".disable-payment").css({
      display: frm.doc.custom_is_invoice ? "none" : "flex",
    });
  }

  render_payment_section() {
    this.render_payment_mode_dom();
    this.make_invoice_fields_control();
    this.update_totals_section();
    this.focus_on_default_mop();
  }

  after_render() {
    const frm = this.events.get_frm();
    frm.script_manager.trigger(
      "after_payment_render",
      frm.doc.doctype,
      frm.doc.docname
    );
  }

  edit_cart() {
    this.events.toggle_other_sections(false);
    this.toggle_component(false);
  }

  checkout() {
    this.events.toggle_other_sections(true);
    this.toggle_component(true);
    this.render_payment_section();
    this.after_render();
  }

  toggle_remarks_control() {
    if (this.$remarks.find(".frappe-control").length) {
      this.$remarks.html("+ Add Remark");
    } else {
      this.$remarks.html("");
      this[`remark_control`] = frappe.ui.form.make_control({
        df: {
          label: __("Remark"),
          fieldtype: "Data",
          onchange: function () {},
        },
        parent: this.$totals_section.find(`.remarks`),
        render_input: true,
      });
      this[`remark_control`].set_value("");
    }
  }

  render_payment_mode_dom() {
    const doc = this.events.get_frm().doc;
    const payments = doc.payments;
    const currency = doc.currency;
    const second_currency = doc.custom_second_currency;

    this.$payment_modes.html(
      `${payments
        .map((p, i) => {
          const mode = p.mode_of_payment.replace(/ +/g, "_").toLowerCase();
          const payment_type = p.type;

          return `
					<div class="payment-mode-wrapper">
						<div class="mode-of-payment" data-mode="${mode}" data-mode_of_payment="${escape(
            p.mode_of_payment
          )}" data-payment-type="${payment_type}">
							${p.mode_of_payment} 
							<div class="${mode}-amount pay-amount"></div>
              <div class="${mode} mode-of-payment-control">
                <div class="${mode} primary-currency" style="${
            second_currency && second_currency != currency
              ? "width: 50%;"
              : "width: 100%; margin-top: 4px;"
          }"></div>
                ${
                  second_currency && second_currency != currency
                    ? `<div class="${mode} second-currency" style="width: 50%;"></div>`
                    : ""
                }
              </div>
              <span class="payment-qrcode"></span>
						</div>
					</div>
				`;
        })
        .join("")}`
    );

    payments.forEach((p) => {
      const mode = p.mode_of_payment.replace(/ +/g, "_").toLowerCase();
      const me = this;
      this[`${mode}_control`] = frappe.ui.form.make_control({
        df: {
          label: currency,
          fieldtype: "Currency",
          placeholder: __("Enter {0} amount.", [p.mode_of_payment]),
          options: currency,
          onchange: function () {
            frappe.model
              .set_value(
                p.doctype,
                p.name,
                "custom_primary_amount",
                flt(this.value)
              )
              .then(() => set_amount_payment());
          },
        },
        parent: this.$payment_modes.find(`.${mode}.primary-currency`),
        render_input: true,
      });

      if (!second_currency || second_currency == currency)
        this[`${mode}_control`].toggle_label(false);

      if (second_currency && second_currency != currency) {
        this[`${mode}_second_control`] = frappe.ui.form.make_control({
          df: {
            label: second_currency,
            fieldtype: "Currency",
            placeholder: __("Enter {0} amount.", [p.mode_of_payment]),
            options: second_currency,
            onchange: function () {
              frappe.model
                .set_value(
                  p.doctype,
                  p.name,
                  "custom_second_amount",
                  flt(this.value)
                )
                .then(() => set_amount_payment());
            },
          },
          parent: this.$payment_modes.find(`.${mode}.second-currency`),
          render_input: true,
        });
      }

      function set_amount_payment() {
        const primary_value = me[`${mode}_control`].get_value() || 0;
        const second_value =
          (second_currency &&
            second_currency != currency &&
            me[`${mode}_second_control`].get_value()) ||
          0;
        frappe.model
          .set_value(
            p.doctype,
            p.name,
            "amount",
            flt(primary_value) + flt(second_value) / flt(me.exchange_rate)
          )
          .then(() => me.update_totals_section());
        const formatted_primary_currency = format_currency(
          primary_value,
          currency
        );
        const formatted_second_currency = format_currency(
          second_value,
          second_currency
        );
        me.$payment_modes
          .find(`.${mode}-amount`)
          .html(
            `<span>${primary_value > 0 ? formatted_primary_currency : ""} ${
              primary_value > 0 && second_value > 0 ? " + " : ""
            } ${second_value > 0 ? formatted_second_currency : ""} </span>`
          );
      }
    });

    this.render_loyalty_points_payment_mode();
  }

  focus_on_default_mop() {
    const doc = this.events.get_frm().doc;
    const payments = doc.payments;
    payments.forEach((p) => {
      const mode = p.mode_of_payment.replace(/ +/g, "_").toLowerCase();
      if (p.default) {
        setTimeout(() => {
          this.$payment_modes
            .find(`.${mode}.mode-of-payment-control`)
            .parent()
            .click();
        }, 500);
      }
    });
  }

  attach_cash_shortcuts(doc) {
    const grand_total = cint(frappe.sys_defaults.disable_rounded_total)
      ? doc.grand_total
      : doc.rounded_total;
    const currency = doc.currency;

    const shortcuts = this.get_cash_shortcuts(flt(grand_total));

    this.$payment_modes.find(".cash-shortcuts").remove();
    let shortcuts_html = shortcuts
      .map((s) => {
        return `<div class="shortcut" data-value="${s}">${format_currency(
          s,
          currency
        )}</div>`;
      })
      .join("");

    this.$payment_modes
      .find('[data-payment-type="Cash"]')
      .find(".mode-of-payment-control")
      .after(`<div class="cash-shortcuts">${shortcuts_html}</div>`);
  }

  get_cash_shortcuts(grand_total) {
    let steps = [1, 5, 10];
    const digits = String(Math.round(grand_total)).length;

    steps = steps.map((x) => x * 10 ** (digits - 2));

    const get_nearest = (amount, x) => {
      let nearest_x = Math.ceil(amount / x) * x;
      return nearest_x === amount ? nearest_x + x : nearest_x;
    };

    return steps.reduce((finalArr, x) => {
      let nearest_x = get_nearest(grand_total, x);
      nearest_x = finalArr.indexOf(nearest_x) != -1 ? nearest_x + x : nearest_x;
      return [...finalArr, nearest_x];
    }, []);
  }

  render_loyalty_points_payment_mode() {
    const me = this;
    const doc = this.events.get_frm().doc;
    const { loyalty_program, loyalty_points, conversion_factor } =
      this.events.get_customer_details();

    this.$payment_modes
      .find(`.mode-of-payment[data-mode="loyalty-amount"]`)
      .parent()
      .remove();

    if (!loyalty_program) return;

    let description, read_only, max_redeemable_amount;
    if (!loyalty_points) {
      description = __("You don't have enough points to redeem.");
      read_only = true;
    } else {
      max_redeemable_amount = flt(
        flt(loyalty_points) * flt(conversion_factor),
        precision("loyalty_amount", doc)
      );
      description = __("You can redeem upto {0}.", [
        format_currency(max_redeemable_amount),
      ]);
      read_only = false;
    }

    const amount =
      doc.loyalty_amount > 0 ? format_currency(doc.loyalty_amount) : "";
    this.$payment_modes.append(
      `<div class="payment-mode-wrapper">
				<div class="mode-of-payment loyalty-card" data-mode="loyalty-amount" data-payment-type="loyalty-amount">
					Redeem Loyalty Points
					<div class="loyalty-amount-amount pay-amount">${amount}</div>
					<div class="loyalty-amount-name">${loyalty_program}</div>
					<div class="loyalty-amount mode-of-payment-control"></div>
				</div>
			</div>`
    );

    this["loyalty-amount_control"] = frappe.ui.form.make_control({
      df: {
        label: __("Redeem Loyalty Points"),
        fieldtype: "Currency",
        placeholder: __("Enter amount to be redeemed."),
        options: "company:currency",
        read_only,
        onchange: async function () {
          if (!loyalty_points) return;

          if (this.value > max_redeemable_amount) {
            frappe.show_alert({
              message: __("You cannot redeem more than {0}.", [
                format_currency(max_redeemable_amount),
              ]),
              indicator: "red",
            });
            frappe.utils.play_sound("submit");
            me["loyalty-amount_control"].set_value(0);
            return;
          }
          const redeem_loyalty_points = this.value > 0 ? 1 : 0;
          await frappe.model.set_value(
            doc.doctype,
            doc.name,
            "redeem_loyalty_points",
            redeem_loyalty_points
          );
          frappe.model
            .set_value(
              doc.doctype,
              doc.name,
              "loyalty_points",
              parseInt(this.value / conversion_factor)
            )
            .then(() => {
              let row = doc.payments.find((p) => p.default);
              if (row)
                me[
                  `${row.mode_of_payment
                    .replace(/ +/g, "_")
                    .toLowerCase()}_control`
                ].set_value(row.amount);
            });
        },
        description,
      },
      parent: this.$payment_modes.find(
        `.loyalty-amount.mode-of-payment-control`
      ),
      render_input: true,
    });
    this["loyalty-amount_control"].toggle_label(false);
  }

  render_add_payment_method_dom() {
    const docstatus = this.events.get_frm().doc.docstatus;
    if (docstatus === 0)
      this.$payment_modes.append(
        `<div class="w-full pr-2">
					<div class="add-mode-of-payment w-half text-grey mb-4 no-select pointer">+ Add Payment Method</div>
				</div>`
      );
  }

  update_totals_section(doc) {
    if (!doc) doc = this.events.get_frm().doc;
    const paid_amount = doc.paid_amount;
    const grand_total = cint(frappe.sys_defaults.disable_rounded_total)
      ? doc.grand_total
      : doc.rounded_total;
    const remaining = grand_total - doc.paid_amount;
    const change =
      doc.change_amount || remaining <= 0 ? -1 * remaining : undefined;
    const currency = doc.currency;
    const second_currency = doc.custom_second_currency;
    const label = change ? __("Change") : __("To Be Paid");

    this.$totals.html(
      `<div class="col">
				<div class="total-label">${__("Grand Total")}</div>
				<div class="value">${format_currency(grand_total, currency)}${exchange(
        this,
        grand_total
      )}</div>
			</div>
			<div class="seperator-y"></div>
			<div class="col">
				<div class="total-label">${__("Paid Amount")}</div>
				<div class="value">${format_currency(paid_amount, currency)}${exchange(
        this,
        paid_amount
      )}</div>
			</div>
			<div class="seperator-y"></div>
			<div class="col">
				<div class="total-label">${label}</div>
				<div class="value">${format_currency(change || remaining, currency)}${exchange(
        this,
        change || remaining
      )}</div>
			</div>`
    );

    function exchange(me, value) {
      let second_total = "";
      if (second_currency) {
        second_total = `<div>${format_currency(
          me.exchange_rate * value,
          second_currency
        )}</div>`;
      }
      return second_total;
    }
  }

  clear_payments() {
    let doc = this.events.get_frm()?.doc;
    if (doc)
      setTimeout(() => {
        doc.payments.forEach((p) => {
          frappe.model.set_value(p.doctype, p.name, "amount", 0);
        });
      }, 300);
  }

  toggle_component(show) {
    const doc = this.events.get_frm()?.doc;
    if (!this.is_retail && show && doc) {
      this.$component.find(".submit-order-btn").css({
        "background-color": doc.custom_is_invoice
          ? "var(--blue-500)"
          : "var(--blue-200)",
      });
      this.$component
        .find(".payment-section, .payment-modes, .fields-numpad-container")
        .css({
          visibility: doc.custom_is_invoice ? "visible" : "hidden",
        });
      this.$component.find(".disable-payment").css({
        display: doc.custom_is_invoice ? "none" : "flex",
      });
    } else if (this.is_retail && show)
      this.$component.find(".submit-order-btn").css({
        "background-color": "var(--blue-500)",
      });
    show
      ? this.$component.css("display", "flex")
      : this.$component.css("display", "none");
    show && this.clear_payments();
  }
};
