from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class L10nItDeclarationOfIntent(models.Model):
    _inherit = "l10n_it_edi_doi.declaration_of_intent"

    # Fix: define _rec_name with a computed field to avoid warning:
    # "Cannot search on display_name, no _rec_name or _rec_names_search defined"
    _rec_name = "protocol_number"

    protocol_number = fields.Char(
        string="Protocol Number",
        compute="_compute_protocol_number",
        store=True,
    )

    @api.depends("protocol_number_part1", "protocol_number_part2")
    def _compute_protocol_number(self):
        """Compute short protocol number for display.

        Format: first 5 chars of part1 + ... + last 3 chars of part2
        Example: "08011...001" from "08011234567" and "000001"
        """
        for record in self:
            part1 = record.protocol_number_part1 or ""
            part2 = record.protocol_number_part2 or ""
            # First 5 chars of part1 + ... + last 3 chars of part2
            short_part1 = part1[:5] if len(part1) >= 5 else part1
            short_part2 = part2[-3:] if len(part2) >= 3 else part2
            record.protocol_number = f"{short_part1}...{short_part2}"

    purchase_order_ids = fields.One2many(
        "purchase.order",
        "l10n_it_edi_doi_id",
        string="Purchase / Rfq Orders",
        copy=False,
        readonly=True,
    )

    type = fields.Selection(
        [("in", "Issued from company"), ("out", "Received from customers")],
        required=True,
        default="out",
    )

    # Override partner_id to make it not required
    # (required only for type='out', enforced by constraint)
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Partner",
        index=True,
        required=False,
        domain="['|', ('is_company', '=', True), ('parent_id', '=', False)]",
        help="For received declarations (type 'out'): the customer who sent the declaration. "
        "For issued declarations (type 'in'): optional, leave empty to use with any supplier.",
    )

    @api.constrains("type", "partner_id")
    def _check_partner_required_for_received(self):
        """Partner is required only for received declarations (type='out')."""
        for record in self:
            if record.type == "out" and not record.partner_id:
                raise ValidationError(
                    self.env._(
                        "Partner is required for received declarations (type 'Received from customers')."
                    )
                )

    def _get_validity_errors(self, company, partner, currency):
        """Override to skip partner check for issued declarations (type='in').

        For issued declarations (type='in'), the declaration can be used with
        any supplier, so we don't validate the partner.
        """
        errors = []
        for declaration in self:
            # Company check
            if not company or declaration.company_id != company:
                errors.append(
                    self.env._(
                        "The Declaration of Intent belongs to company %(declaration_company)s, not %(company)s.",
                        declaration_company=declaration.company_id.name,
                        company=company.name,
                    )
                )
            # Currency check
            if not currency or declaration.currency_id != currency:
                errors.append(
                    self.env._(
                        "The Declaration of Intent uses currency %(declaration_currency)s, not %(currency)s.",
                        declaration_currency=declaration.currency_id.name,
                        currency=currency.name,
                    )
                )
            # Partner check - SKIP for type "in" (issued from company)
            if declaration.type == "out":
                if not partner or declaration.partner_id != partner.commercial_partner_id:
                    errors.append(
                        self.env._(
                            "The Declaration of Intent belongs to partner %(declaration_partner)s, not %(partner)s.",
                            declaration_partner=declaration.partner_id.name,
                            partner=partner.commercial_partner_id.name if partner else "",
                        )
                    )
        return errors

    @api.model
    def _fetch_valid_declaration_of_intent(
        self, company, partner, currency, date, doi_type="out"
    ):
        """Override to not filter by partner for issued declarations (type='in').

        For issued declarations, the plafond can be used with any supplier,
        so we don't filter by partner.
        """
        domain = [
            ("state", "=", "active"),
            ("company_id", "=", company.id),
            ("currency_id", "=", currency.id),
            ("start_date", "<=", date),
            ("end_date", ">=", date),
            ("remaining", ">", 0),
            ("type", "=", doi_type),
        ]
        # Only filter by partner for received declarations (type='out')
        if doi_type == "out" and partner:
            domain.append(("partner_id", "=", partner.commercial_partner_id.id))

        return self.search(domain, limit=1)

    @api.depends(
        "purchase_order_ids",
        "purchase_order_ids.state",
        "purchase_order_ids.l10n_it_edi_doi_not_yet_invoiced",
    )
    def _compute_not_yet_invoiced(self):
        received_doi = self.filtered(lambda r: r.type == "out")
        issued_doi = self - received_doi
        super(L10nItDeclarationOfIntent, received_doi)._compute_not_yet_invoiced()
        for declaration in issued_doi:
            relevant_orders = declaration.purchase_order_ids.filtered(
                lambda order: order.state == "purchase"
            )
            declaration.not_yet_invoiced = sum(
                relevant_orders.mapped("l10n_it_edi_doi_not_yet_invoiced")
            )
        return  # W8110

    @api.ondelete(at_uninstall=False)
    def _unlink_except_linked_to_purchase_document(self):
        if self.purchase_order_ids:
            raise UserError(
                _(
                    "You cannot delete Declarations of Intents that "
                    "are already used on at least one Purchase Order."
                )
            )

    def action_open_invoice_ids(self):
        """Override to use different list view for issued declarations (type='in').

        For type 'in' (issued from company), use a view with 'Supplier' column.
        For type 'out' (received from customers), use the original view with 'Customer' column.
        """
        self.ensure_one()
        if self.type == "in":
            # Use purchase invoice list view with "Supplier" column
            list_view = self.env.ref(
                "l10n_it_edi_doi_extension.view_move_tree_purchase_doi"
            )
            name = _("Purchase Invoices using Declaration of Intent %s", self.display_name)
        else:
            # Use original sale invoice list view with "Customer" column
            list_view = self.env.ref("l10n_it_edi_doi.view_move_tree")
            name = _("Invoices using Declaration of Intent %s", self.display_name)

        return {
            "name": name,
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "domain": [("id", "in", self.invoice_ids.ids)],
            "views": [(list_view.id, "list"), (False, "form")],
            "search_view_id": [
                self.env.ref("account.view_account_invoice_filter").id
            ],
            "context": {
                "search_default_posted": 1,
            },
        }
