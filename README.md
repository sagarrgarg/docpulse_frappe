# DocPulse

**Document Lifecycle Manager** – Track, manage, and automate document renewals with intelligent alerts and comprehensive lifecycle management.

## Features

- **Document Tracking**: Track documents with expiry dates, renewal dates, and lifecycle states
- **Automated Renewal Alerts**: Daily scheduler generates renewal logs for documents requiring attention
- **Lifecycle Management**: Current/Historical state tracking with document renewal chains
- **Status Tracking**: Draft, Active, Active Soon to Expire, Renewal In Progress, Expired, Renewed, Revoked, Cancelled
- **Dashboard & Analytics**: Visual charts and number cards for document status overview
- **Role-Based Access**: DocPulse Master Manager and DocPulse Manager roles with granular permissions
- **Notifications**: Real-time alerts and ToDo creation for document owners

## Installation

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch develop
bench install-app docpulse
```

## Quick Start

1. **Setup Masters**: Create Document Categories and Document Authorities
2. **Configure Settings**: Set up scheduler cron schedule in DocPulse Settings
3. **Create Documents**: Add documents in Document Tracker List with expiry dates
4. **Monitor Renewals**: Check Document Tracker Renewal Log for daily renewal alerts

## Roles & Permissions

- **DocPulse Master Manager**: Full access including cancel permissions
- **DocPulse Manager**: Full access except cancel; read-only access to masters and settings

## Core Doctypes

- **Document Tracker List**: Main document tracking doctype
- **Document Tracker Renewal Log**: Automated renewal logs (system-generated)
- **Document Category**: Document categorization master
- **Document Authority**: Issuing authority master
- **DocPulse Settings**: Scheduler configuration

## Contributing

This app uses `pre-commit` for code formatting and linting:

```bash
cd apps/docpulse
pre-commit install
```

Tools used: `ruff`, `eslint`, `prettier`, `pyupgrade`

## License

MIT
