# Copyright (c) 2025, DocPulse and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.core.doctype.scheduled_job_type.scheduled_job_type import insert_single_event


def sync_renewal_log_scheduler():
	"""Sync scheduled job from DocPulse Settings"""
	try:
		settings = frappe.get_single("DocPulse Settings")
		if settings.cron_schedule:
			method = "docpulse.docpulse.scheduler.daily_renewal_log.create_daily_renewal_logs"
			
			# Use insert_single_event to create/update
			insert_single_event(
				frequency="Cron",
				event=method,
				cron_format=settings.cron_schedule
			)
			
			# Ensure the job is updated and not stopped
			job_name = frappe.db.exists("Scheduled Job Type", {"method": method})
			if job_name:
				job = frappe.get_doc("Scheduled Job Type", job_name)
				# Force update cron_format and ensure it's not stopped
				if job.cron_format != settings.cron_schedule:
					job.cron_format = settings.cron_schedule
				if job.stopped:
					job.stopped = 0
				job.save(ignore_permissions=True)
				frappe.db.commit()
				
				frappe.logger().info(
					f"Synced Scheduled Job Type '{job_name}' with cron: {settings.cron_schedule}"
				)
	except Exception as e:
		frappe.log_error(
			title=_("Error syncing renewal log scheduler"),
			message=str(e)
		)


class DocPulseSettings(Document):
	def on_update(self):
		"""Update scheduled job when cron settings change"""
		if self.cron_schedule:
			try:
				# Create or update Scheduled Job Type with dynamic cron
				method = "docpulse.docpulse.scheduler.daily_renewal_log.create_daily_renewal_logs"
				
				# Use insert_single_event to create/update
				insert_single_event(
					frequency="Cron",
					event=method,
					cron_format=self.cron_schedule
				)
				
				# Ensure the job is updated and not stopped
				job_name = frappe.db.exists("Scheduled Job Type", {"method": method})
				if job_name:
					job = frappe.get_doc("Scheduled Job Type", job_name)
					# Force update cron_format and ensure it's not stopped
					if job.cron_format != self.cron_schedule:
						job.cron_format = self.cron_schedule
					if job.stopped:
						job.stopped = 0
					job.save(ignore_permissions=True)
					frappe.db.commit()
					
					frappe.logger().info(
						f"Updated Scheduled Job Type '{job_name}' with cron: {self.cron_schedule}"
					)
				
				frappe.msgprint(_("Scheduled job updated successfully."))
			except Exception as e:
				frappe.log_error(
					title=_("Error updating scheduled job"),
					message=str(e)
				)
				frappe.throw(_("Failed to update scheduled job: {0}").format(str(e)))
