// Copyright (c) 2025, DocPulse and contributors
// For license information, please see license.txt

frappe.listview_settings["Document Tracker List"] = {
	get_indicator: function (doc) {
		const status_colors = {
			"Draft": "gray",
			"Active": "green",
			"Active Soon to Expire": "yellow",
			"Renewal In Progress": "orange",
			"Expired": "red",
			"Renewed": "gray",
			"Revoked": "red",
			"Cancelled": "red",
		};
		
		// Show custom status if document is submitted and has status field
		if (doc.docstatus === 1) {
			if (doc.status && status_colors[doc.status]) {
				// Document is submitted and has a valid status, show custom status
				const color = status_colors[doc.status];
				return [__(doc.status), color, "status,=," + doc.status];
			}
			// Document is submitted but status not available, show submitted
			return [__("Submitted"), "blue"];
		} else if (doc.docstatus === 0) {
			// Document is draft
			return [__("Draft"), "gray"];
		} else if (doc.docstatus === 2) {
			// Document is cancelled
			return [__("Cancelled"), "red"];
		}
		
		// Fallback to submitted state
		return [__("Submitted"), "blue"];
	},
};
