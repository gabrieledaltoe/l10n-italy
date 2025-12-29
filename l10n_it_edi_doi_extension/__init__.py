from . import models


def _add_fiscal_position_mappings(env, company):
    """Add purchase tax mappings to the Declaration of Intent fiscal position."""
    fiscal_position = company.l10n_it_edi_doi_fiscal_position_id
    if not fiscal_position:
        return

    # Get the purchase DOI tax
    doi_tax = company.l10n_it_edi_doi_bill_tax_id
    if not doi_tax:
        return

    # Purchase tax codes to map (goods and services)
    purchase_tax_codes = ["22am", "10am", "5am", "4am", "22as", "10as", "5as", "4as"]

    for tax_code in purchase_tax_codes:
        # Find the source tax by its template reference
        source_tax = env["account.tax"].search(
            [
                ("company_id", "=", company.id),
                ("type_tax_use", "=", "purchase"),
                ("amount", "=", float(tax_code[:2]) if tax_code[:2].isdigit() else 0),
            ],
            limit=1,
        )
        if source_tax:
            # Check if mapping already exists
            existing_mapping = env["account.fiscal.position.tax"].search(
                [
                    ("position_id", "=", fiscal_position.id),
                    ("tax_src_id", "=", source_tax.id),
                ]
            )
            if not existing_mapping:
                env["account.fiscal.position.tax"].create(
                    {
                        "position_id": fiscal_position.id,
                        "tax_src_id": source_tax.id,
                        "tax_dest_id": doi_tax.id,
                    }
                )


def _l10n_it_edi_doi_extension_post_init(env):
    """Create purchase DOI tax and fiscal position mappings for Italian companies."""
    for company in env["res.company"].search(
        [("chart_template", "=", "it"), ("parent_id", "=", False)]
    ):
        # Check if tax already exists for this company
        existing_tax = env["account.tax"].search(
            [
                ("company_id", "=", company.id),
                ("name", "=", "0% E Acq"),
                ("type_tax_use", "=", "purchase"),
            ],
            limit=1,
        )
        if existing_tax:
            # Tax already exists, just update company configuration if needed
            if not company.l10n_it_edi_doi_bill_tax_id:
                company.l10n_it_edi_doi_bill_tax_id = existing_tax
        else:
            # Create tax using chart template
            chart_template = env["account.chart.template"].with_company(company)
            chart_template._load_data(
                {
                    "account.tax": chart_template._get_it_edi_doi_extension_account_tax(),
                    "res.company": chart_template._get_it_edi_doi_extension_res_company(),
                }
            )
        # Add fiscal position mappings for purchase taxes
        _add_fiscal_position_mappings(env, company)
