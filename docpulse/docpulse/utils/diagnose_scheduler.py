# Copyright (c) 2025, DocPulse and contributors
# For license information, please see license.txt

"""
Diagnostic script to troubleshoot why the renewal log scheduler is not running.
Run this from bench console: bench --site <site> console
Then execute: exec(open('apps/docpulse/docpulse/docpulse/utils/diagnose_scheduler.py').read())
"""

import frappe
from frappe.utils import now_datetime, get_datetime
from frappe.utils.scheduler import is_scheduler_disabled, is_scheduler_inactive

def diagnose_scheduler():
	"""Comprehensive diagnostic for scheduler issues"""
	method = "docpulse.docpulse.scheduler.daily_renewal_log.create_daily_renewal_logs"
	
	print("=" * 70)
	print("🔍 SCHEDULER DIAGNOSTIC REPORT")
	print("=" * 70)
	
	# 1. Check scheduler enabled status
	print("\n1️⃣  SCHEDULER STATUS")
	print("-" * 70)
	
	if frappe.conf.disable_scheduler:
		print("❌ Scheduler DISABLED in frappe.conf (disable_scheduler=True)")
	else:
		print("✅ frappe.conf.disable_scheduler: Not set")
	
	enable_scheduler = frappe.db.get_single_value("System Settings", "enable_scheduler")
	if not enable_scheduler:
		print("❌ Scheduler DISABLED in System Settings")
		print("   Fix: bench --site <site> scheduler enable")
	else:
		print("✅ System Settings.enable_scheduler: Enabled")
	
	if frappe.conf.pause_scheduler:
		print("❌ Scheduler PAUSED in site config")
		print("   Fix: bench --site <site> scheduler resume")
	else:
		print("✅ Scheduler not paused")
	
	if is_scheduler_disabled(verbose=False):
		print("❌ Scheduler is DISABLED")
	else:
		print("✅ Scheduler is ENABLED")
	
	if is_scheduler_inactive():
		print("❌ Scheduler process is INACTIVE")
		print("   Fix: Ensure bench schedule is running")
	else:
		print("✅ Scheduler process is ACTIVE")
	
	# 2. Check if job exists
	print("\n2️⃣  SCHEDULED JOB STATUS")
	print("-" * 70)
	
	job = frappe.db.get_value(
		"Scheduled Job Type",
		{"method": method},
		["name", "last_execution", "stopped", "create_log", "cron_format", "frequency"],
		as_dict=True
	)
	
	if not job:
		print("❌ Scheduled Job NOT FOUND!")
		print(f"   Method: {method}")
		print("\n   🔧 FIX: Update DocPulse Settings to create the job")
		print("   Steps:")
		print("   1. Go to DocPulse Settings")
		print("   2. Set Cron Schedule (e.g., '* * * * *' for every minute)")
		print("   3. Save the document")
		
		# Check if settings exist
		try:
			settings = frappe.get_single("DocPulse Settings")
			if settings.cron_schedule:
				print(f"\n   ⚠️  Settings has cron_schedule: {settings.cron_schedule}")
				print("   But job doesn't exist. Try manually syncing:")
				print("   from docpulse.docpulse.doctype.docpulse_settings.docpulse_settings import sync_renewal_log_scheduler")
				print("   sync_renewal_log_scheduler()")
			else:
				print("\n   ⚠️  DocPulse Settings cron_schedule is NOT SET")
		except:
			print("\n   ⚠️  Could not check DocPulse Settings")
		
		return
	
	print(f"✅ Job found: {job.name}")
	print(f"   Frequency: {job.frequency}")
	print(f"   Cron Format: {job.cron_format}")
	
	if job.stopped:
		print("❌ Job is STOPPED")
		print("   Fix: Uncheck 'Stopped' in Scheduled Job Type")
	else:
		print("✅ Job is NOT stopped")
	
	if job.create_log:
		print("✅ Logging enabled")
	else:
		print("⚠️  Logging disabled (but should auto-enable for Cron)")
	
	if job.last_execution:
		last_exec = get_datetime(job.last_execution)
		now = now_datetime()
		time_diff = (now - last_exec).total_seconds()
		print(f"\n   Last Execution: {last_exec}")
		print(f"   Time Since Last Run: {time_diff:.0f} seconds ({time_diff/60:.1f} minutes)")
		
		# Check if it's been too long
		if time_diff > 120:  # More than 2 minutes for a 1-minute cron
			print("   ⚠️  Job hasn't run recently!")
	else:
		print("\n   Last Execution: Never")
		print("   ⚠️  Job has never executed")
	
	# 3. Check recent logs
	print("\n3️⃣  EXECUTION LOGS")
	print("-" * 70)
	
	logs = frappe.get_all(
		"Scheduled Job Log",
		filters={"scheduled_job_type": job.name},
		fields=["name", "status", "creation", "modified", "details"],
		order_by="creation desc",
		limit=10
	)
	
	if logs:
		print(f"Found {len(logs)} recent log entries:")
		for log in logs:
			status_icon = {
				"Complete": "✅",
				"Failed": "❌",
				"Scheduled": "⏳"
			}.get(log.status, "❓")
			print(f"   {status_icon} {log.status:12} | {log.creation}")
			if log.status == "Failed" and log.details:
				print(f"      Error: {log.details[:200]}...")
	else:
		print("   ⚠️  No logs found")
		if not job.create_log:
			print("   (Logging is disabled for this job)")
	
	# 4. Check error logs
	print("\n4️⃣  ERROR LOGS")
	print("-" * 70)
	
	error_logs = frappe.get_all(
		"Error Log",
		filters={
			"error": ["like", "%Renewal Log%"]
		},
		fields=["name", "error", "creation"],
		order_by="creation desc",
		limit=5
	)
	
	if error_logs:
		print(f"Found {len(error_logs)} related error logs:")
		for err in error_logs:
			print(f"   ❌ {err.creation}: {err.error[:100]}...")
	else:
		print("   ✅ No related errors found")
	
	# 5. Check scheduler process
	print("\n5️⃣  SCHEDULER PROCESS")
	print("-" * 70)
	
	try:
		import subprocess
		result = subprocess.run(
			["pgrep", "-f", "bench.*schedule"],
			capture_output=True,
			text=True
		)
		if result.returncode == 0:
			pids = result.stdout.strip().split('\n')
			print(f"✅ Scheduler process running (PIDs: {', '.join(pids)})")
		else:
			print("❌ Scheduler process NOT RUNNING")
			print("   Fix: bench --site <site> schedule")
	except:
		print("⚠️  Could not check scheduler process (pgrep not available)")
	
	# 6. Recommendations
	print("\n" + "=" * 70)
	print("💡 RECOMMENDATIONS")
	print("=" * 70)
	
	issues = []
	if not job:
		issues.append("Job doesn't exist - Update DocPulse Settings")
	if job and job.stopped:
		issues.append("Job is stopped - Uncheck 'Stopped' in Scheduled Job Type")
	if is_scheduler_disabled(verbose=False):
		issues.append("Scheduler is disabled - Run: bench --site <site> scheduler enable")
	if frappe.conf.pause_scheduler:
		issues.append("Scheduler is paused - Run: bench --site <site> scheduler resume")
	
	if not issues:
		print("✅ All checks passed!")
		print("\n   If job still not running:")
		print("   1. Ensure 'bench schedule' is running")
		print("   2. Check scheduler.log: tail -f logs/scheduler.log")
		print("   3. Manually test: frappe.get_doc('Scheduled Job Type', '{}').execute()".format(job.name))
	else:
		for i, issue in enumerate(issues, 1):
			print(f"   {i}. {issue}")
	
	print("=" * 70)

# Auto-run if executed directly
if __name__ == "__main__" or frappe.local.site:
	diagnose_scheduler()

