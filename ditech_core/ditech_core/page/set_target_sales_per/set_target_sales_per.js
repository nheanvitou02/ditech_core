frappe.pages['set-target-sales-per'].on_page_load = function (wrapper) {
    new setTargetSalesPerson(wrapper);
    document.addEventListener('keydown', function (event) {
        const btnSave = $('btnSave');
        if (btnSave.length && btnSave.css('display') !== 'none' && event.ctrlKey && event.key === 's') {
            event.preventDefault();
            save_data();
        }
    });
};

const setTargetSalesPerson = class {
    constructor(wrapper) {
        this.page = frappe.ui.make_app_page({
            parent: wrapper,
            title: __("Set Target Sales Person"),
            single_column: true,
        });
        this.make();
    }

    async make() {
        frappe.msgprint({ message: "This page allows you to set targets for each sales person. It is designed to help you manage and update sales targets effectively.", title: __("Introduction")});
        $('.page-form').hide();
        let rendered_html = frappe.render_template("set_target_sales_per",);
        $(rendered_html).appendTo(this.page.main);
        await this.add_fields();
    }

    async add_fields() {
        const filterSection = this.page.main.find('#filterSection');
        try {
            const salesPersons = await this.fetch_data("Sales Person", ["name"]);
            let sp_field = this.page.add_field({
                fieldtype: "Autocomplete",
                fieldname: "sales_person",
                label: "Select Sales Person",
                reqd: 1,
                options: salesPersons.map(sp => sp.name)
            });
            sp_field.$wrapper.appendTo(filterSection);

            const fiscalYears = await this.fetch_data("Fiscal Year", ["name"]);
            let fy_field = this.page.add_field({
                fieldtype: "Autocomplete",
                fieldname: "fiscal_year",
                label: "Select Fiscal Year",
                reqd: 1,
                options: fiscalYears.map(fy => fy.name),
                default: 2025
            });
            fy_field.$wrapper.appendTo(filterSection);

            this.add_event_listener();
        } catch (error) {
            console.error("Error fetching data:", error);
        }
        
    }

    async fetch_data(doctype, fields) {
        return new Promise((resolve, reject) => {
            frappe.call({
                method: "frappe.client.get_list",
                args: { doctype, fields },
                callback: function (response) {
                    if (response.message) {
                        resolve(response.message);
                    } else {
                        reject(new Error(`Failed to fetch ${doctype}`));
                    }
                }
            });
        });
    }

    add_event_listener() {
        const { sales_person, fiscal_year } = this.page.fields_dict;
        [sales_person, fiscal_year].forEach(field => {
            if (field) {
                field.$input.on('change', this.log_all_field_values.bind(this));
            }
        });
    }
    
    async log_all_field_values() {
        const sales_person = await this.get_input_value("sales_person");
        const fiscal_year = await this.get_input_value("fiscal_year");
        $('#btnAddTargetQty, #btnAddTargetAmount').toggleClass('hide', !sales_person || !fiscal_year);
        this.get_get_target();
        this.validate_hide_btn_group(sales_person, fiscal_year);
    }

    async get_input_value(fieldname) {
        return new Promise((resolve) => {
            setTimeout(() => {
                let value = this.page.fields_dict[fieldname]?.get_value() || null;
                resolve(value);
            }, 0);
        });
    }

    async get_get_target() {
        try {
            const sales_person = await this.get_input_value("sales_person");
            const fiscal_year = await this.get_input_value("fiscal_year");

            if (!sales_person || !fiscal_year) {
                const [tableBodyQty, tableBodyAmount, btnSave] = ['#tableBodyQty', '#tableBodyAmount', '#btnSave'].map(id => this.page.main.find(id));
                this.render_no_data_qty(tableBodyQty, btnSave);
                this.render_no_data_amount(tableBodyAmount);
                return;
            }

            const response = await frappe.call({
                method: "ditech_core.ditech_core.page.set_target_sales_per.set_target_sales_per.get_target_team",
                args: { sales_person, fiscal_year }
            });

            const data = response.message?.data || [];
            this.render_tables(data);
        } catch (error) {
            frappe.msgprint({ message: error.message, title: __("Error"), indicator: "red" });
        }
    }

    render_tables(data) {
        const tableBodyQty = this.page.main.find('#tableBodyQty');
        const tableBodyAmount = this.page.main.find('#tableBodyAmount');
        const btnSave = this.page.main.find('#btnSave');
    
        if (data.length > 0) {
            btnSave.show();
            this.render_table_td_quantity(data, tableBodyQty);
            this.render_table_td_amount(data, tableBodyAmount);
        } else {
            [tableBodyQty, tableBodyAmount].forEach(table => this.render_no_data_qty(table, btnSave));
        }
    }
    

    render_table_td_quantity(data, tableBodyQty) {
        tableBodyQty.empty();
        data.forEach(item => {
            let row = `<tr>
                <td>
                    <div class="dropdown">
                        <div class="dropdown-toggle target-dropdown" type="button" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
                            ${item.item_group}
                        </div>
                        <div class="dropdown-menu">
                            <a class="dropdown-item item-qty" href="#" onclick="update_selection(this, 'Lead')" style="${item.item_group === 'Lead' ? 'color: gray; pointer-events: none;' : ''}">Lead</a>
                            <a class="dropdown-item item-qty" href="#" onclick="update_selection(this, 'Opportunity')" style="${item.item_group === 'Opportunity' ? 'color: gray; pointer-events: none;' : ''}">Opportunity</a>
                            <a class="dropdown-item item-qty" href="#" onclick="update_selection(this, 'Quotation')" style="${item.item_group === 'Quotation' ? 'color: gray; pointer-events: none;' : ''}">Quotation</a>
                            <a class="dropdown-item item-qty" href="#" onclick="update_selection(this, 'Sales Order')" style="${item.item_group === 'Sales Order' ? 'color: gray; pointer-events: none;' : ''}">Sales Order</a>
                            <a class="dropdown-item item-qty" href="#" onclick="update_selection(this, 'Sales Invoice')" style="${item.item_group === 'Sales Invoice' ? 'color: gray; pointer-events: none;' : ''}">Sales Invoice</a>
                    </div>
                </td>
                <td class="hide">${item.parent}</td>`;
            months.forEach(month => {
                const monthlyData = item.monthly_distribution.find(md => md.month === month);
                const calculate_qty = monthlyData ? monthlyData.target_qty : 0;
                row += `<td><input type="number" name="${month.toLowerCase()}-qty" onchange="get_value_qty(this)" placeholder="0.00" value="${calculate_qty}"></td>`;
            });

            row += `
            <td><p class="total-qty bold" style="margin: 0px !important; font-weight: bold;">${item.target_qty}</p></td>
             <td><button onclick="delete_row(this)" class="btn btn-danger btn-sm" data-index="qty-row-${data.indexOf(item)}">Delete</button></td>
            </tr>
            
            `;
            tableBodyQty.append(row);
        });
    }
   

    render_table_td_amount(data, tableBodyAmount) {
        tableBodyAmount.empty();
        let hasRestrictedItem = false;
    
        data.forEach(item => {
            if (["Quotation", "Sales Order", "Sales Invoice"].includes(item.item_group)) {
                hasRestrictedItem = true;
                let row = `<tr>
                    <td>
                        <div class="dropdown">
                            <div class="dropdown-toggle target-dropdown" type="button" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
                                ${item.item_group}
                            </div>
                             <div class="dropdown-menu">
                                <a class="dropdown-item item-qty" href="#" onclick="update_selection(this, 'Quotation')" style="${item.item_group === 'Quotation' ? 'color: gray; pointer-events: none;' : ''}">Quotation</a>
                                <a class="dropdown-item item-qty" href="#" onclick="update_selection(this, 'Sales Order')" style="${item.item_group === 'Sales Order' ? 'color: gray; pointer-events: none;' : ''}">Sales Order</a>
                                <a class="dropdown-item item-qty" href="#" onclick="update_selection(this, 'Sales Invoice')" style="${item.item_group === 'Sales Invoice' ? 'color: gray; pointer-events: none;' : ''}">Sales Invoice</a>
                            </div>
                        </div>
                    </td>
                    <td class="hide">${item.parent}</td>`;
    
                months.forEach(month => {
                    const monthlyData = item.monthly_distribution.find(md => md.month === month);
                    const calculate_amount = monthlyData ? monthlyData.target__amount : 0;
                    row += `<td><input type="number" name="${month.toLowerCase()}-amount" onchange="get_value_qty(this)" placeholder="0.00" value="${calculate_amount}"></td>`;
                });
    
                row += `<td><p class="total-amount" style="margin: 0px !important; font-weight: bold;">${item.target__amount}</p></td>
                <td><button onclick="delete_row(this)" class="btn btn-danger btn-sm" data-index="amount-row-${data.indexOf(item)}">Delete</button></td>
                </tr>`;
                tableBodyAmount.append(row);
            }
        });
    
        // If no restricted items exist, show alert
        if (!hasRestrictedItem) {
            this.render_no_data_amount(tableBodyAmount);
        }
    }
    
    render_no_data_qty(tableBodyQty, btnSave) {
        tableBodyQty.empty();
        btnSave.hide();
        tableBodyQty.html(`
            <tr id="emptyDataQty" class=tr-no-data>
                <td colspan="15" class="text-center">
                    <p style="padding: 50px;">No data</p>
                </td>
            </tr>
        `);
    }

    render_no_data_amount(tableBodyAmount) {
        tableBodyAmount.empty();
        tableBodyAmount.html(`
            <tr id="emptyDataAmount">
                <td colspan="15" class="text-center">
                    <p style="padding: 50px;">No data</p>
                </td>
            </tr>
        `);
    }

    async validate_hide_btn_group(sales_person, fiscal_year) {
        const action = (sales_person || fiscal_year) ? 'show' : 'hide';
        $('#btnAddTargetQty').add('#btnAddTargetAmount')[action]();
    }
    
};


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

// ---------------------------FUNCTION TO COLLECT QUANTITIES--------------------------------

function collect_quantities() {
    const uniqueTargets = {}; 
    $("#tableBodyQty tr").each(function () {
        const rowData = $(this).find("td").map(function () {
            const dropdown = $(this).find(".dropdown-toggle");
            if (dropdown.length && dropdown.text().trim() === "Select Target Team") {
                frappe.throw(__('Please select a target team is required'));
                throw new Error("Please select a target team is required");
            }
            return dropdown.length ? dropdown.text().trim() : $(this).find("input").val() || $(this).text().trim();
        }).get(); 

        const [targetGroup, parent, ...quantities] = rowData;
        if (!uniqueTargets[targetGroup]) uniqueTargets[targetGroup] = {};

        quantities.forEach((qty, index) => {
            if (index < 12){
                const targetQty = parseFloat(qty) || 0;
                const month = months[index];
                uniqueTargets[targetGroup][month] = { target_qty: targetQty, target_amount: 0, parent };
            }
        });
    });

    return uniqueTargets; 
}

// ---------------------------FUNCTION TO COLLECT QUANTITIES--------------------------------

// ---------------------------FUNCTION TO COLLECT AMOUNTS--------------------------------
function collect_amounts(uniqueTargets) {
    $("#tableBodyAmount tr").each(function () {
        const rowData = $(this).find("td").map(function () {
            const dropdown = $(this).find(".dropdown-toggle");
            if (dropdown.length && dropdown.text().trim() === "Select Target Team") {
                frappe.throw(__('Please select a target team is required'));
                throw new Error("Please select a target team is required");
            }
            return dropdown.length ? dropdown.text().trim() : $(this).find("input").val() || $(this).text().trim();
        }).get(); 

        const [targetGroup, parent, ...amounts] = rowData;
        if (!uniqueTargets[targetGroup]) uniqueTargets[targetGroup] = {};

        amounts.forEach((amount, index) => {
            if (index < 12){
                const month = months[index];
                const targetAmount = parseFloat(amount) || 0;
                if (!uniqueTargets[targetGroup][month]) uniqueTargets[targetGroup][month] = { target_qty: 0, target_amount: 0, parent };
                uniqueTargets[targetGroup][month].target_amount = targetAmount;
            }
        });
    });

    return uniqueTargets; 
}

// -----------------------------------END FUNCTION TO COLLECT AMOUNTS----------------------------------------------------------

// ----------------------------------FUNCTION TO TRANSFORM DATA-------------------------------------------
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
    console.table(data);
    create_sales_person_target(data)
    return data; 
}
// ----------------------------------END FUNCTION TO TRANSFORM DATA-------------------------------------------

// ----------------------------------MAIN FUNCTION TO SAVE DATA-------------------------------------------
function save_data() {
    const uniqueTargets = collect_quantities(); 
    const updatedTargets = collect_amounts(uniqueTargets); 
    return transform_data(updatedTargets); 
}
// ----------------------------------MAIN FUNCTION TO SAVE DATA-------------------------------------------

// ------------------------------FUNCTION TO ADD NEW ROW OF BODY QTY---------------------------------------
let selected_target_teams = [];

function add_target_quantity_row() {
    const table_body_qty = $('#tableBodyQty');
    $('#emptyDataQty').remove();
    if (table_body_qty.find('tr').length >= 5) {
        $('#btnAddTargetQty').addClass("hide");
        return;
    }

    let new_row = `
    <tr>
        <td>
            <div class="dropdown">
                <div class="dropdown-toggle target-dropdown" type="button" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
                    Select Target Team 
                </div>
                <div class="dropdown-menu">
                    <a class="dropdown-item item-qty" href="#" onclick="update_selection(this, 'Lead')">Lead</a>
                    <a class="dropdown-item item-qty" href="#" onclick="update_selection(this, 'Opportunity')">Opportunity</a>
                    <a class="dropdown-item item-qty" href="#" onclick="update_selection(this, 'Quotation')">Quotation</a>
                    <a class="dropdown-item item-qty" href="#" onclick="update_selection(this, 'Sales Order')">Sales Order</a>
                    <a class="dropdown-item item-qty" href="#" onclick="update_selection(this, 'Sales Invoice')">Sales Invoice</a>
                </div>
            </div>
        </td>
        <td class="hide">Hello</td>
        ${Array.from({ length: 12 }, (_, i) => 
            `<td><input type="number" name="${new Date(0, i).toLocaleString('en', { month: 'long' }).toLowerCase()}-qty" 
            onchange="get_value_qty(this)" placeholder="0.00" value="10" /></td>`).join('')}
        <td><p class="total-qty bold" style="margin: 0px !important; font-weight: bold;">120</p></td>
        <td><button onclick="delete_row(this)" class="btn btn-danger btn-sm">Delete</button></td>
    </tr>
    `;

    table_body_qty.append(new_row);
    update_dropdown_options();
    toggle_save_button();

    // Hide "Add" button if the max number of rows is reached
    if (table_body_qty.find('tr').length >= 5) {
        $('#btnAddTargetQty').addClass("hide");
    }
}

function update_selection(element, item) {
    const dropdown = $(element).closest('.dropdown');
    const prev_selected = dropdown.find('.target-dropdown').text().trim();

    // Remove old selection from the list
    if (prev_selected !== "Select Target Team" && selected_target_teams.includes(prev_selected)) {
        selected_target_teams = selected_target_teams.filter(team => team !== prev_selected);
    }

    // Prevent duplicate selections
    if (selected_target_teams.includes(item)) {
        alert("Target Team already selected!");
        return;
    }

    selected_target_teams.push(item);
    dropdown.find('.target-dropdown').text(item);
    update_dropdown_options();
}

function update_dropdown_options() {
    const selectedItems = [];
    $('#tableBodyQty .target-dropdown').each(function() {
        const item = $(this).text().trim();
        if (item !== "Select Target Team") {
            selectedItems.push(item);
        }
    });

    $(".dropdown-menu .item-qty").each(function() {
        const item = $(this).text().trim();
        if (selectedItems.includes(item)) {
            $(this).css("color", "gray").css("pointer-events", "none");
        } else {
            $(this).css("color", "").css("pointer-events", "auto");
        }
    });
}

function delete_row(button) {
    let sales_person = $('input[data-fieldname="sales_person"]').val();
    let fiscal_year = $('input[data-fieldname="fiscal_year"]').val();
    const row = $(button).closest("tr");
    const target_team = row.find('.target-dropdown').text().trim();
    const row_data = {
        target_team: target_team,
        fiscal_year:fiscal_year ,
        parent: `Sales Person ${sales_person} ${fiscal_year}` ,
    };
    

    
    frappe.warn(
        'Are you sure you want to delete this row?',
        'This action will remove the target team from the list.', 
        () => {  
            delete_target_team(row_data);
            // Remove from selected_target_teams array
            selected_target_teams = selected_target_teams.filter(team => team !== target_team);
            row.remove();
            update_dropdown_options();
            toggle_save_button();
            const table_body_qty = $('#tableBodyQty');

            if (table_body_qty.find('tr').length === 0) {
                table_body_qty.append(`
                    <tr id="emptyDataQty">
                        <td colspan="15" class="text-center">
                            <p style="padding: 50px;">No data</p>
                        </td>
                    </tr>
                `);
            }

            // Show "Add" button if rows are less than 5
            if (table_body_qty.find('tr').length < 5) {
                $('#btnAddTargetQty').removeClass("hide");
            }
        },
        'Delete', 
    );
}
// --------------------------------------------------END FUNCTION TO ADD NEW ROW OF BODY QTY --------------------------------------------------------


// --------------------------------------------------FUNCTION TO ADD NEW ROW OF BODY AMOUNT -------------------------------------------------------
let selected_target_teams_amount = [];
function add_target_amount_row() {
    const table_body_amount = $('#tableBodyAmount');
    table_body_amount.find('#emptyDataAmount').remove();
    table_body_amount.find('.tr-no-data').remove();

    // Check if there are already 5 rows
    if (table_body_amount.find('tr').length >= 5) {
        $('#btnAddTargetAmount').addClass("hide");
        return;
    }

    let new_row = `
    <tr>
        <td>
            <div class="dropdown">
                <div class="dropdown-toggle target-dropdown" type="button" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
                    Select Target Team 
                </div>
                <div class="dropdown-menu">
                    <a class="dropdown-item item-amount" href="#" onclick="update_selection_amount(this, 'Quotation')">Quotation</a>
                    <a class="dropdown-item item-amount" href="#" onclick="update_selection_amount(this, 'Sales Order')">Sales Order</a>
                    <a class="dropdown-item item-amount" href="#" onclick="update_selection_amount(this, 'Sales Invoice')">Sales Invoice</a>
                </div>
            </div>
        </td>
        <td class="hide">Hello</td>
        ${Array.from({ length: 12 }, (_, i) => 
            `<td><input type="number" name="${new Date(0, i).toLocaleString('en', { month: 'long' }).toLowerCase()}-amount" 
            onchange="get_value_amount(this)" placeholder="0.00" value="1000" /></td>`).join('')}
        <td><p class="total-amount bold" style="margin: 0px !important; font-weight: bold;">12000</p></td>
        <td><button onclick="delete_row_amount(this)" class="btn btn-danger btn-sm">Delete</button></td>
    </tr>
    `;

    table_body_amount.append(new_row);
    update_dropdown_options_amount();
    toggle_save_button();

    if (table_body_amount.find('tr').length >= 3) {
        $('#btnAddTargetAmount').addClass("hide");
    }
}

function update_selection_amount(element, item) {
    const dropdown = $(element).closest('.dropdown');
    const prev_selected = dropdown.find('.target-dropdown').text().trim();

    if (prev_selected !== "Select Target Team" && selected_target_teams_amount.includes(prev_selected)) {
        selected_target_teams_amount = selected_target_teams_amount.filter(team => team !== prev_selected);
    }

    if (selected_target_teams_amount.includes(item)) {
        alert("Target Team already selected!");
        return;
    }

    selected_target_teams_amount.push(item);
    dropdown.find('.target-dropdown').text(item);
    update_dropdown_options_amount();
}

function update_dropdown_options_amount() {
    const selectedItems = [];
    $('#tableBodyAmount .target-dropdown').each(function() {
        const item = $(this).text().trim();
        if (item !== "Select Target Team") {
            selectedItems.push(item);
        }
    });

    $(".dropdown-menu .item-amount").each(function() {
        const item = $(this).text().trim();
        if (selectedItems.includes(item)) {
            $(this).css("color", "gray").css("pointer-events", "none");
        } else {
            $(this).css("color", "").css("pointer-events", "auto");
        }
    });
}

// --------------------------------------------------END FUNCTION TO ADD NEW ROW OF BODY AMOUNT -------------------------------------------------------

// --------------------------------------------------FUNCTION TO DELETE ROW OF BODY AMOUNT -------------------------------------------------------

function delete_row_amount(button) {
    const sales_person = $('input[data-fieldname="sales_person"]').val();
    const fiscal_year = $('input[data-fieldname="fiscal_year"]').val();
    const row = $(button).closest("tr");
    const target_team = row.find('.target-dropdown').text().trim();
    const row_data = {
        target_team: target_team,
        fiscal_year: fiscal_year,
        parent: `Sales Person ${sales_person} ${fiscal_year}`,
    };

    frappe.warn(
        'Are you sure you want to delete this row?',
        'This action will remove the target team from the list.',
        () => {
            delete_target_team(row_data);
            selected_target_teams_amount = selected_target_teams_amount.filter(team => team !== target_team);
            row.remove();
            update_dropdown_options_amount();
            toggle_save_button();

            const table_body_amount = $('#tableBodyAmount');
            if (table_body_amount.find('tr').length === 0) {
                table_body_amount.append(`
                    <tr id="emptyDataAmount">
                        <td colspan="15" class="text-center">
                            <p style="padding: 50px;">No data</p>
                        </td>
                    </tr>
                `);
            }

            if (table_body_amount.find('tr').length < 5) {
                $('#btnAddTargetAmount').removeClass("hide");
            }
        },
        'Delete',
    );
}
// ----------------------------END BlOCK DELETE ROW----------------------------------------


// ----------------------------FUNCTION DELETE ROW----------------------------------------
function delete_target_team(row_data) {
    frappe.call({
        method: 'ditech_core.ditech_core.page.set_target_sales_per.set_target_sales_per.delete_target_team',
        args: {
            target_team: row_data.target_team,
            fiscal_year: row_data.fiscal_year,
            parent: row_data.parent,
        },
        callback: function (r) {
            return r.message
        }
    });
}

function create_sales_person_target(data) {
    frappe.call({
        method: 'ditech_core.ditech_core.page.set_target_sales_per.set_target_sales_per.set_sales_person_target',
        args: {
            data: data
        },
        callback: function (r) {
            return r.message
        }
    });
}

function toggle_save_button() {
    if ($('#tableBodyQty tr').length > 0) {
        $('#btnSave').show();
    } else {
        $('#btnSave').hide();
    }
}

// PUBLIC VARIABLES
const months = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
];

