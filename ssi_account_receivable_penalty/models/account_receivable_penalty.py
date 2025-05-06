# Copyright 2022 OpenSynergy Indonesia
# Copyright 2022 PT. Simetri Sinergi Indonesia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models

from odoo.addons.ssi_decorator import ssi_decorator


class AccountReceivablePenalty(models.Model):
    _name = "account.receivable_penalty"
    _inherit = [
        "mixin.transaction_cancel",
        "mixin.transaction_done",
        "mixin.transaction_open",
        "mixin.transaction_confirm",
        "mixin.company_currency",
    ]
    _description = "Account Receivable Penalty"

    # Multiple Approval Attribute
    _approval_from_state = "draft"
    _approval_to_state = "open"
    _approval_state = "confirm"
    _after_approved_method = "action_open"

    # Attributes related to add element on view automatically
    _automatically_insert_view_element = True
    _automatically_insert_done_policy_fields = False
    _automatically_insert_done_button = False

    _statusbar_visible_label = "draft,confirm,open,done"
    _policy_field_order = [
        "confirm_ok",
        "approve_ok",
        "reject_ok",
        "restart_approval_ok",
        "cancel_ok",
        "restart_ok",
        "open_ok",
        "done_ok",
        "manual_number_ok",
    ]
    _header_button_order = [
        "action_confirm",
        "action_approve_approval",
        "action_reject_approval",
        "action_done",
        "%(ssi_transaction_cancel_mixin.base_select_cancel_reason_action)d",
        "action_restart",
    ]

    # Attributes related to add element on search view automatically
    _state_filter_order = [
        "dom_draft",
        "dom_confirm",
        "dom_reject",
        "dom_open",
        "dom_done",
        "dom_cancel",
    ]

    # Sequence attribute
    _create_sequence_state = "open"

    # FIELD
    partner_id = fields.Many2one(
        string="Partner",
        comodel_name="res.partner",
        required=True,
        readonly=True,
        ondelete="restrict",
        states={
            "draft": [
                ("readonly", False),
            ],
        },
    )
    type_id = fields.Many2one(
        string="Type",
        comodel_name="account.receivable_penalty_type",
        required=True,
        readonly=True,
        ondelete="restrict",
        states={
            "draft": [
                ("readonly", False),
            ],
        },
    )
    date = fields.Date(
        string="Date",
        required=True,
        readonly=True,
        states={
            "draft": [
                ("readonly", False),
            ],
        },
    )
    date_due = fields.Date(
        string="Date Due",
        required=True,
        readonly=True,
        states={
            "draft": [
                ("readonly", False),
            ],
        },
    )

    @api.depends(
        "type_id",
        "partner_id",
    )
    def _compute_allowed_base_move_line_ids(self):
        AML = self.env["account.move.line"]
        for document in self:
            result = []
            if document.partner_id and document.type_id:
                ttype = document.type_id
                criteria = [
                    ("reconciled", "=", False),
                    ("account_id", "in", ttype.account_ids.ids),
                    ("debit", ">", 0),
                    ("partner_id", "=", document.partner_id.id),
                ]
                result = AML.search(criteria).ids
            document.allowed_base_move_line_ids = result

    allowed_base_move_line_ids = fields.Many2many(
        string="Allowed Base Move Line",
        comodel_name="account.move.line",
        compute="_compute_allowed_base_move_line_ids",
        store=False,
    )
    base_move_line_id = fields.Many2one(
        string="Base Move Line",
        comodel_name="account.move.line",
        required=True,
        readonly=True,
        states={
            "draft": [
                ("readonly", False),
            ],
        },
    )
    base_move_id = fields.Many2one(
        string="# Base Accounting Entry",
        comodel_name="account.move",
        related="base_move_line_id.move_id",
        store=True,
    )
    journal_id = fields.Many2one(
        string="Journal",
        comodel_name="account.journal",
        required=True,
        readonly=True,
        states={
            "draft": [
                ("readonly", False),
            ],
        },
        ondelete="restrict",
    )
    receivable_account_id = fields.Many2one(
        string="Receivable Account",
        comodel_name="account.account",
        required=True,
        readonly=True,
        states={
            "draft": [
                ("readonly", False),
            ],
        },
        ondelete="restrict",
    )
    income_account_id = fields.Many2one(
        string="Income Account",
        comodel_name="account.account",
        required=True,
        readonly=True,
        states={
            "draft": [
                ("readonly", False),
            ],
        },
        ondelete="restrict",
    )
    receivable_move_line_id = fields.Many2one(
        string="Receivable Move Line",
        comodel_name="account.move.line",
        readonly=True,
        ondelete="set null",
        copy=False,
    )
    move_id = fields.Many2one(
        string="# Move",
        comodel_name="account.move",
        readonly=True,
    )
    move_line_ids = fields.Many2many(
        string="Journal Items",
        comodel_name="account.move.line",
        compute="_compute_move_line_ids",
        compute_sudo=True,
        store=False,
    )
    move_line_payment_ids = fields.Many2many(
        string="Payments",
        related="move_id.move_line_payment_ids",
        store=False,
    )
    last_payment_date = fields.Date(
        string="Last Payment Date",
        related="move_id.last_payment_date",
        store=True,
    )
    last_payment_line_id = fields.Many2one(
        string="#Last Payment Line",
        related="move_id.last_payment_line_id",
        store=True,
    )

    @api.depends(
        "move_id",
        "move_id.line_ids",
    )
    def _compute_move_line_ids(self):
        for record in self:
            result = []
            if record.move_id:
                result = record.move_id.line_ids
            record.move_line_ids = result

    @api.depends(
        "receivable_move_line_id",
        "receivable_move_line_id.matched_debit_ids",
        "receivable_move_line_id.matched_credit_ids",
    )
    def _compute_reconcile(self):
        for record in self:
            result = False
            if record.receivable_move_line_id.reconciled:
                result = True
            record.reconcile = result

    reconcile = fields.Boolean(
        string="Reconcile",
        compute="_compute_reconcile",
        store=True,
    )

    @api.depends(
        "type_id",
        "base_move_line_id",
    )
    def _compute_allowed_computation_ids(self):
        obj_computation = self.env["account.receivable_penalty_computation"]
        for document in self:
            result = []
            criteria = [
                ("penalty_id", "=", False),
                ("base_move_line_id", "=", document.base_move_line_id.id),
                ("state", "=", "done"),
            ]
            computation_ids = obj_computation.search(criteria)
            if computation_ids:
                result = computation_ids.ids
            document.allowed_computation_ids = result

    allowed_computation_ids = fields.Many2many(
        string="Allowed Computations",
        comodel_name="account.receivable_penalty_computation",
        compute="_compute_allowed_computation_ids",
        store=False,
    )
    computation_ids = fields.One2many(
        string="Computations",
        comodel_name="account.receivable_penalty_computation",
        inverse_name="penalty_id",
        readonly=True,
        states={
            "draft": [
                ("readonly", False),
            ],
        },
        copy=True,
    )
    tax_ids = fields.Many2many(
        string="Taxes",
        comodel_name="account.tax",
        relation="rel_receivable_penalty_2_tax",
        column1="penalty_id",
        column2="tax_id",
        readonly=True,
        states={
            "draft": [
                ("readonly", False),
            ],
        },
        copy=True,
    )
    penalty_tax_ids = fields.One2many(
        string="Penalty Taxes",
        comodel_name="account.receivable_penalty_tax",
        inverse_name="penalty_id",
        readonly=True,
        states={
            "draft": [
                ("readonly", False),
            ],
        },
        copy=True,
    )

    @api.depends(
        "computation_ids",
        "computation_ids.penalty_amount",
        "penalty_tax_ids",
        "penalty_tax_ids.tax_amount",
    )
    def _compute_amount(self):
        for document in self:
            amount_untaxed = amount_tax = 0.0
            for computation in document.computation_ids:
                amount_untaxed += computation.penalty_amount

            for tax in document.penalty_tax_ids:
                amount_tax += tax.tax_amount

            document.amount_untaxed = amount_untaxed
            document.amount_tax = amount_tax
            document.amount_total = amount_untaxed + amount_tax

    amount_untaxed = fields.Monetary(
        string="Amount Untaxed",
        compute="_compute_amount",
        store=True,
        currency_field="company_currency_id",
    )
    amount_tax = fields.Monetary(
        string="Amount Tax",
        compute="_compute_amount",
        store=True,
        currency_field="company_currency_id",
    )
    amount_total = fields.Monetary(
        string="Amount Total",
        compute="_compute_amount",
        store=True,
        currency_field="company_currency_id",
    )

    @api.depends(
        "amount_total",
        "state",
        "receivable_move_line_id",
        "receivable_move_line_id.reconciled",
        "receivable_move_line_id.amount_residual",
        "receivable_move_line_id.amount_residual_currency",
    )
    def _compute_residual(self):
        for document in self:
            paid = 0.0
            residual = document.amount_total
            currency = document.company_currency_id
            if document.receivable_move_line_id:
                move_line = document.receivable_move_line_id
                if not currency:
                    residual = move_line.amount_residual
                else:
                    residual = move_line.amount_residual_currency
                paid = document.amount_total - residual
            document.amount_paid = paid
            document.amount_residual = residual

    amount_paid = fields.Monetary(
        string="Amount Paid",
        compute="_compute_residual",
        store=True,
        currency_field="company_currency_id",
    )
    amount_residual = fields.Monetary(
        string="Amount Residual",
        compute="_compute_residual",
        store=True,
        currency_field="company_currency_id",
    )

    @api.model
    def _get_policy_field(self):
        res = super(AccountReceivablePenalty, self)._get_policy_field()
        policy_field = [
            "confirm_ok",
            "approve_ok",
            "open_ok",
            "done_ok",
            "cancel_ok",
            "reject_ok",
            "restart_ok",
            "restart_approval_ok",
            "manual_number_ok",
        ]
        res += policy_field
        return res

    @api.onchange(
        "type_id",
    )
    def onchange_journal_id(self):
        if self.type_id:
            self.journal_id = self.type_id.journal_id.id

    @api.onchange(
        "type_id",
    )
    def onchange_receivable_account_id(self):
        if self.type_id:
            self.receivable_account_id = self.type_id.receivable_account_id.id

    @api.onchange(
        "type_id",
    )
    def onchange_income_account_id(self):
        if self.type_id:
            self.income_account_id = self.type_id.income_account_id.id

    def _populate(self):
        self.ensure_one()
        self.allowed_computation_ids.write(
            {
                "penalty_id": self.id,
            }
        )

    def action_populate(self):
        for record in self:
            record._populate()

    def action_clear_computation(self):
        for record in self:
            record._clear_computation()

    def _clear_computation(self):
        self.ensure_one()
        self.computation_ids.write({"penalty_id": False})

    def action_compute_tax(self):
        for record in self:
            record._recompute_tax()

    def _recompute_tax(self):
        self.ensure_one()
        taxes_grouped = self.get_taxes_values()
        self.penalty_tax_ids.unlink()
        tax_lines = []
        for tax in taxes_grouped.values():
            tax_lines.append((0, 0, tax))
        self.write({"penalty_tax_ids": tax_lines})

    def _prepare_tax_line_vals(self, tax):
        vals = {
            "penalty_id": self.id,
            "tax_id": tax["id"],
            "tax_amount": tax["amount"],
            "base_amount": tax["base"],
            "account_id": tax["account_id"],
        }
        return vals

    def get_taxes_values(self):
        self.ensure_one()
        obj_penalty_tax = self.env["account.receivable_penalty_tax"]
        tax_grouped = {}
        round_curr = self.company_currency_id.round
        for computation in self.computation_ids:
            for taxes_id in self.tax_ids:
                price_unit = computation.penalty_amount
                taxes = taxes_id.compute_all(
                    price_unit=price_unit, currency=self.company_currency_id, quantity=1
                )["taxes"]
                for tax in taxes:
                    val = self._prepare_tax_line_vals(tax)
                    key = obj_penalty_tax.browse(tax["id"]).get_grouping_key(val)

                    if key not in tax_grouped:
                        tax_grouped[key] = val
                        tax_grouped[key]["base_amount"] = round_curr(val["base_amount"])
                    else:
                        tax_grouped[key]["tax_amount"] += val["tax_amount"]
                        tax_grouped[key]["base_amount"] += round_curr(
                            val["base_amount"]
                        )
        return tax_grouped

    def _prepare_account_move_data(self):
        self.ensure_one()
        return {
            "date": self.date,
            "name": self.name,
            "journal_id": self.journal_id.id,
            "ref": self.name,
        }

    def _get_receivable_amount(self, currency):
        self.ensure_one()
        debit = credit = amount = amount_currency = 0.0
        move_date = self.date

        amount_currency = self.amount_total
        amount = currency.with_context(date=move_date).compute(
            amount_currency,
            self.company_currency_id,
        )

        if amount > 0.0:
            debit = abs(amount)
        else:
            credit = abs(amount)

        return debit, credit, amount_currency

    def _prepare_receivable_aml_data(self):
        self.ensure_one()
        debit, credit, amount_currency = self._get_receivable_amount(
            self.company_currency_id
        )
        data = {
            "name": self.name,
            "move_id": self.move_id.id,
            "partner_id": self.base_move_line_id.partner_id.id,
            "account_id": self.receivable_account_id.id,
            "debit": debit,
            "credit": credit,
            "currency_id": self.company_currency_id.id,
            "amount_currency": amount_currency,
            "date_maturity": self.date_due,
        }
        return data

    def _create_receivable_aml(self):
        self.ensure_one()
        obj_account_move_line = self.env["account.move.line"]
        aml = obj_account_move_line.with_context(check_move_validity=False).create(
            self._prepare_receivable_aml_data()
        )
        self.write(
            {
                "receivable_move_line_id": aml.id,
            }
        )

    def _create_computation_aml(self):
        self.ensure_one()
        for computation in self.computation_ids:
            computation._create_aml()

    def _create_tax_aml(self):
        self.ensure_one()
        for tax in self.penalty_tax_ids:
            tax._create_aml()

    @ssi_decorator.post_open_action()
    def _create_accounting_entry(self):
        self.ensure_one()
        if self.move_id:
            return True

        move = (
            self.env["account.move"]
            .with_context(check_move_validity=False)
            .create(self._prepare_account_move_data())
        )
        self.write(
            {
                "move_id": move.id,
            }
        )
        self._create_receivable_aml()
        self._create_computation_aml()
        self._create_tax_aml()
        self.move_id.action_post()

    @ssi_decorator.post_cancel_action()
    def _delete_accounting_entry(self):
        self.ensure_one()
        if self.move_id:
            move = self.move_id
            self.write(
                {
                    "move_id": False,
                }
            )
            move.unlink()

    @ssi_decorator.insert_on_form_view()
    def _insert_form_element(self, view_arch):
        if self._automatically_insert_view_element:
            view_arch = self._reconfigure_statusbar_visible(view_arch)
        return view_arch
