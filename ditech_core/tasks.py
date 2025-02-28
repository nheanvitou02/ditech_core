import frappe
from erpnext.accounts.doctype.journal_entry.journal_entry import make_reverse_journal_entry
from frappe.utils import nowdate

###############################################################################
# This function use to daily auto reverse journal entry
# Request:
#   
# Response:
#   
# Taks:
#   TASK-2024-00417, 
# History
# 18-06-2024  Pisethpong    Created
###############################################################################
def auto_reverse_journal_entry():
    frappe.enqueue(method=auto_reverse_journal_entry_q, queue='short', timeout=1000)

### END function ###

###############################################################################
# This function use to enqueue for auto reverse journal entry
# Request:
#   
# Response:
#   
# Taks:
#   TASK-2024-00417, 
# History
# 18-06-2024  Pisethpong    Created
###############################################################################
def auto_reverse_journal_entry_q():
    try:
        get_journal_entry = frappe.db.get_all("Journal Entry", 
                                                pluck='name', 
                                                filters={
                                                        'custom_reversed_journal_entry': 1,
                                                        'custom_schedule_date': nowdate()
                                                    }
                                            )
        
        for je in get_journal_entry:
            everse = make_reverse_journal_entry(je)
            everse.update({
                        'posting_date': nowdate(),
                        'custom_reversed_journal_entry': 0,
                        'custom_schedule_date': ''
                    })
            everse.insert()
            everse.submit()

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"{e}")

### END function ###
