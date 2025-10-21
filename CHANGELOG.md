# Changelog

All notable changes in this repository will be documented in this file.

## 2025-10-21 - github-actions (unreleased)

### Added
- Tests: Added and improved `GoogleSheetsService` tests to cover authentication errors, invalid data handling, and worksheet update behavior.

### Fixed
- Google Sheets service: validate `VOs_complete_list` and distinguish between `None` (error) and empty list (no VOs). Use `'-'` placeholders for missing values and handle `ValueError` through `handle_exception` to avoid breaking integration flows.
- Improved error handling in `update_GWorkSheet` to better log and recover from invalid summaries.

### Notes
- All tests pass locally: `22 passed`.
- The branch `github-actions` has been pushed to your fork remote (`fork`).
