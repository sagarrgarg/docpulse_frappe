# Copyright (c) 2025, DocPulse and contributors
# For license information, please see license.txt

"""
Utility script to check the status of the Document Tracker Renewal Log scheduler.
Run this from bench console: bench --site <site> console
Then execute: exec(open('apps/docpulse/docpulse/docpulse/utils/check_scheduler_status.py').read())
"""

import frappe
from frappe.utils import now_datetime, get_datetime

def check_renewal_log_scheduler_status():
	"""Check the status of the renewal log scheduler job"""
	method = "docpulse.docpulse.scheduler.daily_renewal_log.create_daily_renewal_logs"
	
	# Get the scheduled job
	job = frappe.db.get_value(
		"Scheduled Job Type",
		{"method": method},
		["name", "last_execution", "stopped", "create_log", "cron_format", "frequency"],
		as_dict=True
	)
	
	if not job:
		print("❌ Scheduled Job NOT FOUND!")
		print(f"   Method: {method}")
		print("\n   Action: Update DocPulse Settings to create the job.")
		return
	
	print("=" * 70)
	print("📋 SCHEDULED JOB STATUS")
	print("=" * 70)
	print(f"Job Name: {job.name}")
	print(f"Method: {method}")
	print(f"Frequency: {job.frequency}")
	print(f"Cron Format: {job.cron_format}")
	print(f"Stopped: {'Yes ❌' if job.stopped else 'No ✅'}")
	print(f"Create Log: {'Yes ✅' if job.create_log else 'No'}")
	
	if job.last_execution:
		last_exec = get_datetime(job.last_execution)
		now = now_datetime()
		time_diff = (now - last_exec).total_seconds()
		print(f"\nLast Execution: {last_exec}")
		print(f"Time Since Last Run: {time_diff:.0f} seconds ({time_diff/60:.1f} minutes)")
	else:
		print("\nLast Execution: Never")
	
	# Get recent logs
	logs = frappe.get_all(
		"Scheduled Job Log",
		filters={"scheduled_job_type": job.name},
		fields=["name", "status", "creation", "modified"],
		order_by="creation desc",
		limit=10
	)
	
	print(f"\n📊 Recent Execution Logs (Last 10):")
	print("-" * 70)
	if logs:
		for log in logs:
			status_icon = {
				"Complete": "✅",
				"Failed": "❌",
				"Scheduled": "⏳"
			}.get(log.status, "❓")
			print(f"{status_icon} {log.status:12} | Created: {log.creation} | Modified: {log.modified}")
	else:
		print("   No logs found (create_log might be disabled)")
	
	# Check scheduler process
	print("\n" + "=" * 70)
	print("⚙️  SCHEDULER PROCESS STATUS")
	print("=" * 70)
	try:
		from frappe.utils.scheduler import is_scheduler_inactive
		if is_scheduler_inactive():
			print("❌ Scheduler is INACTIVE")
			print("   Run: bench --site <site> enable-scheduler")
		else:
			print("✅ Scheduler is ACTIVE")
	except:
		print("⚠️  Could not check scheduler process status")
	
	print("\n" + "=" * 70)
	print("💡 TIPS")
	print("=" * 70)
	print("1. Check Error Log (Error Log doctype) for any failures")
	print("2. Check scheduler logs: tail -f logs/scheduler.log")
	print("3. Manually trigger: bench --site <site> console")
	print("   Then: frappe.get_doc('Scheduled Job Type', '{}').execute()".format(job.name))
	print("=" * 70)

# Auto-run if executed directly
if __name__ == "__main__" or frappe.local.site:
	check_renewal_log_scheduler_status()

