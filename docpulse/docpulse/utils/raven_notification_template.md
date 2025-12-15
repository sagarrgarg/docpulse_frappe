# Raven Document Notification Template for Document Tracker Renewal Log

## Message Content (Jinja Template)

```jinja
📋 **Document Renewal Alert - {{ doc.company }}**

**Renewal Log:** {{ doc.name }}
**Date:** {{ frappe.format_date(doc.log_date) }}
**Total Documents Flagged:** {{ doc.total_documents_flagged }}

---

## 📊 Summary by Severity

{% set overdue_count = doc.renewal_pending_items | selectattr("severity", "equalto", "Overdue") | list | count %}
{% set due_today_count = doc.renewal_pending_items | selectattr("severity", "equalto", "Due Today") | list | count %}
{% set due_soon_count = doc.renewal_pending_items | selectattr("severity", "equalto", "Due Soon") | list | count %}

🔴 **Overdue:** {{ overdue_count }} document(s)
🟡 **Due Today:** {{ due_today_count }} document(s)
🟢 **Due Soon:** {{ due_soon_count }} document(s)

---

## 📄 Documents Requiring Attention

{% for item in doc.renewal_pending_items %}
{% if item.severity == "Overdue" %}
🔴 **{{ item.document_name }}**
{% elif item.severity == "Due Today" %}
🟡 **{{ item.document_name }}**
{% else %}
🟢 **{{ item.document_name }}**
{% endif %}
- **Category:** {{ item.category or "N/A" }}
- **Authority:** {{ item.authority or "N/A" }}
- **Expiry Date:** {{ frappe.format_date(item.expiry_date) }}
- **Days to Expiry:** {{ item.days_to_expiry }} days
- **Owner:** {{ item.owner_person or "Unassigned" }}
- **Status:** {{ item.current_status }}
- **Document:** [View Document]({{ frappe.utils.get_url_to_form("Document Tracker List", item.document) }})

{% endfor %}

---

## ⚡ Action Required

Please review and take necessary action on the documents listed above. Documents marked as **Overdue** require immediate attention.

**View Full Renewal Log:** [{{ doc.name }}]({{ frappe.utils.get_url_to_form("Document Tracker Renewal Log", doc.name) }})

---
*Generated automatically by DocPulse on {{ frappe.format_datetime(frappe.utils.now()) }}*
```

## Alternative Compact Version

```jinja
🚨 **Document Renewal Alert**

**Company:** {{ doc.company }}
**Log Date:** {{ frappe.format_date(doc.log_date) }}
**Total Documents:** {{ doc.total_documents_flagged }}

**Documents:**
{% for item in doc.renewal_pending_items %}
{% if item.severity == "Overdue" %}🔴{% elif item.severity == "Due Today" %}🟡{% else %}🟢{% endif %} {{ item.document_name }} - Expires: {{ frappe.format_date(item.expiry_date) }} ({{ item.days_to_expiry }} days)
{% endfor %}

[View Renewal Log]({{ frappe.utils.get_url_to_form("Document Tracker Renewal Log", doc.name) }})
```

## Minimal Version (for Quick Notifications)

```jinja
📋 **Renewal Alert - {{ doc.company }}**

{{ doc.total_documents_flagged }} document(s) require renewal attention.

{% if doc.renewal_pending_items | selectattr("severity", "equalto", "Overdue") | list | count > 0 %}
⚠️ **{{ doc.renewal_pending_items | selectattr("severity", "equalto", "Overdue") | list | count }} document(s) are OVERDUE**
{% endif %}

[View Details]({{ frappe.utils.get_url_to_form("Document Tracker Renewal Log", doc.name) }})
```

## Grouped by Owner Version

```jinja
📋 **Document Renewal Alert - {{ doc.company }}**

**Renewal Log:** {{ doc.name }}
**Date:** {{ frappe.format_date(doc.log_date) }}

---

{% set owners = {} %}
{% for item in doc.renewal_pending_items %}
{% if item.owner_person %}
{% if item.owner_person not in owners %}
{% set _ = owners.update({item.owner_person: []}) %}
{% endif %}
{% set _ = owners[item.owner_person].append(item) %}
{% endif %}
{% endfor %}

{% for owner, items in owners.items() %}
**👤 {{ owner }}** ({{ items | count }} document(s))

{% for item in items %}
{% if item.severity == "Overdue" %}🔴{% elif item.severity == "Due Today" %}🟡{% else %}🟢{% endif %} **{{ item.document_name }}**
- Expires: {{ frappe.format_date(item.expiry_date) }} ({{ item.days_to_expiry }} days)
- Category: {{ item.category or "N/A" }}

{% endfor %}
{% endfor %}

[View Full Renewal Log]({{ frappe.utils.get_url_to_form("Document Tracker Renewal Log", doc.name) }})
```
