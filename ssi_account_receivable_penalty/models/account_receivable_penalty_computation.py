# Copyright 2022 OpenSynergy Indonesia
# Copyright 2022 PT. Simetri Sinergi Indonesia
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from odoo import api, fields, models


class AccountReceivablePenaltyComputation(models.Model):
    _name = "account.receivable_penalty_computation"
    _inherit = [
        "mixin.transaction_confirm",
        "mixin.transaction_done",
        "mixin.transaction_cancel",
        "mixin.company_currency",
    ]
    _description = "Account Receivable Penalty Computation"

    # Multiple Approval Attribute
    _approval_from_state = "draft"
    _approval_to_state = "done"
    _approval_state = "confirm"
    _after_approved_method = "action_done"

    # Attributes related to add element on view automatically
    _automatically_insert_view_element = True
    _automatically_insert_done_policy_fields = False
    _automatically_insert_done_button = False

    _statusbar_visible_label = "draft,confirm,done"
    _policy_field_order = [
        "confirm_ok",
        "approve_ok",
        "reject_ok",
        "restart_approval_ok",
        "cancel_ok",
        "restart_ok",
        "done_ok",
        "manual_number_ok",
    ]
    _header_button_order = [
        "action_confirm",
        "action_approve_approval",
        "action_reject_approval",
        "%(ssi_transaction_cancel_mixin.base_select_cancel_reason_action)d",
        "action_restart",
    ]

    # Attributes related to add element on search view automatically
    _state_filter_order = [
        "dom_draft",
        "dom_confirm",
        "dom_reject",
        "dom_done",
        "dom_cancel",
    ]

    # Sequence attribute
    _create_sequence_state = "done"

    # FIELD
    penalty_id = fields.Many2one(
        string="# Penalty",
        comodel_name="account.receivable_penalty",
        required=False,
        ondelete="set null",
    )
    partner_id = fields.Many2one(
        string="Partner",
        comodel_name="res.partner",
        domain=[
            ("parent_id", "=", False),
        ],
        required=True,
        readonly=True,
        ondelete="restrict",
        states={
            "draft": [
                ("readonly", False),
            ],
        },
    )

    @api.depends(
        "partner_id",
        "type_id",
    )
    def _compute_allowed_base_move_line_ids(self):
        AML = self.env["account.move.line"]
        for record in self:
            result = []
            if record.partner_id and record.type_id:
                ttype = record.type_id
                criteria = [
                    ("partner_id.id", "=", record.partner_id.id),
                    ("account_id.id", "in", ttype.account_ids.ids),
                    ("debit", ">", 0.0),
                    ("reconciled", "=", False),
                ]
                result = AML.search(criteria).ids
            record.allowed_base_move_line_ids = result

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
    base_amount = fields.Monetary(
        string="Base Amount",
        currency_field="company_currency_id",
        required=True,
    )
    penalty_amount = fields.Monetary(
        string="Penalty Amount",
        currency_field="company_currency_id",
        required=True,
    )
    account_move_line_id = fields.Many2one(
        string="# Move Line",
        comodel_name="account.move.line",
        readonly=True,
        copy=False,
    )
    state = fields.Selection(
        string="State",
        default="draft",
        required=True,
        readonly=True,
        selection=[
            ("draft", "Draft"),
            ("confirm", "Waiting for Approval"),
            ("done", "Done"),
            ("cancel", "Cancelled"),
            ("reject", "Rejected"),
        ],
    )

    @api.model
    def _get_policy_field(self):
        res = super(AccountReceivablePenaltyComputation, self)._get_policy_field()
        policy_field = [
            "confirm_ok",
            "approve_ok",
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
        "base_move_line_id",
    )
    def onchange_base_amount(self):
        self.base_amount = 0.0

    @api.onchange(
        "type_id",
        "base_move_line_id",
    )
    def onchange_penalty_amount(self):
        self.penalty_amount = 0.0

    def _create_aml(self):
        self.ensure_one()
        obj_account_move_line = self.env["account.move.line"]
        aml = obj_account_move_line.with_context(check_move_validity=False).create(
            self._prepare_aml_data()
        )
        self.write(
            {
                "account_move_line_id": aml.id,
            }
        )

    def _prepare_aml_data(self):
        self.ensure_one()
        penalty = self.penalty_id
        debit, credit, amount_currency = self._get_aml_amount(
            penalty.company_currency_id
        )
        return {
            "move_id": penalty.move_id.id,
            "name": self.name,
            "partner_id": penalty.base_move_line_id.partner_id.id,
            "account_id": penalty.income_account_id.id,
            "quantity": 1.0,
            "price_unit": self.penalty_amount,
            "debit": debit,
            "credit": credit,
            "currency_id": penalty.company_currency_id.id,
            "amount_currency": amount_currency,
        }

    def _get_aml_amount(self, currency):
        self.ensure_one()
        debit = credit = amount = amount_currency = 0.0
        penalty = self.penalty_id
        move_date = penalty.date

        amount_currency = self.penalty_amount
        amount = currency.with_context(date=move_date).compute(
            amount_currency,
            penalty.company_currency_id,
        )

        if amount < 0.0:
            debit = abs(amount)
        else:
            credit = abs(amount)

        return debit, credit, amount_currency
