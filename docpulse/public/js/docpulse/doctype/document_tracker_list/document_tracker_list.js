// Copyright (c) 2025, DocPulse and contributors
// For license information, please see license.txt

frappe.ui.form.on("Document Tracker List", {
	refresh: function(frm) {
		// Show/hide buttons based on status and lifecycle state
		if (frm.doc.status === "Active" && frm.doc.lifecycle_state === "Current" && frm.doc.is_renewable) {
			frm.add_custom_button(__("Renew"), function() {
				frm.call({
					method: "renew",
					callback: function(r) {
						if (r && r.message && !r.exc) {
							// Show success message and navigate to the new draft document
							frappe.show_alert({
								message: __("Renewal draft created. Opening new document..."),
								indicator: "green"
							}, 3);
							// Navigate to the new draft document
							setTimeout(function() {
								frappe.set_route("Form", "Document Tracker List", r.message);
							}, 500);
						}
					}
				});
			}, __("Actions"));
		}

		if (frm.doc.status === "Active" || frm.doc.status === "Active Soon to Expire" || frm.doc.status === "Draft") {
			frm.add_custom_button(__("Mark Renewal In Progress"), function() {
				frm.call({
					method: "mark_renewal_in_progress",
					callback: function(r) {
						if (r && !r.exc) {
							frm.reload_doc();
						}
					}
				});
			}, __("Actions"));
		}

		if (frm.doc.status === "Renewal In Progress") {
			frm.add_custom_button(__("Revert Renewal Status"), function() {
				frm.call({
					method: "revert_renewal_status",
					callback: function(r) {
						if (r && !r.exc) {
							frm.reload_doc();
						}
					}
				});
			}, __("Actions"));
		}

		if (frm.doc.status !== "Revoked" && frm.doc.status !== "Cancelled" && frm.doc.status !== "Renewed") {
			frm.add_custom_button(__("Revoke/Cancel"), function() {
				// Determine action text and title
				const actionText = frm.doc.status === "Active" ? __("revoke") : __("cancel");
				const actionTitle = frm.doc.status === "Active" ? __("Revoke Document") : __("Cancel Document");
				
				// Show red warning confirmation dialog
				frappe.warn(
					actionTitle,
					__("Are you sure you want to {0} this document? This action cannot be undone.", actionText),
					function() {
						// User confirmed - proceed with action
						frm.call({
							method: "revoke_or_cancel",
							callback: function(r) {
								if (r && !r.exc) {
									// Reload to hide action buttons after status change
									frm.reload_doc();
								}
							}
						});
					},
					__("Confirm")
				);
			}, __("Actions"));
		}
	},

	renewal_lead_time_type: function(frm) {
		// Auto-calculate renewal_lead_time_days when type changes
		if (frm.doc.renewal_lead_time_type && frm.doc.renewal_lead_time_type !== "Custom") {
			let days = 0;
			if (frm.doc.renewal_lead_time_type === "1D") days = 1;
			else if (frm.doc.renewal_lead_time_type === "1W") days = 7;
			else if (frm.doc.renewal_lead_time_type === "1M") days = 30;
			else if (frm.doc.renewal_lead_time_type === "3M") days = 90;
			
			frm.set_value("renewal_lead_time_days", days);
		}
	}
});
