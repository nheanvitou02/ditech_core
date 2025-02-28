frappe.pages["target-vs-actual-das"].on_page_load = function (wrapper) {
    new DepartmentSaleDashboard(wrapper);
};

// Define the DepartmentSaleDashboard class
let DepartmentSaleDashboard = Class.extend({
    // Initialize the dashboard page
    init: function (wrapper) {
        this.page = frappe.ui.make_app_page({
            parent: wrapper,
            title: __("Target Vs Actual Dashboard"),
            single_column: true,
        });
        this.make();
    },
    
    // Setup the dashboard by rendering templates and fetching data
    make: async function () {
        let rendered_html = frappe.render_template("target_vs_actual_das", {});
        $(rendered_html).appendTo(this.page.main);

        await this.get_actual(); 
        await this.get_fiscal_years();
        await this.get_sales_person();
        await this.bind_filter_events();
        await this.get_sales_person_group(); 

    },
    // Fetch actual total targets
    get_actual: async function () {
        try {
            // Empty the content before fetching new data
            this.page.main.find("#totalActualCardsQty").empty();
    
            let { message: total_actual } = await frappe.call({
                method: "ditech_core.ditech_core.page.target_vs_actual_das.sales_person_das.get_total_target_doc",
            });
    
           this.card_html_total_actual(total_actual)
        } catch (error) {
            frappe.msgprint(__("Error occurred while fetching total actual targets") + "<br><br>" + error.message, __("Error"));
        }
    },
    

    // Fetch fiscal years
    get_fiscal_years: async function () {
        try {
            let { message: fiscal_years } = await frappe.call({
                method: "frappe.client.get_list",
                args: {
                    doctype: "Fiscal Year",
                    fields: ["name"]
                }
            });
            if (fiscal_years) {
                let fiscal_year_dropdown = $("#fiscalYearQty");
                fiscal_year_dropdown.empty(); // Clear existing options
                const currentYear = new Date().getFullYear().toString();
                fiscal_years.forEach(fiscal_year => {
                    let isSelected = currentYear;
                    fiscal_year_dropdown.append(new Option(fiscal_year.name, fiscal_year.name, isSelected, isSelected));
                });
            }
        } catch (error) {
            frappe.msgprint({ message: error.message, title: __("Error"), indicator: "red" });
        }
    },
    get_sales_person_group: async function () {
        try {
            let { message: sales_person_groups } = await frappe.call({
                method: "frappe.client.get_list",
                args: {
                    doctype: "Sales Person",
                    filters: {is_group: 1},
                    fields: ["name"]
                }
            });
            if (sales_person_groups) {
                let filter_group_dropdown = $("#filterGroupQty");
                filter_group_dropdown.empty(); // Clear existing options
                filter_group_dropdown
                    .append($("<option>", { value: "", text: "Select a Group", style: "color: gray", disabled: true, selected: true}))
                    .append($("<option>", { value: "", text: "All Sales Persons"}))
                    .append($("<option>", { value: "All Groups", text: "All Groups" }))
                    .append(
                        sales_person_groups.map(sales_person_group => $("<option>", { value: sales_person_group.name, text: sales_person_group.name }))
                    );
            }
        } catch (error) {
            frappe.msgprint({ message: error.message, title: __("Error"), indicator: "red" });
        }
    },
    
    // Fetch sales person data
    get_sales_person: async function () {
        try {
            let { message: sales_person_api } = await frappe.call({
                method: "ditech_core.ditech_core.page.target_vs_actual_das.sales_person_das.get_target_sales_person",
                args: { filter_view: "Year",filter_is_qty:1 },
            });
            this.card_html_sales_person(sales_person_api)
        } catch (error) {
            frappe.msgprint({ message: error.message, title: __("Error"), indicator: "red" });
        }
    },

    // Bind filter button events
  bind_filter_events: function () {
        let selected_filter_view = "Year"; // Default filter view
    
        $("#filterYear").on("click", () => {
            selected_filter_view = "Year";
            this.handle_filter_request(selected_filter_view);
        });
        $("#filterSemester").on("click", () => {
            selected_filter_view = "Semester";
            this.handle_filter_request(selected_filter_view);
        });
        $("#filterQuater").on("click", () => {
            selected_filter_view = "Quarterly";
            this.handle_filter_request(selected_filter_view);
        });
        $("#filterMonthly").on("click", () => {
            selected_filter_view = "Monthly";
            this.handle_filter_request(selected_filter_view);
        });
        $("#fiscalYearQty").on("change", () => {
            this.handle_filter_request(selected_filter_view);
        });
        $("#filterGroupQty").on("change", () => {
            this.handle_filter_request(selected_filter_view);
        });

    },
    
    // Handle filter requests and update sales person data
    handle_filter_request: async function (filter_view) {
        try {
            let filter_fiscal_year = $("#fiscalYearQty").val();
            let filter_group_name = $("#filterGroupQty").val() || "";
            let { message: sales_person_api } = await frappe.call({
                method: "ditech_core.ditech_core.page.target_vs_actual_das.sales_person_das.get_target_sales_person",
                args: {
                    filter_is_qty:1,
                    filter_view,
                    filter_group_name,
                    filter_fiscal_year },
            });
            if (filter_group_name !== "") {
                this.card_html_sales_person_group(sales_person_api);
            } else if (sales_person_api) {
                this.card_html_sales_person(sales_person_api);
            }

        } catch (error) {
            frappe.msgprint({ message: error.message, title: __("Error"), indicator: "red" });
        }
    },
    // Create DOM elements for total actual data
    card_html_total_actual: async function (total_actual) {
        let totalActualCardsQty = this.page.main.find("#totalActualCardsQty");
        $.each(total_actual.message, function (index, item_group) {
            let docTypeUrl = total_actual.page_uql[index.toLowerCase().replace(/ /g, '-')];
            let cardHtml = `
                <div class="col-xl-3 col-md-6 mb-4">
                    <a class="text-decoration-none" href="${frappe.urllib.get_base_url()}/${docTypeUrl}" target="_blank" rel="noopener noreferrer">
                        <div class="card custom-card shadow h-100 py-2">
                            <div class="card-body">
                                <div class="row no-gutters align-items-center">
                                    <div class="col mr-2">
                                        <div class="text-2xl font-weight-bold text-primary text-uppercase mb-1">${index}</div>
                                        <div class="h3 mb-0 font-weight-bold text-gray-800" id="earnings">${item_group}</div>
                                    </div>
                                    <div class="col-auto">
                                        ${
                                            index === "Lead" ? '<i class="fas fa-user fa-2x text-primary"></i>' :
                                            index === "Opportunity" ? '<i class="fas fa-briefcase fa-2x text-success"></i>' :
                                            index === "Quotation" ? '<i class="fas fa-file-invoice fa-2x text-info"></i>' :
                                            index === "Sales Order" ? '<i class="fas fa-shopping-cart fa-2x text-warning"></i>' :
                                            index === "Sales Invoice" ? '<i class="fas fa-file-invoice fa-2x text-danger"></i>' : ''
                                        }
                                    </div>
                                </div>
                            </div>
                        </div>
                    </a>
                </div>
            `;
            totalActualCardsQty.append(cardHtml);
        });
    },
    // Function to display "no data found" message
display_no_data_found: async function () {
    let main_group = this.page.main.find(".main_group");
    let no_data_html = `
       <div class="no_data_found text-center">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 80" fill="none">
            <rect x="2" y="2" width="60" height="76" rx="4" fill="#fff" stroke="#d1d5db" stroke-width="2"/>
            <path d="M48 2H62V16L48 2Z" fill="#f8f9fa" stroke="#d1d5db" stroke-width="2"/>
            </svg>
            <h2>NOTHING!</h2>
            <p>Your collection list is empty.</p>
       </div>`;
    main_group.html(no_data_html);
},
// Create DOM elements for sales person groups
card_html_sales_person: async function (sales_person_api) {
    let sales_person_container = this.page.main.find("#salesPersonContainerQty");
    let sales_person_data = sales_person_api.combine_data;
    sales_person_container.html('<div class="main_group p-3 "></div>');
    
    let all_empty = true;
    let self = this;
    $.each(sales_person_data, function (index, sales_person) {
        let target_docs = sales_person.target_docs;
        if (target_docs.length != 0) {
            all_empty = false;
            let sales_person_group_html = `
              <div class="sale-person-group border p-3 mt-3 rounded bg-light">
                <div class="d-sm-flex align-items-center justify-content-between mb-4">
                  <h1 class="h3 mb-0 text-gray-800 pt-3 w-100 text-center font-weight-bold">${sales_person.sales_person}</h1>
                </div>
        
                <!-- Chart and Summary Row -->
                <div class="row">
            `;
    
            $.each(target_docs, function (docIndex, target_doc) {
                sales_person_group_html += `
                <div class="col-xl-6 col-md-12 mb-4 item_groups">
                  <div class="card sales-person-card shadow h-100 py-2">
                    <div class="card-body">
                      <div class="chart-area" style="height: 250px;" >
                        <canvas class="h-100" id="salesPerformanceChartQty${index + 1}_${docIndex + 1}"></canvas>
                      </div>
                    </div>
                  </div>
                </div>
              `;
            });
    
            sales_person_group_html += `
              </div> <!-- End of Chart and Summary Row -->
            </div> <!-- End of sales-person-group -->
            `;
    
            sales_person_container.find(".main_group").append(sales_person_group_html);
            self.chart_sales_person(target_docs, index);
        }
    });

    if (all_empty) {
        this.display_no_data_found();
    }
},

// Initialize charts for each sales person group
chart_sales_person: async function (target_docs, salesPersonIndex) {
    $.each(target_docs, function (docIndex, target_doc) {
        let ctx = document.getElementById(`salesPerformanceChartQty${salesPersonIndex + 1}_${docIndex + 1}`).getContext('2d');
        const { target_amount: amount, percentage_qty, actual_target, target_qty, chart_bar_label } = target_doc.chart_data;
            let salesChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: chart_bar_label,
                    datasets: [
                        {
                            label: "Actual Qty",
                            data: actual_target,
                            backgroundColor: '#d90429',
                            borderColor: '#d90429',
                            borderWidth: 1
                        },
                        {
                            label: "Targets Qty",
                            data: target_qty,
                            backgroundColor: '#03045e',
                            borderColor: '#03045e',
                            borderWidth: 1
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false, // Disable aspect ratio maintenance
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    },
                    plugins: {
                        title: {
                            display: true,
                            text: target_doc.item_group
                        },
                        legend: {
                            display: true,
                            position: 'top',
                        },
                        tooltip: {
                            callbacks: {
                                label: ({ dataset, dataIndex, raw }) => {
                                    const label = dataset.label ? `${dataset.label}: ` : '';
                                    const value = raw;
                                    const percentageText = dataset.label === 'Actual Qty' ? ` (${percentage_qty[dataIndex]}%)` : '';
                                    return `${label}${value}${percentageText}`;
                                },
                            },
                        },
                    },
                },
            });
    

    });
},
card_html_sales_person_group: async function (api_data){
    let sales_person_container = $("#salesPersonContainerQty");
    let sales_person_data = api_data.combine_data;
    sales_person_container.html('<div class="main_group p-3 "></div>')
    let all_empty = true;
    let self = this;
    $.each(sales_person_data, function (index, sales_person) {
        if (sales_person.summed_target_docs && Object.keys(sales_person.summed_target_docs).length !== 0){
            all_empty = false;
            let sales_person_group_html = `
            <div class="sale-person-group border p-3 mt-3 rounded bg-light">
              <div class="d-sm-flex align-items-center justify-content-between mb-4">
                <h1 class="h3 mb-0 text-gray-800 pt-3 w-100 text-center font-weight-bold">${sales_person.parent_sales_person}</h1>
              </div>
      
              <!-- Chart and Summary Row -->
              <div class="row">
          `;

            $.each(sales_person.summed_target_docs, function (docIndex, target_doc) {
                sales_person_group_html += `
                <div class="col-xl-6 col-md-12 mb-4 item_groups ">
                  <div class="card sales-person-card shadow h-100 py-2">
                    <div class="card-body">
                      <div class="chart-area" style="height: 250px;">
                        <canvas class="h-100" id="salesPerformanceChartQtyGroup${index + 1}_${docIndex + 1}"></canvas>
                      </div>
                    </div>
                  </div>
                </div>
              `;
            });

            sales_person_group_html += `
              </div> <!-- End of Chart and Summary Row -->
            </div> <!-- End of sales-person-group -->
            `;
            sales_person_container.find(".main_group").append(sales_person_group_html);
            self.chart_sales_person_group(sales_person.summed_target_docs, index);
        }
    });

    if (all_empty){
        this.display_no_data_found();
    }
},
chart_sales_person_group: async function (sales_person, sales_person_index) {
    $.each(sales_person, function (docIndex, target_doc) {
        let ctx = document.getElementById(`salesPerformanceChartQtyGroup${sales_person_index + 1}_${docIndex + 1}`).getContext('2d');
        const { target_qty, actual_qty, percentage_qty, chart_label } = target_doc.chart_data;
        const title_chart = docIndex;

            let salesChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: chart_label,
                    datasets: [{
                        label: "Actual Qty",
                        data: actual_qty,
                        backgroundColor: '#d90429',
                        borderColor: '#d90429',
                        borderWidth: 1
                    }, {
                        label: "Target Qty",
                        data: target_qty,
                        backgroundColor: '#03045e',
                        borderColor: '#03045e',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false, // Allow height customization
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    },
                    plugins: {
                        title: {
                            display: true,
                            text: title_chart
                        },
                        legend: {
                            display: true,
                            position: 'top'
                        },
                        tooltip: {
                            callbacks: {
                              label: ({ dataset, dataIndex, raw }) => {
                                const label = dataset.label ? `${dataset.label}: ` : '';
                                const value = raw;
                                const percentage = dataset.label === 'Actual Qty'? ` (${percentage_qty[dataIndex]}%)`: '';
                                return `${label}${value}${percentage}`;
                              },
                            },
                        }
                    }
                }
            });
    });
}

});
