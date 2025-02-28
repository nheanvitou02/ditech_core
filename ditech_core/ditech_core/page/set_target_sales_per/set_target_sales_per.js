frappe.pages['set-target-sales-per'].on_page_load = function(wrapper) {
    new setTargetSalesPerson(wrapper);
    document.addEventListener('keydown', function(event) {
        const btnSave = document.getElementById('btnSave');
        if (btnSave && btnSave.style.display !== 'none' && event.ctrlKey && event.key === 's') {
            event.preventDefault();
            save_data();
        }
    });
}
const setTargetSalesPerson = Class.extend({

    init: function (wrapper) {
        this.page = frappe.ui.make_app_page({
            parent: wrapper,
            title: __("Set Target Sales Person"),
            single_column: true,
        });
        this.make();
    },

    make: function () {
        $('.page-form').hide();
        let rendered_html = frappe.render_template("set_target_sales_per", {data:null});
        $(rendered_html).appendTo(this.page.main);
        this.add_fields();
    },

    add_fields: function () {
        const filterSection = this.page.main.find('#filterSection');
        const self = this; 
    
        // Fetch Sales Persons first
        frappe.call({
            method: "frappe.client.get_list",
            args: { doctype: "Sales Person", fields: ["name"] },
            callback: function (response) {
                let sales_persons = Array.isArray(response.message) ? response.message.map(sp => sp.name) : [];
                let sp_field = self.page.add_field({
                    fieldtype: "Autocomplete",
                    fieldname: "sales_person",
                    label: "Select Sales Person",
                    reqd: 1,
                    options: sales_persons
                });
                sp_field.$wrapper.appendTo(filterSection);
    
                // Now fetch Fiscal Years after Sales Person field is appended
                frappe.call({
                    method: "frappe.client.get_list",
                    args: { doctype: "Fiscal Year", fields: ["name"] },
                    callback: function (response) {
                        let fiscal_years = Array.isArray(response.message) ? response.message.map(fy => fy.name) : [];
                        let fy_field = self.page.add_field({
                            fieldtype: "Autocomplete",
                            fieldname: "fiscal_year",
                            label: "Select Fiscal Year",
                            reqd: 1,
                            options: fiscal_years,
                            default: 2025
                        });
                        fy_field.$wrapper.appendTo(filterSection);
    
                        // Add event listener after both fields are added
                        self.add_event_listener();
                    }
                });
            }
        });
    },
    

    add_event_listener: function () {
        const sales_person_field = this.page.fields_dict["sales_person"];
        const fiscal_year_field = this.page.fields_dict["fiscal_year"];
        if (sales_person_field && fiscal_year_field) {
            sales_person_field.$input.on('change', this.log_all_field_values.bind(this));
            fiscal_year_field.$input.on('change', this.log_all_field_values.bind(this));
        }
       
    },

    log_all_field_values: function () {
        const sales_person = this.page.fields_dict.sales_person.get_value();
        const fiscal_year = this.page.fields_dict.fiscal_year.get_value();
        this.get_get_target();
    },

    get_get_target: function () {
        const self = this;
        frappe.call({
            method: "ditech_core.ditech_core.page.set_target_sales_per.set_target_sales_per.get_target_team",
            args: {
                sales_person: this.page.fields_dict.sales_person.get_value(),
                fiscal_year: this.page.fields_dict.fiscal_year.get_value(),
            },
            callback: function (r) {
                // console.log('r: ', r.message.data);
                const tableBodyQty = self.page.main.find('#tableBodyQty');
                const tableBodyAmount = self.page.main.find('#tableBodyAmount');
                let emptyDataQty = self.page.main.find('#emptyDataQty')
                let emptyDataAmount = self.page.main.find('#emptyDataAmount')
                let btnSave = self.page.main.find('#btnSave')
                if (r.message.data.length > 0) {
                    emptyDataQty.hide();
                    btnSave.show();
                    self.render_table_td_qty(r.message.data,tableBodyQty);
                    self.render_table_td_amount(r.message.data,tableBodyAmount);
                } else if (r.message.data.length == 0) {
                    self.render_no_data_qty(tableBodyQty,btnSave);
                    self.render_no_data_amount(tableBodyAmount,btnSave,);
                }
                
            }
        });
    },

    render_table_td_qty: function (data, tableBodyQty) {
        tableBodyQty.empty(); 
        data.forEach(item => {
            console.log('item: ', item);
            
            let row = `
                <tr>
                    <td>${item.item_group}</td>
                    <td class="hide">${item.parent}</td>`;
    
            const months = [
                "January", "February", "March", "April", "May", "June", 
                "July", "August", "September", "October", "November", "December"
            ];
    
            months.forEach(month => {
                const monthlyData = item.monthly_distribution.find(md => md.month === month);
                const calculate_qty = monthlyData ? monthlyData.target_qty : 0;
                row += `<td><input type="number" name="${month.toLowerCase()}-qty" onchange="get_value_qty(this)" placeholder="0.00" value="${calculate_qty}"></td>`;
            });
    
            row += `
                    <td>
                        <p class="total-qty bold">${item.target_qty}</p>
                    </td>
                </tr>`;
    
            tableBodyQty.append(row);
        });
    },    
    
    render_table_td_amount: function (data, tableBodyAmount, btnSave) {
        tableBodyAmount.empty();
        let hasValidData = false;
    
        data.forEach(item => {
            if (["Quotation", "Sales Order", "Sales Invoice"].includes(item.item_group)) {
                hasValidData = true;
                let row = `
                <tr>
                    <td>${item.item_group}</td>
                    <td class="hide">${item.parent}</td>`;
    
            const months = [
                "January", "February", "March", "April", "May", "June", 
                "July", "August", "September", "October", "November", "December"
            ];
    
            months.forEach(month => {
                const monthlyData = item.monthly_distribution.find(md => md.month === month);
                const calculate_qty = monthlyData ? monthlyData.target__amount : 0;
                row += `<td><input type="number" name="${month.toLowerCase()}-qty" onchange="get_value_qty(this)" placeholder="0.00" value="${calculate_qty}"></td>`;
            });
    
            row += `
                    <td>
                        <p class="total-qty bold">${item.target__amount}</p>
                    </td>
                </tr>`;
    
                tableBodyAmount.append(row);
            }
        });
    
        if (!hasValidData) {
            this.render_no_data_amount(tableBodyAmount, btnSave);
        }
    },
    
    render_no_data_qty: function (tableBodyQty,btnSave) {
        tableBodyQty.empty(); 
        btnSave.hide();
        tableBodyQty.html(`
            <tr  id="emptyDataQty" >
                <td colspan="14"  class="text-center">
                    <p style="padding: 50px;">No data</p>
                </td>
            </tr>
        `);
    },
    render_no_data_amount: function (tableBodyAmount,btnSave) {
        tableBodyAmount.empty(); 
        // btnSave.hide();
        tableBodyAmount.html(`
            <tr  id="emptyDataAmount" >
                <td colspan="14" class="text-center">
                    <p style="padding: 50px;">No data</p>
                </td>
            </tr>
        `);
    }
    
});

function get_value_qty(e) {
    const value = Math.max(parseFloat(e.value) || 0, 0);
    e.value = value;

    const row = $(e).closest("tr"),
          total = row.find('input[type="number"]').toArray()
                     .reduce((sum, input) => sum + (parseFloat(input.value) || 0), 0);

    row.find(".total-qty").text(total.toFixed(2));
}
function get_value_amount(e) {
    const value = Math.max(parseFloat(e.value) || 0, 0);
    e.value = value;

    const row = $(e).closest("tr"),
          total = row.find('input[type="number"]').toArray()
                     .reduce((sum, input) => sum + (parseFloat(input.value) || 0), 0);

    row.find(".total-amount").text(total.toFixed(2));
}

function collect_quantities() {
    const uniqueTargets = {}; // Object to hold unique target groups
    const months = [
        "January", "February", "March", "April", "May", "June", 
        "July", "August", "September", "October", "November", "December"
    ];

    // Iterate over each row in the tableBodyQty
    $("#tableBodyQty tr").each(function () {
        const rowData = $(this).find("td").map(function () {
            return $(this).find("input").val() || $(this).text().trim();
        }).get(); 

        const targetGroup = rowData[0]; 
        const parent = rowData[1]

        // Initialize the target group if not already done
        if (!uniqueTargets[targetGroup]) {
            uniqueTargets[targetGroup] = {};
        }

        // Assign the quantities for each month
        $.each(months, function (index, monthName) {
            const targetQty = parseFloat(rowData[index + 2]) || 0; 
            uniqueTargets[targetGroup][monthName] = {
                target_qty: targetQty,
                target_amount: 0, 
                parent: parent
            };
        });
    });

    return uniqueTargets; // Return the collected quantities
}

function collect_amounts(uniqueTargets) {
    const months = [
        "January", "February", "March", "April", "May", "June", 
        "July", "August", "September", "October", "November", "December"
    ];

    // Iterate over each row in the tableBodyAmount
    $("#tableBodyAmount tr").each(function () {
        const rowData = $(this).find("td").map(function () {
            return $(this).find("input").val() || $(this).text().trim();
        }).get(); // Collect values into an array
        const targetGroup = rowData[0]; 
        const parent = rowData[1]; 

        // Ensure the target group is initialized
        if (!uniqueTargets[targetGroup]) {
            uniqueTargets[targetGroup] = {};
        }

        // Update the target amounts for each month
        $.each(months, function (index, monthName) {
            const targetAmount = parseFloat(rowData[index + 2]) || 0; // Get the amount for the month

            if (!uniqueTargets[targetGroup][monthName]) {
                uniqueTargets[targetGroup][monthName] = {
                    target_qty: 0, 
                    target_amount: 0,
                    parent: parent
                };
            }
            
            uniqueTargets[targetGroup][monthName].target_amount = targetAmount;
        });
    });

    return uniqueTargets; 
}

function transform_data(uniqueTargets) {
    const data = [];
    let sales_person = $('input[data-fieldname="sales_person"]').val();
    let fiscal_year = $('input[data-fieldname="fiscal_year"]').val();
    // Transform the uniqueTargets object into an array
    $.each(uniqueTargets, function (targetGroup, monthsData) {
        if (targetGroup !== "No data") {
            $.each(monthsData, function (month, values) {
                data.push({
                    target_group: targetGroup,
                    month: month,
                    target_qty: values.target_qty,
                    target_amount: values.target_amount,
                    total_qty: Object.values(monthsData).reduce((sum, val) => sum + val.target_qty, 0),
                    total_amount: Object.values(monthsData).reduce((sum, val) => sum + val.target_amount, 0),
                    sales_person: sales_person,
                    fiscal_year: fiscal_year,
                    parent: values.parent
                });
            });
        }
    });

    // console.table(data); 
    create_monthly_distribution(data)
    return data; 
}

// Main function to save data
function save_data() {
    const uniqueTargets = collect_quantities(); // Collect quantities
    const updatedTargets = collect_amounts(uniqueTargets); // Collect amounts
    return transform_data(updatedTargets); // Transform and return the final data
}

function create_monthly_distribution(data) {
    frappe.call({
        method: 'ditech_core.ditech_core.page.set_target_sales_per.set_target_sales_per.create_updated_monthly_dist',
        args: {
            data: data
        },
        callback: function (r) {
            return r.message
        }
    });
}



