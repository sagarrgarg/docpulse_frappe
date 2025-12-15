# Copyright (c) 2025, DocPulse and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, getdate, today, date_diff


class DocumentTrackerList(Document):
	def validate(self):
		"""Validate document and compute system fields"""
		self.compute_remind_from_date()
		self.validate_current_document_uniqueness()
		self.compute_validity_fields()

		# Validate required fields
		if not self.document_name:
			frappe.throw(_("Document Name is required"))
		if not self.company:
			frappe.throw(_("Company is required"))
		
		# Expiry date validation - only enforce on submit, allow draft without it
		if self.docstatus == 1 and self.is_expiry_based and not self.expiry_date:
			frappe.throw(_("Expiry Date is required when Is Expiry Based is checked"))
		
		# Auto-set correct status on first submit only
		# This overrides any manual status selection on first submit
		# Check if this is a new document being submitted (first time)
		if self.docstatus == 1 and self.is_new():
			correct_status = self.determine_correct_status()
			self.status = correct_status
	
	def determine_correct_status(self):
		"""
		Determine the correct status based on document conditions.
		This function ensures status is set correctly regardless of manual selection.
		Renewal In Progress is only set via the action button, not automatically.
		
		Returns:
			str: Correct status based on expiry date and renewal conditions
		"""
		# For non-expiry based documents, always set to Active
		if not self.is_expiry_based or not self.expiry_date:
			return "Active"
		
		expiry_date = getdate(self.expiry_date)
		today_date = getdate(today())
		
		# Check if expired
		if expiry_date < today_date:
			return "Expired"
		
		# Check if expiring soon (within renewal lead time)
		# Set to "Active Soon to Expire" instead of "Renewal In Progress"
		if self.remind_from_date:
			remind_date = getdate(self.remind_from_date)
			if today_date >= remind_date:
				return "Active Soon to Expire"
		
		# Default to Active for valid, non-expiring documents
		return "Active"

	def on_submit(self):
		"""Handle post-submit actions"""
		# Status is already set in validate() before submit
		# If this doc is a renewal of another, archive the previous one now
		if self.replaces_document:
			old_doc = frappe.get_doc("Document Tracker List", self.replaces_document)
			old_doc.flags.ignore_validate_update_after_submit = True
			old_doc.lifecycle_state = "Historical"
			old_doc.status = "Renewed"
			old_doc.renewed_by_document = self.name
			old_doc.renewal_count = (old_doc.renewal_count or 0) + 1
			old_doc.save(ignore_permissions=True)

	def compute_remind_from_date(self):
		"""Compute remind_from_date based on renewal_lead_time_type and expiry_date"""
		if not self.is_expiry_based or not self.expiry_date:
			self.remind_from_date = None
			return

		if not self.is_renewable:
			self.remind_from_date = None
			return

		expiry_date = getdate(self.expiry_date)

		if self.renewal_lead_time_type == "Custom":
			if self.custom_remind_from_date:
				self.remind_from_date = self.custom_remind_from_date
			else:
				self.remind_from_date = None
		elif self.renewal_lead_time_type == "1D":
			self.renewal_lead_time_days = 1
			self.remind_from_date = add_days(expiry_date, -1)
		elif self.renewal_lead_time_type == "1W":
			self.renewal_lead_time_days = 7
			self.remind_from_date = add_days(expiry_date, -7)
		elif self.renewal_lead_time_type == "1M":
			self.renewal_lead_time_days = 30
			self.remind_from_date = add_days(expiry_date, -30)
		elif self.renewal_lead_time_type == "3M":
			self.renewal_lead_time_days = 90
			self.remind_from_date = add_days(expiry_date, -90)
		else:
			self.remind_from_date = None

	def validate_current_document_uniqueness(self):
		"""Ensure only one Current doc per (document_name, document_category, company)."""
		if self.lifecycle_state != "Current":
			return

		# allow drafts that are renewals; uniqueness will be enforced on submit when old doc is archived
		if self.docstatus == 0 and self.replaces_document:
			return

		# allow amended documents (they reference the original via amended_from)
		if self.amended_from:
			return

		if not self.company or not self.document_name or not self.document_category:
			return

		# Build filters excluding cancelled documents and amended documents
		# Use get_all to properly filter out null amended_from and cancelled docs
		existing_docs = frappe.get_all(
			"Document Tracker List",
			filters={
				"company": self.company,
				"document_name": self.document_name,
				"document_category": self.document_category,
				"lifecycle_state": "Current",
				"name": ["!=", self.name],
				"docstatus": ["!=", 2],  # exclude cancelled documents
				"status": ["!=", "Cancelled"],  # exclude cancelled status
			},
			fields=["name", "amended_from"],
		)

		# Filter out amended documents (those with amended_from set)
		existing_current = None
		for doc in existing_docs:
			if not doc.amended_from:  # only consider non-amended documents
				existing_current = doc.name
				break

		if existing_current:
			# if the only existing current is the one we're replacing, allow submit; it will be archived in on_submit
			if self.docstatus == 1 and self.replaces_document and existing_current == self.replaces_document:
				return
			frappe.throw(
				_(
					"Only one Current document is allowed per Document Name, Category, and Company. "
					"Document {0} is already marked as Current."
				).format(existing_current),
				frappe.ValidationError,
			)

	def get_root_document(self):
		"""Get the root document in the renewal chain"""
		current = self
		visited = set()

		while current.replaces_document and current.replaces_document not in visited:
			visited.add(current.name)
			try:
				current = frappe.get_doc("Document Tracker List", current.replaces_document)
			except frappe.DoesNotExistError:
				break

		return current

	def get_chain_documents(self, root_name):
		"""Get all document names in the renewal chain starting from root"""
		chain = [root_name]
		current_name = root_name

		while True:
			renewed_by = frappe.db.get_value(
				"Document Tracker List",
				{"replaces_document": current_name},
				"name"
			)
			if not renewed_by:
				break
			chain.append(renewed_by)
			current_name = renewed_by

		return chain

	def compute_validity_fields(self):
		"""Compute validity_remaining_days, flag_expiring_soon, flag_overdue"""
		if not self.is_expiry_based or not self.expiry_date:
			self.validity_remaining_days = None
			self.flag_expiring_soon = 0
			self.flag_overdue = 0
			return

		expiry_date = getdate(self.expiry_date)
		today_date = getdate(today())
		remaining_days = date_diff(expiry_date, today_date)

		self.validity_remaining_days = remaining_days

		# Flag expiring soon if within renewal lead time
		if self.remind_from_date:
			remind_date = getdate(self.remind_from_date)
			self.flag_expiring_soon = 1 if today_date >= remind_date else 0
		else:
			self.flag_expiring_soon = 0

		# Flag overdue if past expiry date
		self.flag_overdue = 1 if remaining_days < 0 else 0

	@frappe.whitelist()
	def renew(self):
		"""Create a new document renewal draft without altering current doc yet"""
		if not self.is_renewable:
			frappe.throw(_("This document is not renewable."))

		if self.lifecycle_state != "Current":
			frappe.throw(_("Only Current documents can be renewed."))

		# Create new document as draft, link back via replaces_document
		new_doc = frappe.new_doc("Document Tracker List")
		new_doc.update({
			"document_name": self.document_name,
			"document_reference_no": self.document_reference_no,
			"document_category": self.document_category,
			"authority": self.authority,
			"company": self.company,
			"business_unit": self.business_unit,
			"department": self.department,
			"owner_person": self.owner_person,
			"counterparty_type": self.counterparty_type,
			"counterparty": self.counterparty,
			"issue_date": today(),  # new issue date at renewal
			"is_expiry_based": self.is_expiry_based,
			"expiry_date": self.expiry_date,  # copy expiry date if expiry-based
			"is_renewable": self.is_renewable,
			"renewal_lead_time_type": self.renewal_lead_time_type,
			"custom_remind_from_date": self.custom_remind_from_date,
			"lifecycle_state": "Current",
			"replaces_document": self.name,
			"renewal_count": 0,
			"status": "Draft"
		})

		# Copy attachments if needed
		if self.primary_document:
			new_doc.primary_document = self.primary_document

		if self.supplementary_documents:
			for att in self.supplementary_documents:
				new_doc.append("supplementary_documents", {
					"attachment_type": att.attachment_type,
					"file": att.file,
					"description": att.description
				})

		new_doc.insert()

		# Link back from old document
		self.renewed_by_document = new_doc.name
		self.save(ignore_permissions=True)

		# Return the new document name for navigation
		# Don't show msgprint here as it interferes with navigation
		return new_doc.name

	@frappe.whitelist()
	def mark_renewal_in_progress(self):
		"""Mark document status as Renewal In Progress - only set via this action"""
		if self.status not in ["Active", "Active Soon to Expire", "Draft"]:
			frappe.throw(_("Document must be Active, Active Soon to Expire, or Draft to mark as Renewal In Progress."))
		
		self.status = "Renewal In Progress"
		self.save()
		frappe.msgprint(_("Document marked as Renewal In Progress."))

	@frappe.whitelist()
	def revert_renewal_status(self):
		"""Revert Renewal In Progress status back to correct status based on document conditions"""
		if self.status != "Renewal In Progress":
			frappe.throw(_("Document status must be Renewal In Progress to revert."))
		
		correct_status = self.determine_correct_status()
		self.status = correct_status
		self.save()
		frappe.msgprint(_("Document status reverted to {0}.").format(correct_status))

	@frappe.whitelist()
	def revoke_or_cancel(self):
		"""Revoke or cancel the document"""
		if self.status in ["Revoked", "Cancelled", "Renewed"]:
			frappe.throw(_("Document is already {0}.").format(self.status))

		# Determine action based on current status
		if self.status == "Active":
			# Revoke: Just change status, don't cancel document
			self.status = "Revoked"
			self.lifecycle_state = "Historical"
			self.save()
			frappe.msgprint(_("Document status updated to {0}.").format(self.status))
		else:
			# Cancel: Only DocPulse Master Manager can cancel documents
			user_roles = frappe.get_roles()
			if "DocPulse Master Manager" not in user_roles and "System Manager" not in user_roles:
				frappe.throw(_("Only DocPulse Master Manager can cancel tracker list entries."))
			
			# Check if document is submitted before canceling
			if self.docstatus != 1:
				frappe.throw(_("Only submitted documents can be cancelled."))
			
			# Set status and lifecycle state before canceling
			self.status = "Cancelled"
			if self.lifecycle_state == "Current":
				self.lifecycle_state = "Historical"
			
			# Save status changes first
			self.save()
			
			# Cancel the document (sets docstatus to 2)
			self.cancel()
			frappe.msgprint(_("Document cancelled and status updated to {0}.").format(self.status))

	def validate_update_after_submit(self):
		"""Allow only specific fields to change after submit; block others."""
		if self.docstatus != 1:
			return

		allowed = {
			"status",
			"lifecycle_state",
			"remind_from_date",
			"flag_expiring_soon",
			"flag_overdue",
			"renewal_count",
			"renewed_by_document",
		}

		meta_fields = {"modified", "modified_by", "_user_tags", "_assign", "_comments", "_liked_by"}

		dirty = set()
		try:
			before = self.get_doc_before_save()
		except Exception:
			before = None

		if before:
			current = self.as_dict()
			for field, value in current.items():
				if before.get(field) != value:
					dirty.add(field)

		# ignore meta/system fields
		dirty = dirty - meta_fields

		disallowed = [f for f in dirty if f not in allowed]

		if disallowed:
			frappe.throw(
				_("Not allowed to change fields after submission: {0}").format(", ".join(disallowed)),
				frappe.ValidationError,
			)


def _resolve_docname(value: str | dict | None) -> str:
	"""Extract a docname from assorted inputs (name, JSON string, or dict)."""
	if isinstance(value, dict):
		return value.get("name") or value.get("docname") or value.get("doc")

	if isinstance(value, str):
		trimmed = value.strip()
		# If the string looks like JSON, try to parse it and get name
		if trimmed.startswith("{") or trimmed.startswith("["):
			try:
				parsed = frappe.parse_json(trimmed)
				if isinstance(parsed, dict):
					return parsed.get("name") or parsed.get("docname") or parsed.get("doc")
			except Exception:
				pass
		return value  # assume it's already a docname

	return None


def _get_docname_from_inputs(doc: str | dict | None = None) -> str:
	candidates = [
		doc,
		frappe.form_dict.get("doc"),
		frappe.form_dict.get("name"),
		frappe.form_dict.get("docname"),
	]
	for candidate in candidates:
		docname = _resolve_docname(candidate)
		if docname:
			return docname
	frappe.throw(_("Document name is required"), frappe.ValidationError)


@frappe.whitelist()
def renew(doc: str | dict | None = None):
	"""Server action wrapper to renew a document by name or JSON payload."""
	docname = _get_docname_from_inputs(doc)
	doc_obj = frappe.get_doc("Document Tracker List", docname)
	return doc_obj.renew()


@frappe.whitelist()
def mark_renewal_in_progress(doc: str | dict | None = None):
	"""Server action wrapper to mark renewal in progress by name or JSON payload."""
	docname = _get_docname_from_inputs(doc)
	doc_obj = frappe.get_doc("Document Tracker List", docname)
	return doc_obj.mark_renewal_in_progress()


@frappe.whitelist()
def revert_renewal_status(doc: str | dict | None = None):
	"""Server action wrapper to revert renewal status by name or JSON payload."""
	docname = _get_docname_from_inputs(doc)
	doc_obj = frappe.get_doc("Document Tracker List", docname)
	return doc_obj.revert_renewal_status()


@frappe.whitelist()
def revoke_or_cancel(doc: str | dict | None = None):
	"""Server action wrapper to revoke or cancel by name or JSON payload."""
	docname = _get_docname_from_inputs(doc)
	doc_obj = frappe.get_doc("Document Tracker List", docname)
	return doc_obj.revoke_or_cancel()


@frappe.whitelist()
def update_lifecycle_state(doc: str | dict | None = None, lifecycle_state: str | None = None):
	"""Allow controlled lifecycle_state change after submit via server-side action.

	- Uses ignore_validate_update_after_submit to bypass the standard restriction.
	- Still validates required inputs and persists via doc.save to run hooks.
	"""
	if not lifecycle_state:
		frappe.throw(_("Lifecycle State is required"), frappe.ValidationError)

	docname = _get_docname_from_inputs(doc)
	doc_obj = frappe.get_doc("Document Tracker List", docname)

	# allow update after submit while keeping validations/hook runs
	doc_obj.flags.ignore_validate_update_after_submit = True
	doc_obj.lifecycle_state = lifecycle_state
	doc_obj.save(ignore_permissions=True)

	return doc_obj.name


@frappe.whitelist()
def update_status(doc: str | dict | None = None, status: str | None = None):
	"""Allow controlled status change after submit via server-side action."""
	if not status:
		frappe.throw(_("Status is required"), frappe.ValidationError)

	docname = _get_docname_from_inputs(doc)
	doc_obj = frappe.get_doc("Document Tracker List", docname)

	# allow update after submit while keeping validations/hook runs
	doc_obj.flags.ignore_validate_update_after_submit = True
	doc_obj.status = status
	doc_obj.save(ignore_permissions=True)

	return doc_obj.name
