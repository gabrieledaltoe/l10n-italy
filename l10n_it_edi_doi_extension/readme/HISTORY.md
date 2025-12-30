# 18.0.1.2.0 (2025-12-30)

- [ADD] Multi-supplier support for DOI type "in" (issued declarations)
  - Partner is now optional for DOI type "in" - a single DOI can be used with any supplier
  - Override of `_get_validity_errors` to skip partner validation for type "in"
  - Override of `_fetch_valid_declaration_of_intent` to not filter by partner for type "in"
  - Constraint to require partner only for DOI type "out" (received declarations)
- [ADD] Protocol number field for DOI search
  - Added `_rec_name = "protocol_number"` to fix search warnings
  - Computed field used for `name_search` functionality (display_name unchanged)
- [IMP] View improvements for DOI type "in"
  - Domain filters on invoice/PO forms show all DOI "in" without partner restriction
  - New list view for purchase invoices with "Supplier" column instead of "Customer"
  - Override of `action_open_invoice_ids` to use correct view based on DOI type

# 18.0.1.1.0 (2025-12-28)

- [ADD] Automatic creation of purchase DOI tax during module installation
  - New tax `00dia` (0% E Acq) for purchase invoices with DOI
  - Fiscal position mappings for all Italian purchase taxes (22%, 10%, 5%, 4%)
  - Automatic company configuration with the new purchase tax
- [ADD] Threshold warning for purchase invoices
  - Extended `_compute_l10n_it_edi_doi_warning` to show warnings on vendor bills
  - Consistent behavior with sales invoices from base module

# 18.0.1.0.0

- Start of the history.
