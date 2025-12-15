# Copyright (c) 2025, DocPulse and contributors
# For license information, please see license.txt

"""
Daily cron job to create renewal logs for documents that need renewal attention.
Runs once daily to generate Document Tracker Renewal Log records.
"""

import frappe
from frappe import _
from frappe.utils import getdate, today, date_diff


def create_daily_renewal_logs():
	"""
	Create daily renewal logs for all companies.
	This function is called by the scheduler.
	"""
	import datetime
	start_time = datetime.datetime.now()
	frappe.logger().info(f"[Renewal Log Scheduler] Job started at {start_time}")
	
	try:
		# Get all companies
		companies = frappe.get_all("Company", fields=["name"])
		
		if not companies:
			frappe.logger().info("[Renewal Log Scheduler] No companies found. Skipping renewal log creation.")
			return
		
		frappe.logger().info(f"[Renewal Log Scheduler] Processing {len(companies)} companies")
		
		for company in companies:
			create_renewal_log_for_company(company.name)
		
		end_time = datetime.datetime.now()
		duration = (end_time - start_time).total_seconds()
		frappe.logger().info(
			f"[Renewal Log Scheduler] Job completed successfully at {end_time} "
			f"(Duration: {duration:.2f}s, Companies: {len(companies)})"
		)
		
	except Exception as e:
		end_time = datetime.datetime.now()
		duration = (end_time - start_time).total_seconds()
		frappe.logger().error(
			f"[Renewal Log Scheduler] Job failed at {end_time} "
			f"(Duration: {duration:.2f}s) - Error: {str(e)}"
		)
		frappe.log_error(
			title=_("Error in Daily Renewal Log Creation"),
			message=str(e)
		)
		raise


def create_renewal_log_for_company(company):
	"""
	Create renewal log for a specific company.
	Creates a new log on every scheduler run if there are documents requiring renewal.
	
	Args:
		company: Company name
	"""
	today_date = getdate(today())
	
	# Query documents that need renewal attention
	documents = get_documents_for_renewal(company, today_date)
	
	if not documents:
		frappe.logger().info(f"No documents requiring renewal for company {company} on {today_date}. Skipping log creation.")
		return
	
	# Always create a new renewal log on each scheduler run
	# Each log gets a unique name from the naming series
	renewal_log = frappe.new_doc("Document Tracker Renewal Log")
	renewal_log.company = company
	renewal_log.log_date = today_date
	
	# Add child rows
	for doc in documents:
		expiry_date = getdate(doc.expiry_date)
		days_to_expiry = date_diff(expiry_date, today_date)
		
		# Determine severity
		if days_to_expiry < 0:
			severity = "Overdue"
		elif days_to_expiry == 0:
			severity = "Due Today"
		else:
			severity = "Due Soon"
		
		renewal_log.append("renewal_pending_items", {
			"document": doc.name,
			"document_name": doc.document_name,
			"category": doc.document_category,
			"authority": doc.authority,
			"issue_date": doc.issue_date,
			"expiry_date": doc.expiry_date,
			"remind_from_date": doc.remind_from_date,
			"days_to_expiry": days_to_expiry,
			"severity": severity,
			"owner_person": doc.owner_person,
			"current_status": doc.status
		})
	
	# Save and submit with ignore_permissions for automated submission
	renewal_log.insert(ignore_permissions=True)
	renewal_log.flags.ignore_permissions = True
	renewal_log.submit()
	
	frappe.logger().info(
		f"Created renewal log {renewal_log.name} for company {company} "
		f"with {len(documents)} documents."
	)


def get_documents_for_renewal(company, today_date):
	"""
	Get documents that need renewal attention for a company.
	
	Args:
		company: Company name
		today_date: Date to check against
		
	Returns:
		List of Document Tracker List documents
	"""
	filters = {
		"company": company,
		"is_expiry_based": 1,
		"is_renewable": 1,
		"lifecycle_state": "Current",
		"docstatus": 1,  # only submitted documents
		"status": ["not in", ["Draft", "Renewed", "Revoked", "Cancelled"]]
	}
	
	# Get all current submitted documents that are renewable
	all_documents = frappe.get_all(
		"Document Tracker List",
		filters=filters,
		fields=[
			"name", "document_name", "document_category", "authority",
			"issue_date", "expiry_date", "remind_from_date", "status",
			"owner_person", "department"
		]
	)
	
	# Filter documents where today >= remind_from_date and expiry_date exists
	documents_for_renewal = []
	for doc_dict in all_documents:
		# Skip if no expiry date
		if not doc_dict.expiry_date:
			continue
		
		# Check if remind_from_date has been reached
		if doc_dict.remind_from_date and getdate(doc_dict.remind_from_date) <= today_date:
			# Load full doc only when needed (for department access in on_submit)
			doc = frappe.get_doc("Document Tracker List", doc_dict.name)
			documents_for_renewal.append(doc)
	
	return documents_for_renewal
