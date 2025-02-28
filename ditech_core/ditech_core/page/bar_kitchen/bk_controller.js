ditech.BarKitchen.Controller = class {
  constructor(wrapper) {
    this.wrapper = $(wrapper).find(".layout-main-section");
    this.page = wrapper.page;

    this.check_opening_entry();
  }

  fetch_opening_entry() {
    return frappe.call("ditech_core.ditech_core.pos.check_bar_kitchen");
  }

  check_opening_entry() {
    this.fetch_opening_entry().then((r) => {
      if (r.message.length) {
        // assuming only one opening voucher is available for the current user
        // this.toggle_components(false);
        this.prepare_app_defaults(r.message[0]);
      } else {
        // this.create_opening_voucher();
        frappe.msgprint({
          title: __("Notification"),
          indicator: "red",
          message: __("Opening entry is not create"),
        });
      }
    });
  }

  async prepare_app_defaults(data) {
    this.pos_profile = data.pos_profile;
    this.item_stock_map = {};
    this.settings = {};
    this.key = data.pos_profile;

    frappe.call({
      method: "ditech_core.ditech_core.pos.get_pos_profile_data",
      args: { pos_profile: this.pos_profile },
      callback: (res) => {
        const profile = res.message;
        Object.assign(this.settings, profile);
        this.settings.customer_groups = profile.customer_groups.map(
          (group) => group.name
        );
        this.make_app();
      },
    });
  }

  make_app() {
    this.prepare_dom();
    this.prepare_components();
    this.set_pos_profile_status();
    this.prepare_menu();
    this.bind_events();
  }

  prepare_dom() {
    this.wrapper.append(`<div class="pos-app"></div>`);

    this.$components_wrapper = this.wrapper.find(".pos-app");
  }

  prepare_components() {
    this.init_bar_kitchen();
  }

  init_bar_kitchen() {
    this.bar_kitchen = new ditech.BarKitchen.BarKitchen({
      wrapper: this.$components_wrapper,
      pos_profile: this.pos_profile,
      settings: this.settings,
      events: {},
    });
  }

  prepare_menu() {
    this.page.clear_inner_toolbar();
    this.page.add_inner_button(`<span><svg class="icon icon-md" aria-hidden="true">
          <use class="" href="#icon-refresh"></use></svg></span>`, () => location.reload())
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
  bind_events() {
    this.page.$title_area.on("click", ".title-text", () =>
      frappe.set_route("/")
    );
    frappe.realtime.on(this.key, async (res) => {
      switch (res.type) {
        case "Refresh Kitchen":
          this.bar_kitchen.load_items_data();
          break;
        default:
          break;
      }
    });
  }
  set_pos_profile_status() {
    this.page.set_indicator(this.pos_profile, "blue");
  }
};
