# Copyright (c) 2024, tech@ditech.software and contributors
# For license information, please see license.txt
###############################################################################
#  E Filing.py
###############################################################################
#   This code is for E Filing
#
#   History
#   01-12-2024  Pheakdey    Created
###############################################################################
from frappe.model.document import Document
import pandas as pd
import frappe
import os
from datetime import datetime

class EFiling(Document):
	pass

###############################################################################
# This function is used to get data from Sales Invoice, Purchase Invoice, 
# POS invoice and Employee to show on E filing Details
# Request:
#   
# Response:
#   
# Taks:
#   
# History
# 01-12-2024  Pheakdey    Created
#
################################################################################
@frappe.whitelist()
def get_data_e_filing(doctype, from_date, to_date):
    if doctype == "Sales Invoice":
        sales_invoice = frappe.qb.DocType("Sales Invoice")
        customer = frappe.qb.DocType("Customer")
        company = frappe.qb.DocType("Company")
        data_sales_sheet = (
            frappe.qb.from_(doctype)
            .where(sales_invoice.posting_date[from_date:to_date])
            .where(sales_invoice.docstatus ==1)
            .select(
                sales_invoice.name,
                sales_invoice.name.as_('name_reference'),
                sales_invoice.posting_date,
                sales_invoice.customer,
                sales_invoice.tax_id,
                sales_invoice.company_tax_id,
            ).run(as_dict=True)
        )
        return data_sales_sheet
    
    elif doctype == "POS Invoice":
        pos_invoice = frappe.qb.DocType("POS Invoice")
        customer = frappe.qb.DocType("Customer")
        company = frappe.qb.DocType("Company")
        data_sales_sheet = (
            frappe.qb.from_(doctype)
            .join(customer)
            .on(pos_invoice.customer == customer.name)
            .join(company)
            .on(pos_invoice.company == company.name)
            .where(pos_invoice.posting_date[from_date:to_date])
            .where((pos_invoice.docstatus == 1) & (pos_invoice.status == "Consolidated"))
            .select(
                pos_invoice.invoice_number.as_('name'),
                pos_invoice.name.as_('name_reference'),
                pos_invoice.posting_date,
                pos_invoice.customer,
                customer.tax_id,
                company.tax_id.as_('company_tax_id'),
            ).run(as_dict=True)
        )
        return data_sales_sheet
    
    elif doctype == "Purchase Invoice":
        purchase_invoice = frappe.qb.DocType("Purchase Invoice")
        supplier = frappe.qb.DocType("Supplier")
        company = frappe.qb.DocType("Company")
        data_sales_sheet = (
            frappe.qb.from_(doctype)
            .join(supplier)
            .on(purchase_invoice.supplier == supplier.name)
            .join(company)
            .on(purchase_invoice.company == company.name)
            .where(purchase_invoice.posting_date[from_date:to_date])
            .where(purchase_invoice.docstatus == 1)
            .select(
                purchase_invoice.bill_no.as_('name'),
                purchase_invoice.name.as_('name_reference'),
                purchase_invoice.posting_date,
                purchase_invoice.supplier,
                purchase_invoice.tax_id,
                company.tax_id.as_('company_tax_id'),
            ).run(as_dict=True)
        )
        return data_sales_sheet
    
################################# END function #################################


################################################################################
# This function is used to export to excel template
# Request:
#   
# Response:
#   
# Taks:
#    
# History
# 01-12-2024  Pheakdey    Created
#
################################################################################
@frappe.whitelist()
def export_e_filing_data(doctype, from_date, to_date):

    date_obj = datetime.strptime(from_date, "%Y-%m-%d")
    formatted_date_obj = date_obj.strftime("%m/%Y")
    
    ###################################### START SALES INVOICE FILE ####################################################
    if doctype == "Sales Invoice":
        sale_invoice = frappe.qb.DocType("Sales Invoice")
        customer = frappe.qb.DocType("Customer")
        company = frappe.qb.DocType("Company")
        data_sales_sheet = (
            frappe.qb.from_(sale_invoice)
            .join(customer)
            .on(sale_invoice.customer == customer.name)
            .join(company)
            .on(sale_invoice.company == company.name)
            .where(sale_invoice.posting_date[from_date:to_date])
            .where(sale_invoice.docstatus ==1)
            .select(
                sale_invoice.name,
                sale_invoice.posting_date,
                sale_invoice.customer,
                sale_invoice.customer_name,
                sale_invoice.currency,
                sale_invoice.conversion_rate,
                sale_invoice.tax_id,
                sale_invoice.company,
                sale_invoice.company_tax_id,
                sale_invoice.taxes_and_charges,
                sale_invoice.grand_total,
                sale_invoice.remarks,
                customer.customer_type,
                customer.custom_foreign,
                company.custom_type_of_company,
                company.custom_prepayment_of_income_tax
            ).run(as_dict=True)
        )

        # GET DATA EXCHANGE CURRENCY
        data_exchange_currency = frappe.db.get_all(
            'Currency Exchange',
            filters={
                'from_currency': 'USD',
                'to_currency': 'KHR',
            },
            fields=['exchange_rate', 'from_currency'],
            order_by= 'date desc',
            limit=1
        )

        vatin_company = ''
        for idx, row in enumerate(data_sales_sheet, start=1):
            vatin_company = row.get("company_tax_id")

        company_type = frappe.db.get_all(
              'E Filing Company Table',
                fields=['idx', 'id', 'type_of_company_english'],
                order_by='idx'
        )
        
        # PREPARE DATA FOR SALES SHEET
        sales_invoice_data = []

        for idx, row in enumerate(data_sales_sheet, start=1):
            # GET TYPE OF CUSTOMER 
            customer_type_idx = None
            if row.get('customer_type') == "Company":
                if row.get('custom_foreign') == 1:
                    customer_type_idx = 3
                else:
                    customer_type_idx = 1
            elif row.get('customer_type') == "Individual":
                customer_type_idx = 2

            # GET TYPE OF COMPANY 
            company_type_idx = None
            for i in company_type:
                if row.get('custom_type_of_company') == i.get('type_of_company_english'):
                    company_type_idx = i.get('id')

            # GET PREPAYMENT OF INCOME TAX TYPE
            prepayment_of_income_tax_type = None
            if row.get('custom_prepayment_of_income_tax') == "1%":
                prepayment_of_income_tax_type = 1
            elif row.get('custom_prepayment_of_income_tax') == "5%":
                prepayment_of_income_tax_type = 5
            else:
                prepayment_of_income_tax_type = 0
            
            # GET GRAND TOTAL AS KHMER
            grand_total_khr = None
            for cur in data_exchange_currency:
                if row.get('currency') == "USD":
                    grand_total_khr = row.get("grand_total") * cur.get("exchange_rate")  
                else:
                    grand_total_khr = row.get("grand_total")
              
            sales_invoice_data.append({
                "ល.រ": idx,
                "កាលបរិច្ឆេទ": row.get('posting_date'),
                "លេខវិក្កយបត្រ ឬ ប្រតិវេទន៍គយ": row.get('name'),
                "ប្រភេទ": customer_type_idx,
                "លេខសម្គាល់": row.get('tax_id'),
                "ឈ្មោះ(ខ្មែរ)": row.get("customer"),
                "ឈ្មោះ(ឡាតាំង)": row.get("customer"),
                "ប្រភេទផ្គត់ផ្គង់ទំនិញ*ឬ​សេវាកម្ម": company_type_idx,
                "តម្លៃសរុបជាប់អតប*": grand_total_khr,
                "តម្លៃសរុបមិនជាប់អតប ឬ អតប អត្រា 0%": "",
                "អាករពិសេសលើទំនិញមួយចំនួន": "",
                "អាករពិសេសលើសេវាមួយចំនួន": "",
                "អាករបំភ្លឺសាធារណៈ": "",
                "អាករលើការស្នាក់នៅ": "",
                "អត្រាប្រាក់រំដោះពន្ធលើប្រាក់ចំណូល": prepayment_of_income_tax_type,
                "វិស័យ": "",
                "លេខឥណទានរតនាគារជាតិ": "",
                "បរិយាយ*": row.get('remarks'),
            })

        # PREPARE DATA FOR NONTAXABLE SHEET
        nontaxable_data = []
        for idx, row in enumerate(nontaxable_data, start=1):
            nontaxable_data.append({
                "ល.រ": idx,
                "លេខវិក្កយបត្រ ឬ ប្រតិវេទន៍គយ": row.get('name'),
                "ឈ្មោះ(ខ្មែរ)": row.get("customer_name"),
                "ឈ្មោះ(ឡាតាំង)": row.get("customer_name")
        })
        
        # PREPARE DATA FOR OVERSEACOMPANY SHEET
        overseacompany_data = []
        for idx, row in enumerate(overseacompany_data, start=1):
            overseacompany_data.append({
                "ល.រ": idx,
                "លេខវិក្កយបត្រ ឬ ប្រតិវេទន៍គយ": row.get('name'),
                "ឈ្មោះ(ខ្មែរ)": row.get("customer_name"),
                "ឈ្មោះ(ឡាតាំង)": row.get("customer_name")
        })

        df_sale_sheet = pd.DataFrame(sales_invoice_data)
        df_nontaxable_sheet = pd.DataFrame(nontaxable_data)
        df_overseacompany_sheet = pd.DataFrame(overseacompany_data)

        file_path = f"/tmp/E-Filing-Sale-{frappe.generate_hash()}.xlsx" 

        script_dir = os.path.dirname(os.path.abspath(__file__))

        # READ FILE TO WRITE TO FILE
        file_noted_of_sale_to_read = os.path.join(script_dir, 'e-Filing-Sale.xlsx')
        df_noted = pd.read_excel(file_noted_of_sale_to_read, sheet_name="NOTED")

        with pd.ExcelWriter(file_path, engine='xlsxwriter') as writer:

            ###################################### START SALES SHEET ######################################k
            df_sale_sheet.to_excel(writer, index=False, startrow=2, sheet_name='SALE')
            workbook = writer.book
            worksheet_sales = writer.sheets['SALE']

            # OPTION PROTECT SHEET BUT ALLOW MAC AND WINDOW CAN EDIT AND FORMAT DATA
            # worksheet_sales.protect(options={'format_cells': True, 'format_columns': True, 'format_rows': True})
            worksheet_sales.protect()

            columns = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R']

            cell_data_format = workbook.add_format({
                'font_name': 'Khmer OS Siemreap',
                'font_size': 10,
                'align': 'left',
                'locked': False,
            })

            top_format = workbook.add_format({
                'align': 'right',
                'valign': 'vcenter',
                'font_name': 'Khmer OS Siemreap',
                'locked': True,
                'fg_color': '#eeeeee',
            })

            top_format_data = workbook.add_format({
                'align': 'left',
                'valign': 'vcenter',
                'font_name': 'Khmer OS Siemreap',
                'bold': True,
                'locked': False,
                'fg_color': '#eeeeee',
            })

            for col in columns:
                worksheet_sales.write(f'{col}1', '', top_format)

            worksheet_sales.merge_range('A1:B1', 'លេខសម្គាល់អត្តសញ្ញាណ៖', top_format)
            worksheet_sales.write('C1', vatin_company, top_format_data)
            worksheet_sales.write('D1', 'សម្រាប់ខែ៖', top_format)
            
            text_format = workbook.add_format({
                'num_format': '@',
                'align': 'left', 
                'locked': False, 
                'font_name': 'Khmer OS Siemreap',
                'valign': 'vcenter',
                'bold': True, 
                'fg_color': '#eeeeee'
            })  # Format as text
            worksheet_sales.write('E1', formatted_date_obj, text_format)

            # SET GROUP HEADER FOR SALES SHEET
            merge_format_header = workbook.add_format({
                'align': 'center',
                'valign': 'vcenter',
                'border': 1,
                'font_name': 'Khmer OS Siemreap',
                'fg_color': '#70ad47',
                "locked": True,
            })
            merge_format_header2 = workbook.add_format({
                'align': 'center',
                'valign': 'vcenter',
                'border': 1,
                'font_name': 'Khmer OS Siemreap',
                'fg_color': '#70ad47',
                "locked": True,
                "bottom": 6
            })

            merge_format_header1 = workbook.add_format({
                'align': 'center',
                'valign': 'vcenter',
                'border': 1,
                'font_name': 'Khmer OS Siemreap',
                "locked": True,
                "bottom": 6
            })

            merge_format_header.set_text_wrap()

            # HEADER SALES SHEET
            worksheet_sales.merge_range('A2:A3', 'ល.រ*', merge_format_header)
            worksheet_sales.merge_range('B2:B3', 'កាលបរិច្ឆេទ*', merge_format_header)
            worksheet_sales.merge_range('C2:C3', 'លេខវិក្កយបត្រ ឬ ប្រតិវេទន៍គយ*', merge_format_header)
            worksheet_sales.merge_range('D2:G2', 'អ្នកទិញ', merge_format_header)
            worksheet_sales.merge_range('H2:H3', 'ប្រភេទផ្គត់ផ្គង់ទំនិញ*ឬសេវាកម្ម', merge_format_header)
            worksheet_sales.merge_range('I2:I3', 'តម្លៃសរុបជាប់អតប*', merge_format_header)
            worksheet_sales.merge_range('J2:J3', 'តម្លៃសរុបមិនជាប់ អតប ឬ អតប អត្រា ០%', merge_format_header)
            worksheet_sales.merge_range('K2:K3', 'អាករពិសេសលើទំនិញមួយចំនួន', merge_format_header)
            worksheet_sales.merge_range('L2:L3', 'អាករពិសេសលើសេវាមួយចំនួន', merge_format_header)
            worksheet_sales.merge_range('M2:M3', 'អាករបំភ្លឺសាធារណៈ', merge_format_header)
            worksheet_sales.merge_range('N2:N3', 'អាករលើការស្នាក់នៅ', merge_format_header)
            worksheet_sales.merge_range('O2:O3', 'អត្រាប្រាក់រំដោះពន្ធលើប្រាក់ចំណូល', merge_format_header)
            worksheet_sales.merge_range('P2:P3', 'វិស័យ', merge_format_header)
            worksheet_sales.merge_range('Q2:Q3', 'លេខឥណទានរតនាគារជាតិ', merge_format_header)
            worksheet_sales.merge_range('R2:R3', 'បរិយាយ*', merge_format_header)

            for col in columns:
                worksheet_sales.write(f'{col}3', '', merge_format_header1)

            worksheet_sales.write('D3', 'ប្រភេទ*', merge_format_header2)
            worksheet_sales.write('E3', 'លេខសម្គាល់*', merge_format_header2) 
            worksheet_sales.write('F3', 'ឈ្មោះ(ខ្មែរ)', merge_format_header2)  
            worksheet_sales.write('G3', 'ឈ្មោះ(ឡាតាំង)', merge_format_header2)  

            # SET COLUMN WIDTHS FOR SALES SHEET
            worksheet_sales.set_column('A:A', 7)
            worksheet_sales.set_column('B:B', 15)
            worksheet_sales.set_column('C:C', 30)
            worksheet_sales.set_column('D:D', 10)
            worksheet_sales.set_column('E:G', 15)
            worksheet_sales.set_column('H:L', 20)
            worksheet_sales.set_column('M:N', 20)
            worksheet_sales.set_column('O:O', 20)
            worksheet_sales.set_column('P:Q', 25)
            worksheet_sales.set_column('R:R', 50)

            worksheet_sales.set_column("S:XFD", None, None, {"hidden": True})

            # SET ROW HEIGHT FOR HEADER OF SALES SHEET 
            worksheet_sales.set_row(0, 30)
            worksheet_sales.set_row(1, 23)
            worksheet_sales.set_row(2, 23)

            # FIRST, HIDE ALL ROWS FROM 0 TO THE LAST ROW
            worksheet_sales.set_default_row(24, {'hidden': True})

            # THEN, MAKE ONLY ROWS 0 TO 25003 VISIBLE
            for row in range(0, 25003):
                worksheet_sales.set_row(row, 23, cell_data_format, {'hidden': False})

            # TO FORMAT DATE IN CELL
            date_format_khmer = workbook.add_format({
                'font_size': 11,
                'align': 'right',
                'num_format': 'yyyy-mm-dd',
                'locked': False
            })

            # APPLY FONT AND FORMAT TO COLUMN THAT HAVE DATE, 1 IS COLUMN B(DATE)
            for row_num in range(3, len(df_sale_sheet) + 3): 
                worksheet_sales.write(row_num, 1, df_sale_sheet.iloc[row_num - 3, 1], date_format_khmer)

            ########################################## END SALE SHEET ##########################################

           
            ###################################### START NONTAXABLE SHEET ######################################
            # FORMAT HEADER
            format_header = workbook.add_format({
                'align': 'center',
                'valign': 'vcenter',
                'border': 1,
                'fg_color': '#8faadc',
                'font_name': 'Khmer OS Siemreap',
                'locked': True,
                'bottom':6
            })

            df_nontaxable_sheet.to_excel(writer, index=False, startrow=1, sheet_name='NONTAXABLE')
            worksheet_nontaxable = writer.sheets['NONTAXABLE']
            worksheet_nontaxable.protect()

            for col in columns:
                worksheet_nontaxable.write(f'{col}1', '',merge_format_header1)

            worksheet_nontaxable.write('A1', 'ល.រ*', format_header)
            worksheet_nontaxable.write('B1', 'លេខសម្គាល់អត្តសញ្ញាណ*', format_header)
            worksheet_nontaxable.write('C1', 'ឈ្មោះ(ខ្មែរ)*', format_header)  
            worksheet_nontaxable.write('D1', 'ឈ្មោះ(ឡាតាំង)*', format_header)  

            # ADJUST COLUMN WIDTHS FOR NONTAXABLE SHEET
            worksheet_nontaxable.set_column('A:A', 10)
            worksheet_nontaxable.set_column('B:B', 25)
            worksheet_nontaxable.set_column('C:D', 20)

            worksheet_nontaxable.set_column("E:XFD", None, None, {"hidden": True})

            worksheet_nontaxable.set_default_row(23, {'hidden': True})

            # MAKE ONLY ROWS 0 TO 25003 VISIBLE
            for row in range(0, 25001):
                worksheet_nontaxable.set_row(row, 23, cell_data_format, {'hidden': False})
                worksheet_nontaxable.protect()

            worksheet_nontaxable.set_row(0, 25)

            ######################################### END NONTAXABLE SHEET #########################################


            ###################################### START OVERSEACOMPANY SHEET ######################################
            df_overseacompany_sheet.to_excel(writer, index=False, startrow=1, sheet_name='OVERSEACOMPANY')
            worksheet_overseacompany = writer.sheets['OVERSEACOMPANY']
            worksheet_overseacompany.protect()

            worksheet_overseacompany.write('A1', 'ល.រ*', format_header)
            worksheet_overseacompany.write('B1', 'លេខអត្ដសញ្ញាណកម្មបរទេស*', format_header)
            worksheet_overseacompany.write('C1', 'ឈ្មោះសហគ្រាស(ខ្មែរ)*', format_header)  
            worksheet_overseacompany.write('D1', 'ឈ្មោះសហគ្រាស(ឡាតាំង)*', format_header)  
            worksheet_overseacompany.write('E1', 'លេខកូដប្រទេស*', format_header)  
            worksheet_overseacompany.write('F1', 'លេខទូរស័ព្ទសហគ្រាស*', format_header)  
            worksheet_overseacompany.write('G1', 'សារអេឡិកត្រូនិក*', format_header)  
            worksheet_overseacompany.write('H1', 'អាសយដ្ឋាន*', format_header)  

            # ADJUST COLUMN WIDTHS FOR NONTAXABLE SHEET
            worksheet_overseacompany.set_column('A:H', 25)

            worksheet_overseacompany.set_column("I:XFD", None, None, {"hidden": True})

            worksheet_overseacompany.set_default_row(23, {'hidden': True})

            # MAKE ONLY ROWS 0 TO 25003 VISIBLE
            for row in range(0, 25001):
                worksheet_overseacompany.set_row(row, 23, cell_data_format, {'hidden': False})
                worksheet_overseacompany.protect()

            ####################################### END OVERSEACOMPANY SHEET ######################################


            ########################################## START NOTED SHEET ##########################################
            df_noted.to_excel(writer, index=False, sheet_name='NOTED')
            worksheet_noted = writer.sheets['NOTED']

            merge_format = workbook.add_format({
                'align': 'center',
                'valign': 'vcenter',
                'fg_color': '#70ad47',
                'font_name': "Khmer OS Siemreap",
                'font_size': 10,
            })

            merge_format_data = workbook.add_format({
                'align': 'center',
                'valign': 'vcenter',
                'font_name': "Khmer OS Siemreap",
                'font_size': 10,
            })

            worksheet_noted.merge_range('A1:C1', 'បញ្ជីរាយលេខកូដប្រទេស', merge_format)
            worksheet_noted.write('D1', '', merge_format_data)
            worksheet_noted.merge_range('E1:F1','ប្រភេទអ្នកផ្គត់ផ្គង់', merge_format)
            worksheet_noted.merge_range('E6:F6','ទម្រង់កាលបរិច្ឆេទ', merge_format)
            worksheet_noted.merge_range('E7:F7','DD-MM-YYYY', merge_format_data)
            worksheet_noted.merge_range('E9:F9','អត្រាប្រាក់រំដោះពន្ធលើប្រាក់ចំណូល', merge_format)
            worksheet_noted.write('F11', '1%')
            worksheet_noted.write('F12', '5%')
            worksheet_noted.merge_range('E14:F14','វិស័យ', merge_format)
            worksheet_noted.write('G1', '', merge_format_data)
            worksheet_noted.merge_range('H1:I1','ប្រភេទផ្គត់់ផ្គង់ទំនិញ/សេវាកម្ម', merge_format)
            worksheet_noted.merge_range('H11:I11','ចំនួនទឹកប្រាក់', merge_format)
            worksheet_noted.merge_range('H12:I12','គ្រប់តម្លៃទាំងអស់នឹងត្រូវបង្គត់', merge_format_data)
            worksheet_noted.write('J1', '', merge_format_data)
            worksheet_noted.merge_range('K1:L1','*', merge_format)
            worksheet_noted.merge_range('K2:L2','តម្រូវឱ្យបញ្ចូលទិន្នន័យ', merge_format_data)
            worksheet_noted.protect()

            worksheet_noted.set_column('A1:A1', 10)
            worksheet_noted.set_column('B1:B1', 20)
            worksheet_noted.set_column('C1:C1', 25)
            worksheet_noted.set_column('D1:D1', 7)
            worksheet_noted.set_column('E1:F1', 20)
            worksheet_noted.set_column('E1:E2', 7)
            worksheet_noted.set_column('G1:G1', 7)
            worksheet_noted.set_column('H1:I1', 30)
            worksheet_noted.set_column('H1:H1', 7)
            worksheet_noted.set_column('J1:J1', 7)
            worksheet_noted.set_column('K1:L1', 10)
            
            worksheet_noted.set_row(0, 25)
            
            # TO FORMAT DATE IN CELL
            cell_data_format_noted = workbook.add_format({
                'font_name': 'Khmer OS Siemreap',
                'font_size': 10,
                'align': 'left',
                'locked': True,
            })

            # SET ROW HEIGHT
            for row_num in range(1, len(df_noted) + 1):  
                worksheet_noted.set_row(row_num, 23, cell_data_format_noted)
                worksheet_noted.protect()

        ############################################ END NOTED SHEET ###########################################

        # READ THE FILE CONTENT
        with open(file_path, "rb") as file:
            content = file.read()

        # CREATE A FILE DOCUMENT
        file_doc_sales = frappe.get_doc({
            "doctype": "File",
            "file_name": "E-Filing-Sale.xlsx",
            "content": content
        })
        file_doc_sales.save(ignore_permissions=True)

        return {"file_url": file_doc_sales.file_url}
    
    ############################################ END SALES INVOICE FILE ##################################################


    ############################################ START POS INVOICE FILE ################################################
    elif doctype == "POS Invoice":
        pos_invoice = frappe.qb.DocType("POS Invoice")
        customer = frappe.qb.DocType("Customer")
        company = frappe.qb.DocType("Company")
        data_sales_sheet = (
            frappe.qb.from_(pos_invoice)
            .join(customer)
            .on(pos_invoice.customer == customer.name)
            .join(company)
            .on(pos_invoice.company == company.name)
            .where(pos_invoice.due_date[from_date:to_date])
            .where((pos_invoice.docstatus == 1) & (pos_invoice.status == "Consolidated"))
            .select(
                pos_invoice.name,
                pos_invoice.customer,
                pos_invoice.docstatus,
                pos_invoice.status,
                pos_invoice.invoice_number,
                pos_invoice.posting_date,
                pos_invoice.due_date,
                pos_invoice.grand_total,
                pos_invoice.total_taxes_and_charges,
                pos_invoice.net_total,
                pos_invoice.total,
                pos_invoice.currency,
                pos_invoice.remarks,
                customer.tax_id,
                company.tax_id.as_('company_tax_id'),
                customer.customer_type,
                customer.custom_foreign,
                company.custom_type_of_company,
                company.custom_prepayment_of_income_tax
            ).run(as_dict=True)
        )

        # GET DATA EXCHANGE CURRENCY
        data_exchange_currency = frappe.db.get_all(
            'Currency Exchange',
            filters={
                'from_currency': 'USD',
                'to_currency': 'KHR',
            },
            fields=['exchange_rate', 'from_currency'],
            order_by= 'date desc',
            limit=1
        )

        vatin_company = ''
        for idx, row in enumerate(data_sales_sheet, start=1):
            vatin_company = row.get("company_tax_id")

        company_type = frappe.db.get_all(
              'E Filing Company Table',
                fields=['idx', 'id', 'type_of_company_english'],
                order_by='idx'
        )
        
        # PREPARE DATA FOR SALES SHEET
        sales_invoice_data = []

        for idx, row in enumerate(data_sales_sheet, start=1):
            # GET TYPE OF CUSTOMER 
            customer_type_idx = None
            if row.get('customer_type') == "Company":
                if row.get('custom_foreign') == 1:
                    customer_type_idx = 3
                else:
                    customer_type_idx = 1
            elif row.get('customer_type') == "Individual":
                customer_type_idx = 2

            # GET TYPE OF COMPANY 
            company_type_idx = None
            for i in company_type:
                if row.get('custom_type_of_company') == i.get('type_of_company_english'):
                    company_type_idx = i.get('id')

            # GET PREPAYMENT OF INCOME TAX TYPE
            prepayment_of_income_tax_type = None
            if row.get('custom_prepayment_of_income_tax') == "1%":
                prepayment_of_income_tax_type = 1
            elif row.get('custom_prepayment_of_income_tax') == "5%":
                prepayment_of_income_tax_type = 5
            else:
                prepayment_of_income_tax_type = 0
            
            # GET GRAND TOTAL AS KHMER
            grand_total_khr = None
            for cur in data_exchange_currency:
                if row.get('currency') == "USD":
                    grand_total_khr = row.get("grand_total") * cur.get("exchange_rate")  
                else:
                    grand_total_khr = row.get("grand_total")
              
            sales_invoice_data.append({
                "ល.រ": idx,
                "កាលបរិច្ឆេទ": row.get('posting_date'),
                "លេខវិក្កយបត្រ ឬ ប្រតិវេទន៍គយ": row.get('name'),
                "ប្រភេទ": customer_type_idx,
                "លេខសម្គាល់": row.get('tax_id'),
                "ឈ្មោះ(ខ្មែរ)": row.get("customer"),
                "ឈ្មោះ(ឡាតាំង)": row.get("customer"),
                "ប្រភេទផ្គត់ផ្គង់ទំនិញ*ឬ​សេវាកម្ម": company_type_idx,
                "តម្លៃសរុបជាប់អតប*": grand_total_khr,
                "តម្លៃសរុបមិនជាប់អតប ឬ អតប អត្រា 0%": "",
                "អាករពិសេសលើទំនិញមួយចំនួន": "",
                "អាករពិសេសលើសេវាមួយចំនួន": "",
                "អាករបំភ្លឺសាធារណៈ": "",
                "អាករលើការស្នាក់នៅ": "",
                "អត្រាប្រាក់រំដោះពន្ធលើប្រាក់ចំណូល": prepayment_of_income_tax_type,
                "វិស័យ": "",
                "លេខឥណទានរតនាគារជាតិ": "",
                "បរិយាយ*": row.get('remarks'),
            })

        # PREPARE DATA FOR NONTAXABLE SHEET
        nontaxable_data = []
        for idx, row in enumerate(nontaxable_data, start=1):
            nontaxable_data.append({
                "ល.រ": idx,
                "លេខវិក្កយបត្រ ឬ ប្រតិវេទន៍គយ": row.get('name'),
                "ឈ្មោះ(ខ្មែរ)": row.get("customer_name"),
                "ឈ្មោះ(ឡាតាំង)": row.get("customer_name")
        })
        
        # PREPARE DATA FOR OVERSEACOMPANY SHEET
        overseacompany_data = []
        for idx, row in enumerate(overseacompany_data, start=1):
            overseacompany_data.append({
                "ល.រ": idx,
                "លេខវិក្កយបត្រ ឬ ប្រតិវេទន៍គយ": row.get('name'),
                "ឈ្មោះ(ខ្មែរ)": row.get("customer_name"),
                "ឈ្មោះ(ឡាតាំង)": row.get("customer_name")
        })

        df_sale_sheet = pd.DataFrame(sales_invoice_data)
        df_nontaxable_sheet = pd.DataFrame(nontaxable_data)
        df_overseacompany_sheet = pd.DataFrame(overseacompany_data)

        file_path = f"/tmp/E-Filing-Sale-{frappe.generate_hash()}.xlsx" 

        script_dir = os.path.dirname(os.path.abspath(__file__))

        # READ FILE TO WRITE TO FILE
        file_noted_of_sale_to_read = os.path.join(script_dir, 'e-Filing-Sale.xlsx')
        df_noted = pd.read_excel(file_noted_of_sale_to_read, sheet_name="NOTED")

        with pd.ExcelWriter(file_path, engine='xlsxwriter') as writer:

            ###################################### START SALES SHEET ######################################k
            df_sale_sheet.to_excel(writer, index=False, startrow=2, sheet_name='SALE')
            workbook = writer.book
            worksheet_sales = writer.sheets['SALE']

            # OPTION PROTECT SHEET BUT ALLOW MAC AND WINDOW CAN EDIT AND FORMAT DATA
            # worksheet_sales.protect(options={'format_cells': True, 'format_columns': True, 'format_rows': True})
            worksheet_sales.protect()

            columns = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R']

            cell_data_format = workbook.add_format({
                'font_name': 'Khmer OS Siemreap',
                'font_size': 10,
                'align': 'left',
                'locked': False,
            })

            top_format = workbook.add_format({
                'align': 'right',
                'valign': 'vcenter',
                'font_name': 'Khmer OS Siemreap',
                'locked': True,
                'fg_color': '#eeeeee',
            })

            top_format_data = workbook.add_format({
                'align': 'left',
                'valign': 'vcenter',
                'font_name': 'Khmer OS Siemreap',
                'bold': True,
                'locked': False,
                'fg_color': '#eeeeee',
            })

            for col in columns:
                worksheet_sales.write(f'{col}1', '', top_format)

            worksheet_sales.merge_range('A1:B1', 'លេខសម្គាល់អត្តសញ្ញាណ៖', top_format)
            worksheet_sales.write('C1', vatin_company, top_format_data)
            worksheet_sales.write('D1', 'សម្រាប់ខែ៖', top_format)
            
            text_format = workbook.add_format({
                'num_format': '@',
                'align': 'left', 
                'locked': False, 
                'font_name': 'Khmer OS Siemreap',
                'valign': 'vcenter',
                'bold': True, 
                'fg_color': '#eeeeee'
            })  # Format as text
            worksheet_sales.write('E1', formatted_date_obj, text_format)

            # SET GROUP HEADER FOR SALES SHEET
            merge_format_header = workbook.add_format({
                'align': 'center',
                'valign': 'vcenter',
                'border': 1,
                'font_name': 'Khmer OS Siemreap',
                'fg_color': '#70ad47',
                "locked": True,
            })

            merge_format_header2 = workbook.add_format({
                'align': 'center',
                'valign': 'vcenter',
                'border': 1,
                'font_name': 'Khmer OS Siemreap',
                'fg_color': '#70ad47',
                "locked": True,
                "bottom": 6
            })

            merge_format_header1 = workbook.add_format({
                'align': 'center',
                'valign': 'vcenter',
                'border': 1,
                'font_name': 'Khmer OS Siemreap',
                "locked": True,
                "bottom": 6
            })

            merge_format_header.set_text_wrap()

            # HEADER SALES SHEET
            worksheet_sales.merge_range('A2:A3', 'ល.រ*', merge_format_header)
            worksheet_sales.merge_range('B2:B3', 'កាលបរិច្ឆេទ*', merge_format_header)
            worksheet_sales.merge_range('C2:C3', 'លេខវិក្កយបត្រ ឬ ប្រតិវេទន៍គយ*', merge_format_header)
            worksheet_sales.merge_range('D2:G2', 'អ្នកទិញ', merge_format_header)
            worksheet_sales.merge_range('H2:H3', 'ប្រភេទផ្គត់ផ្គង់ទំនិញ*ឬសេវាកម្ម', merge_format_header)
            worksheet_sales.merge_range('I2:I3', 'តម្លៃសរុបជាប់អតប*', merge_format_header)
            worksheet_sales.merge_range('J2:J3', 'តម្លៃសរុបមិនជាប់ អតប ឬ អតប អត្រា ០%', merge_format_header)
            worksheet_sales.merge_range('K2:K3', 'អាករពិសេសលើទំនិញមួយចំនួន', merge_format_header)
            worksheet_sales.merge_range('L2:L3', 'អាករពិសេសលើសេវាមួយចំនួន', merge_format_header)
            worksheet_sales.merge_range('M2:M3', 'អាករបំភ្លឺសាធារណៈ', merge_format_header)
            worksheet_sales.merge_range('N2:N3', 'អាករលើការស្នាក់នៅ', merge_format_header)
            worksheet_sales.merge_range('O2:O3', 'អត្រាប្រាក់រំដោះពន្ធលើប្រាក់ចំណូល', merge_format_header)
            worksheet_sales.merge_range('P2:P3', 'វិស័យ', merge_format_header)
            worksheet_sales.merge_range('Q2:Q3', 'លេខឥណទានរតនាគារជាតិ', merge_format_header)
            worksheet_sales.merge_range('R2:R3', 'បរិយាយ*', merge_format_header)

            for col in columns:
                worksheet_sales.write(f'{col}3', '', merge_format_header1)

            worksheet_sales.write('D3', 'ប្រភេទ*', merge_format_header2)
            worksheet_sales.write('E3', 'លេខសម្គាល់*', merge_format_header2) 
            worksheet_sales.write('F3', 'ឈ្មោះ(ខ្មែរ)', merge_format_header2)  
            worksheet_sales.write('G3', 'ឈ្មោះ(ឡាតាំង)', merge_format_header2)  

            # SET COLUMN WIDTHS FOR SALES SHEET
            worksheet_sales.set_column('A:A', 7)
            worksheet_sales.set_column('B:B', 15)
            worksheet_sales.set_column('C:C', 30)
            worksheet_sales.set_column('D:D', 10)
            worksheet_sales.set_column('E:G', 15)
            worksheet_sales.set_column('H:L', 20)
            worksheet_sales.set_column('M:N', 20)
            worksheet_sales.set_column('O:O', 20)
            worksheet_sales.set_column('P:Q', 25)
            worksheet_sales.set_column('R:R', 50)

            # HIDE COLUMN FROM S TO LAST COLUMN
            worksheet_sales.set_column("S:XFD", None, None, {"hidden": True})

            # SET ROW HEIGHT FOR HEADER OF SALES SHEET 
            worksheet_sales.set_row(0, 30)
            worksheet_sales.set_row(1, 23)
            worksheet_sales.set_row(2, 23)

            # FIRST, HIDE ALL ROWS FROM 0 TO THE LAST ROW
            worksheet_sales.set_default_row(24, {'hidden': True})

            # THEN, MAKE ONLY ROWS 0 TO 25003 VISIBLE
            for row in range(0, 25003):
                worksheet_sales.set_row(row, 23, cell_data_format, {'hidden': False})

            # TO FORMAT DATE IN CELL
            date_format_khmer = workbook.add_format({
                'font_size': 11,
                'align': 'right',
                'num_format': 'yyyy-mm-dd',
                'locked': False
            })

            # APPLY FONT AND FORMAT TO COLUMN THAT HAVE DATE, 1 IS COLUMN B(DATE)
            for row_num in range(3, len(df_sale_sheet) + 3): 
                worksheet_sales.write(row_num, 1, df_sale_sheet.iloc[row_num - 3, 1], date_format_khmer)

            ########################################## END SALE SHEET ##########################################

           
            ###################################### START NONTAXABLE SHEET ######################################
            # FORMAT HEADER
            format_header = workbook.add_format({
                'align': 'center',
                'valign': 'vcenter',
                'border': 1,
                'fg_color': '#8faadc',
                'font_name': 'Khmer OS Siemreap',
                'locked': True,
                'bottom':6
            })

            df_nontaxable_sheet.to_excel(writer, index=False, startrow=1, sheet_name='NONTAXABLE')
            worksheet_nontaxable = writer.sheets['NONTAXABLE']
            worksheet_nontaxable.protect()

            for col in columns:
                worksheet_nontaxable.write(f'{col}1', '',merge_format_header1)

            worksheet_nontaxable.write('A1', 'ល.រ*', format_header)
            worksheet_nontaxable.write('B1', 'លេខសម្គាល់អត្តសញ្ញាណ*', format_header)
            worksheet_nontaxable.write('C1', 'ឈ្មោះ(ខ្មែរ)*', format_header)  
            worksheet_nontaxable.write('D1', 'ឈ្មោះ(ឡាតាំង)*', format_header)  

            # ADJUST COLUMN WIDTHS FOR NONTAXABLE SHEET
            worksheet_nontaxable.set_column('A:A', 10)
            worksheet_nontaxable.set_column('B:B', 25)
            worksheet_nontaxable.set_column('C:D', 20)

            worksheet_nontaxable.set_column("E:XFD", None, None, {"hidden": True})

            worksheet_nontaxable.set_default_row(23, {'hidden': True})

            # MAKE ONLY ROWS 0 TO 25003 VISIBLE
            for row in range(0, 25001):
                worksheet_nontaxable.set_row(row, 23, cell_data_format, {'hidden': False})
                worksheet_nontaxable.protect()

            worksheet_nontaxable.set_row(0, 25)

            ######################################### END NONTAXABLE SHEET #########################################


            ###################################### START OVERSEACOMPANY SHEET ######################################
            df_overseacompany_sheet.to_excel(writer, index=False, startrow=1, sheet_name='OVERSEACOMPANY')
            worksheet_overseacompany = writer.sheets['OVERSEACOMPANY']
            worksheet_overseacompany.protect()

            worksheet_overseacompany.write('A1', 'ល.រ*', format_header)
            worksheet_overseacompany.write('B1', 'លេខអត្ដសញ្ញាណកម្មបរទេស*', format_header)
            worksheet_overseacompany.write('C1', 'ឈ្មោះសហគ្រាស(ខ្មែរ)*', format_header)  
            worksheet_overseacompany.write('D1', 'ឈ្មោះសហគ្រាស(ឡាតាំង)*', format_header)  
            worksheet_overseacompany.write('E1', 'លេខកូដប្រទេស*', format_header)  
            worksheet_overseacompany.write('F1', 'លេខទូរស័ព្ទសហគ្រាស*', format_header)  
            worksheet_overseacompany.write('G1', 'សារអេឡិកត្រូនិក*', format_header)  
            worksheet_overseacompany.write('H1', 'អាសយដ្ឋាន*', format_header)  

            # ADJUST COLUMN WIDTHS FOR NONTAXABLE SHEET
            worksheet_overseacompany.set_column('A:H', 25)

            worksheet_overseacompany.set_column("I:XFD", None, None, {"hidden": True})

            worksheet_overseacompany.set_default_row(23, {'hidden': True})

            # MAKE ONLY ROWS 0 TO 25003 VISIBLE
            for row in range(0, 25001):
                worksheet_overseacompany.set_row(row, 23, cell_data_format, {'hidden': False})
                worksheet_overseacompany.protect()

            ####################################### END OVERSEACOMPANY SHEET ######################################


            ########################################## START NOTED SHEET ##########################################
            df_noted.to_excel(writer, index=False, sheet_name='NOTED')
            worksheet_noted = writer.sheets['NOTED']

            merge_format = workbook.add_format({
                'align': 'center',
                'valign': 'vcenter',
                'fg_color': '#70ad47',
                'font_name': "Khmer OS Siemreap",
                'font_size': 10,
            })

            merge_format_data = workbook.add_format({
                'align': 'center',
                'valign': 'vcenter',
                'font_name': "Khmer OS Siemreap",
                'font_size': 10,
            })

            worksheet_noted.merge_range('A1:C1', 'បញ្ជីរាយលេខកូដប្រទេស', merge_format)
            worksheet_noted.write('D1', '', merge_format_data)
            worksheet_noted.merge_range('E1:F1','ប្រភេទអ្នកផ្គត់ផ្គង់', merge_format)
            worksheet_noted.merge_range('E6:F6','ទម្រង់កាលបរិច្ឆេទ', merge_format)
            worksheet_noted.merge_range('E7:F7','DD-MM-YYYY', merge_format_data)
            worksheet_noted.merge_range('E9:F9','អត្រាប្រាក់រំដោះពន្ធលើប្រាក់ចំណូល', merge_format)
            worksheet_noted.write('F11', '1%')
            worksheet_noted.write('F12', '5%')
            worksheet_noted.merge_range('E14:F14','វិស័យ', merge_format)
            worksheet_noted.write('G1', '', merge_format_data)
            worksheet_noted.merge_range('H1:I1','ប្រភេទផ្គត់់ផ្គង់ទំនិញ/សេវាកម្ម', merge_format)
            worksheet_noted.merge_range('H11:I11','ចំនួនទឹកប្រាក់', merge_format)
            worksheet_noted.merge_range('H12:I12','គ្រប់តម្លៃទាំងអស់នឹងត្រូវបង្គត់', merge_format_data)
            worksheet_noted.write('J1', '', merge_format_data)
            worksheet_noted.merge_range('K1:L1','*', merge_format)
            worksheet_noted.merge_range('K2:L2','តម្រូវឱ្យបញ្ចូលទិន្នន័យ', merge_format_data)
            worksheet_noted.protect()

            worksheet_noted.set_column('A1:A1', 10)
            worksheet_noted.set_column('B1:B1', 20)
            worksheet_noted.set_column('C1:C1', 25)
            worksheet_noted.set_column('D1:D1', 7)
            worksheet_noted.set_column('E1:F1', 20)
            worksheet_noted.set_column('E1:E2', 7)
            worksheet_noted.set_column('G1:G1', 7)
            worksheet_noted.set_column('H1:I1', 30)
            worksheet_noted.set_column('H1:H1', 7)
            worksheet_noted.set_column('J1:J1', 7)
            worksheet_noted.set_column('K1:L1', 10)
            
            worksheet_noted.set_row(0, 25)
            
            # TO FORMAT DATE IN CELL
            cell_data_format_noted = workbook.add_format({
                'font_name': 'Khmer OS Siemreap',
                'font_size': 10,
                'align': 'left',
                'locked': True,
            })

            # SET ROW HEIGHT
            for row_num in range(1, len(df_noted) + 1):  
                worksheet_noted.set_row(row_num, 23, cell_data_format_noted)
                worksheet_noted.protect()

        ############################################ END NOTED SHEET ###########################################

        # READ THE FILE CONTENT
        with open(file_path, "rb") as file:
            content = file.read()

        # CREATE A FILE DOCUMENT
        file_doc_sales = frappe.get_doc({
            "doctype": "File",
            "file_name": "E-Filing-Sale.xlsx",
            "content": content
        })
        file_doc_sales.save(ignore_permissions=True)

        return {"file_url": file_doc_sales.file_url}
    
    ############################################ END POS INVOICE FILE ##################################################

    
    ############################################ START PURCHASE INVOICE FILE ###########################################
    elif doctype == "Purchase Invoice":
        purchase_invoice = frappe.qb.DocType("Purchase Invoice")
        company = frappe.qb.DocType("Company")
        supplier = frappe.qb.DocType("Supplier")
        data_purchase_sheet = (
            frappe.qb.from_(purchase_invoice)
            .join(company)
            .on(purchase_invoice.company == company.name)
            .join(supplier)
            .on(supplier.name == purchase_invoice.supplier)
            .where(purchase_invoice.posting_date[from_date:to_date])
            .where(purchase_invoice.docstatus == 1)
            .select(
                purchase_invoice.posting_date,
                purchase_invoice.bill_no.as_('name'),
                purchase_invoice.supplier_name,
                purchase_invoice.name.as_('name_reference'),
                purchase_invoice.tax_id.as_('supplier_tax_id'),
                purchase_invoice.currency,
                purchase_invoice.conversion_rate,
                purchase_invoice.taxes_and_charges,
                purchase_invoice.grand_total,
                purchase_invoice.remarks,
                purchase_invoice.taxes_and_charges,
                supplier.supplier_type,
                company.custom_type_of_company,
                company.tax_id.as_('company_tax_id')
            ).run(as_dict=True)
        )

        # GET DATA EXCHANGE CURRENCY
        data_exchange_currency = frappe.db.get_all(
            'Currency Exchange',
            filters={
                'from_currency': 'USD',
                'to_currency': 'KHR',
            },
            fields=['exchange_rate', 'from_currency'],
            order_by= 'date desc',
            limit=1
        )

        vatin_company = ''
        for idx, row in enumerate(data_purchase_sheet, start=1):
            vatin_company = row.get("company_tax_id")

        company_type = frappe.db.get_all(
                'E Filing Company Table',
                fields=['idx', 'type_of_company_english'],
                order_by='idx'
        )

        # PREPARE DATA FOR PURCHASE SHEET
        purchase_invoice_data = []
        for idx, row in enumerate(data_purchase_sheet, start=1):

            # GET TYPE OF SUPPLIER 
            supplier_type_idx = None
            if row.get('supplier_type') == "Company":
                if row.get('custom_foreign') == 1:
                    supplier_type_idx = 3
                else:
                    supplier_type_idx = 1
            elif row.get('supplier_type') == "Individual":
                supplier_type_idx = 2

            # GET TYPE OF COMPANY
            company_type_idx = None
            for i in company_type:
                if row.get('custom_type_of_company') == i.get('type_of_company_english'):
                    company_type_idx = i.get('idx')
                if row.get('supplier_type') == "Individual":
                    company_type_idx = 3

            # GET GRAND TOTAL AS KHMER
            grand_total_khr = None
            for cur in data_exchange_currency:
                if row.get('currency') == "USD":
                    grand_total_khr = row.get("grand_total") * cur.get("exchange_rate")  
                else:
                    grand_total_khr = row.get("grand_total")
              
            purchase_invoice_data.append({
                "ល.រ": idx,
                "កាលបរិច្ឆេទ": row.get('posting_date'),
                "លេខវិក្កយបត្រ ឬ ប្រតិវេទន៍គយ": row.get('name'),
                "ប្រភេទ": supplier_type_idx,
                "លេខសម្គាល់": row.get('supplier_tax_id'),
                "ឈ្មោះ(ខ្មែរ)": row.get("supplier_name"),
                "ឈ្មោះ(ឡាតាំង)": row.get("supplier_name"),
                "ប្រភេទផ្គត់ផ្គង់ទំនិញ*ឬ​សេវាកម្ម": company_type_idx,
                "តម្លៃសរុបជាប់អតប*": grand_total_khr,
                "តម្លៃសរុបមិនជាប់អតប": "",
                "បរិយាយ*": row.get('remarks'),
            })

        # PREPARE DATA FOR NONTAXABLE SHEET
        nontaxable_data = []
        for idx, row in enumerate(nontaxable_data, start=1):
            nontaxable_data.append({
                "ល.រ": idx,
                "លេខវិក្កយបត្រ ឬ ប្រតិវេទន៍គយ": row.get('name'),
                "ឈ្មោះ(ខ្មែរ)": row.get("customer_name"),
                "ឈ្មោះ(ឡាតាំង)": row.get("customer_name")
        })
        
        # PREPARE DATA FOR OVERSEACOMPANY SHEET
        overseacompany_data = []
        for idx, row in enumerate(overseacompany_data, start=1):
            overseacompany_data.append({
                "ល.រ": idx,
                "លេខវិក្កយបត្រ ឬ ប្រតិវេទន៍គយ": row.get('name'),
                "ឈ្មោះ(ខ្មែរ)": row.get("customer_name"),
                "ឈ្មោះ(ឡាតាំង)": row.get("customer_name")
        })

        df_purchase_sheet = pd.DataFrame(purchase_invoice_data)
        df_nontaxable_sheet = pd.DataFrame(nontaxable_data)
        df_overseacompany_sheet = pd.DataFrame(overseacompany_data)

        file_path = f"/tmp/E-Filing-Purchase-{frappe.generate_hash()}.xlsx" 

        script_dir = os.path.dirname(os.path.abspath(__file__))

        # READ FILE TO WRITE TO FILE
        file_noted_of_purchase_to_read = os.path.join(script_dir, 'e-Filing-Purchase.xlsx')
        df_noted = pd.read_excel(file_noted_of_purchase_to_read, sheet_name="NOTED")

        with pd.ExcelWriter(file_path, engine='xlsxwriter') as writer:

        ######################################## START PURCHASE SHEET ########################################
            df_purchase_sheet.to_excel(writer, index=False, startrow=2, sheet_name='PURCHASE')
            workbook = writer.book
            worksheet_purchase = writer.sheets['PURCHASE']

            worksheet_purchase.protect(options={'format_cells': True, 'format_columns': True, 'format_rows': True})

            cell_data_format = workbook.add_format({
                'font_name': 'Khmer OS Siemreap',
                'font_size': 10,
                'align': 'left',
                'locked': False,
            })

            top_format = workbook.add_format({
                'align': 'right',
                'valign': 'vcenter',
                'font_name': 'Khmer OS Siemreap',
                'locked': True,
            })

            top_format_data = workbook.add_format({
                'align': 'left',
                'valign': 'vcenter',
                'font_name': 'Khmer OS Siemreap',
                'bold': True,
                'locked': False
            })

            worksheet_purchase.merge_range('A1:B1', 'លេខសម្គាល់អត្តសញ្ញាណ៖', top_format)
            worksheet_purchase.write('C1', vatin_company, top_format_data)
            worksheet_purchase.write('D1', 'សម្រាប់ខែ៖', top_format)
            worksheet_purchase.write('E1', formatted_date_obj, top_format_data)

            # SET GROUP HEADER FOR PURCHASE SHEET
            merge_format_header = workbook.add_format({
                'align': 'center',
                'valign': 'vcenter',
                'border': 1,
                'font_name': 'Khmer OS Siemreap',
                'fg_color': '#8faadc',
                "locked": True,
                "bottom": 6
            })
            merge_format_header.set_text_wrap() 

            # អ្នកផ្គត់ផ្គង់
            merge_format_header_first = workbook.add_format({
                'align': 'center',
                'valign': 'vcenter',
                'border': 1,
                'font_name': 'Khmer OS Siemreap',
                'fg_color': '#8faadc',
                "locked": True,
            })

            # HEADER PURCHASE SHEET
            worksheet_purchase.merge_range('A2:A3', 'ល.រ*', merge_format_header)
            worksheet_purchase.merge_range('B2:B3', 'កាលបរិច្ឆេទ*', merge_format_header)
            worksheet_purchase.merge_range('C2:C3', 'លេខវិក្កយបត្រ ឬ ប្រតិវេទន៍គយ*', merge_format_header)
            worksheet_purchase.merge_range('D2:G2', 'អ្នកផ្គត់ផ្គង់', merge_format_header_first)
            worksheet_purchase.write('D3', 'ប្រភេទ*', merge_format_header)
            worksheet_purchase.write('E3', 'លេខសម្គាល់*', merge_format_header) 
            worksheet_purchase.write('F3', 'ឈ្មោះ(ខ្មែរ)', merge_format_header)  
            worksheet_purchase.write('G3', 'ឈ្មោះ(ឡាតាំង)', merge_format_header)  
            worksheet_purchase.merge_range('H2:H3', 'ប្រភេទផ្គត់ផ្គង់ទំនិញ*ឬសេវាកម្ម', merge_format_header)
            worksheet_purchase.merge_range('I2:I3', 'តម្លៃសរុបជាប់អតប*', merge_format_header)
            worksheet_purchase.merge_range('J2:J3', 'តម្លៃសរុបមិនជាប់អតប', merge_format_header)
            worksheet_purchase.merge_range('K2:K3', 'បរិយាយ*', merge_format_header)

            # SET COLUMN WIDTHS FOR PURCHASE SHEET
            worksheet_purchase.set_column('A:A', 7)
            worksheet_purchase.set_column('B:B', 15)
            worksheet_purchase.set_column('C:C', 30)
            worksheet_purchase.set_column('D:D', 10)
            worksheet_purchase.set_column('E:G', 20)
            worksheet_purchase.set_column('H:J', 20)
            worksheet_purchase.set_column('K:K', 50)

            worksheet_purchase.set_column("L:XFD", None, None, {"hidden": True})

            # SET ROW HEIGHT FOR PURCHASE SHEET
            worksheet_purchase.set_row(0, 30)
            worksheet_purchase.set_row(1, 23)
            worksheet_purchase.set_row(2, 23)

            # FIRST, HIDE ALL ROWS FROM 0 TO THE LAST ROW
            worksheet_purchase.set_default_row(23, {'hidden': True})

            # THEN, MAKE ONLY ROWS 0 TO 25003 VISIBLE
            for row in range(0, 25003):
                worksheet_purchase.set_row(row, 23, cell_data_format, {'hidden': False})

            date_format_khmer = workbook.add_format({
                'font_name': 'Khmer OS Siemreap',
                'font_size': 10,
                'align': 'left',
                'num_format': 'yyyy-mm-dd',
                'locked': False
            })

            for row_num in range(3, len(df_purchase_sheet) + 3):  
                worksheet_purchase.write(row_num, 1, df_purchase_sheet.iloc[row_num - 3, 1], date_format_khmer)


        ######################################## END PURCHASE SHEET ########################################
            
            
        ###################################### START NONTAXABLE SHEET ######################################
            # FORMAT HEADER
            format_header = workbook.add_format({
                'align': 'center',
                'valign': 'vcenter',
                'border': 1,
                'fg_color': '#8faadc',
                'font_name': 'Khmer OS Siemreap',
                'locked': True,
                'bottom': 6
            })

            df_nontaxable_sheet.to_excel(writer, index=False, startrow=1, sheet_name='NONTAXABLE')
            worksheet_nontaxable = writer.sheets['NONTAXABLE']
            worksheet_nontaxable.protect()

            worksheet_nontaxable.write('A1', 'ល.រ*', format_header)
            worksheet_nontaxable.write('B1', 'លេខវិក្កយបត្រ ឬ ប្រតិវេទន៍គយ*', format_header)
            worksheet_nontaxable.write('C1', 'ឈ្មោះ(ខ្មែរ)*', format_header)  
            worksheet_nontaxable.write('D1', 'ឈ្មោះ(ឡាតាំង)*', format_header)  

            # ADJUST COLUMN WIDTHS FOR NONTAXABLE SHEET
            worksheet_nontaxable.set_column('A:A', 10)
            worksheet_nontaxable.set_column('B:B', 25)
            worksheet_nontaxable.set_column('C:D', 20)

            # ADJUST ROW HEIGHT FOR NONTAXABLE SHEET
            worksheet_nontaxable.set_default_row(23, {'hidden': True})

            # MAKE ONLY ROWS 0 TO 25001 VISIBLE
            for row in range(0, 25001):
                worksheet_nontaxable.set_row(row, 23, cell_data_format, {'hidden': False})
                worksheet_nontaxable.protect()

        ###################################### END NONTAXABLE SHEET ######################################


        ################################### START OVERSEACOMPANY SHEET ###################################
            df_overseacompany_sheet.to_excel(writer, index=False, startrow=1, sheet_name='OVERSEACOMPANY')
            worksheet_overseacompany = writer.sheets['OVERSEACOMPANY']

            worksheet_overseacompany.write('A1', 'ល.រ*', format_header)
            worksheet_overseacompany.write('B1', 'លេខអត្ដសញ្ញាណកម្មបរទេស*', format_header)
            worksheet_overseacompany.write('C1', 'ឈ្មោះសហគ្រាស(ខ្មែរ)*', format_header)  
            worksheet_overseacompany.write('D1', 'ឈ្មោះសហគ្រាស(ឡាតាំង)*', format_header)  
            worksheet_overseacompany.write('E1', 'លេខកូដប្រទេស*', format_header)  
            worksheet_overseacompany.write('F1', 'លេខទូរស័ព្ទសហគ្រាស*', format_header)  
            worksheet_overseacompany.write('G1', 'សារអេឡិកត្រូនិក*', format_header)  
            worksheet_overseacompany.write('H1', 'អាសយដ្ឋាន*', format_header)  

            # ADJUST COLUMN WIDTHS FOR NONTAXABLE SHEET
            worksheet_overseacompany.set_column('A:H', 25)

            # ADJUST ROW HEIGHT FOR NONTAXABLE SHEET
            worksheet_overseacompany.set_default_row(23, {'hidden': True})

            # MAKE ONLY ROWS 0 TO 25001 VISIBLE
            for row in range(0, 25001):
                worksheet_overseacompany.set_row(row, 23, cell_data_format, {'hidden': False})
                worksheet_overseacompany.protect()

        ################################### END OVERSEACOMPANY SHEET ####################################


        ###################################### START NOTED SHEET ########################################
            df_noted.to_excel(writer, index=False, sheet_name='NOTED')
            worksheet_noted = writer.sheets['NOTED']
            worksheet_noted.protect()
            
            merge_format = workbook.add_format({
                'align': 'center',
                'valign': 'vcenter',
                'fg_color': '#95d660',
                'font_name': "Khmer OS Siemreap",
                'font_size': 10,
            })
            merge_format.set_border()

            format_cell_data = workbook.add_format({
                'align': 'center',
                'font_name': "Khmer OS Siemreap",
                'font_size': 10,
            })

            worksheet_noted.merge_range('A1:C1', 'បញ្ជីរាយលេខកូដប្រទេស', merge_format)
            worksheet_noted.write('D1','', '')
            worksheet_noted.merge_range('E1:F1','ប្រភេទអ្នកផ្គត់ផ្គង់', merge_format)
            worksheet_noted.merge_range('E6:F6','ទម្រង់កាលបរិច្ឆេទ', merge_format)
            worksheet_noted.merge_range('E7:F7','DD-MM-YYYY', format_cell_data)
            worksheet_noted.merge_range('E9:F9','ចំនួនទឹកប្រាក់', merge_format)
            worksheet_noted.merge_range('E10:F10','គ្រប់តម្លៃទាំងអស់នឹងត្រូវបង្គត់', format_cell_data)
            worksheet_noted.write('G1', '', '')
            worksheet_noted.merge_range('H1:I1','ប្រភេទផ្គត់់ផ្គង់ទំនិញ/សេវាកម្ម', merge_format)
            worksheet_noted.write('J1', '', '')
            worksheet_noted.merge_range('K1:L1','*', merge_format)
            worksheet_noted.merge_range('K2:L2','តម្រូវឱ្យបញ្ចូលទិន្នន័យ', format_cell_data)
            worksheet_noted = writer.sheets['NOTED']
            worksheet_noted.protect()

            worksheet_noted.set_column('B1:B1', 20)
            worksheet_noted.set_column('C1:C1', 25)
            worksheet_noted.set_column('D1:D1', 7)
            worksheet_noted.set_column('E1:F1', 20)
            worksheet_noted.set_column('E1:E2', 7)
            worksheet_noted.set_column('G1:G1', 7)
            worksheet_noted.set_column('H1:I1', 30)
            worksheet_noted.set_column('H1:H1', 7)
            worksheet_noted.set_column('J1:J1', 7)
            worksheet_noted.set_column('K1:L1', 10)
            worksheet_noted.set_row(0, 25)

            cell_data_format_noted = workbook.add_format({
                'font_name': 'Khmer OS Siemreap',
                'font_size': 10,
                'align': 'left',
                'locked': True,
            })

            # SET ROW HEIGHT AND FONT SIZE
            for row_num in range(1, len(df_noted) + 100):  
                worksheet_noted.set_row(row_num, 23, cell_data_format_noted)
                worksheet_noted.protect()

        ###################################### END NOTED SHEET #######################################


        # READ THE FILE CONTENT
        with open(file_path, "rb") as file:
            content = file.read()

        # CREATE A FILE DOCUMENT
        file_doc_purchase = frappe.get_doc({
            "doctype": "File",
            "file_name": "E-Filing-Purchase.xlsx",
            "content": content
        })
        file_doc_purchase.save(ignore_permissions=True)

        return {"file_url": file_doc_purchase.file_url}
    
    ############################################ END PURCHASE INVOICE FILE  ############################################


#################################################### END FUNCTION ######################################################
