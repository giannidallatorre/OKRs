# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

- Add package source files for `pyOKR_VOs_CPUs_Accounting` (controllers, services, utils).
- Add unit and integration tests covering controller, services and utils.
- Add Apache-2.0 license file for the package.
- Security: stop tracking `pyOKR_VOs_CPUs_Accounting/.config/service_account.json` and
  document how to create and keep the service account file locally.

Notes
- A local service account file `.config/service_account.json` was detected in your
  working copy and contains a private key. This file must remain local and must
  not be committed. The repository includes a template: `.config/service_account.json.template`.
