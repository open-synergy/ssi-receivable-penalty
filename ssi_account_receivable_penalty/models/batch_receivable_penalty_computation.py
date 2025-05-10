# Copyright 2022 OpenSynergy Indonesia
# Copyright 2022 PT. Simetri Sinergi Indonesia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models

from odoo.addons.ssi_decorator import ssi_decorator


class BatchPenaltyComputation(models.Model):
    _name = "batch_receivable_penalty_computation"
    _inherit = [
        "mixin.transaction_cancel",
        "mixin.transaction_terminate",
        "mixin.transaction_done",
        "mixin.transaction_open",
        "mixin.transaction_confirm",
        "mixin.company_currency",
    ]
    _description = "Batch Receivable Penalty Computation"

    # Multiple Approval Attribute
    _approval_from_state = "draft"
    _approval_to_state = "open"
    _approval_state = "confirm"
    _after_approved_method = "action_open"

    # Attributes related to add element on view automatically
    _automatically_insert_view_element = True
    _automatically_insert_open_policy_fields = False
    _automatically_insert_open_button = False
    _automatically_insert_done_policy_fields = False
    _automatically_insert_done_button = False

    _statusbar_visible_label = "draft,confirm,open,done"
    _policy_field_order = [
        "confirm_ok",
        "approve_ok",
        "reject_ok",
        "restart_approval_ok",
        "open_ok",
        "cancel_ok",
        "restart_ok",
        "done_ok",
        "terminate_ok",
        "manual_number_ok",
    ]
    _header_button_order = [
        "action_confirm",
        "action_approve_approval",
        "action_reject_approval",
        "%(ssi_transaction_cancel_mixin.base_select_cancel_reason_action)d",
        "%(ssi_transaction_terminate_mixin.base_select_terminate_reason_action)d",
        "action_restart",
    ]

    # Attributes related to add element on search view automatically
    _state_filter_order = [
        "dom_draft",
        "dom_confirm",
        "dom_open",
        "dom_reject",
        "dom_done",
        "dom_cancel",
    ]

    # Sequence attribute
    _create_sequence_state = "open"

    allowed_base_move_line_ids = fields.Many2many(
        string="Allowed Base Move Line",
        comodel_name="account.move.line",
        compute="_compute_allowed_base_move_line_ids",
        store=False,
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
    use_min_days_overdue = fields.Boolean(
        string="Use Min. Days Overdue",
        readonly=True,
        states={
            "draft": [
                ("readonly", False),
            ],
        },
    )
    min_days_overdue = fields.Integer(
        string="Min. Days Overdue",
        readonly=True,
        states={
            "draft": [
                ("readonly", False),
            ],
        },
    )
    use_max_days_overdue = fields.Boolean(
        string="Use Max. Days Overdue",
        readonly=True,
        states={
            "draft": [
                ("readonly", False),
            ],
        },
    )
    max_days_overdue = fields.Integer(
        string="Max. Days Overdue",
        readonly=True,
        states={
            "draft": [
                ("readonly", False),
            ],
        },
    )
    detail_ids = fields.One2many(
        string="Details",
        comodel_name="batch_receivable_penalty_computation.detail",
        inverse_name="batch_id",
        readonly=True,
    )
    num_computation = fields.Integer(
        string="Num. of Generated Penalty Computation",
        compute="_compute_num_computation",
        store=True,
        compute_sudo=True,
    )
    num_done_computation = fields.Integer(
        string="Num. of Finished Penalty Computation",
        compute="_compute_num_computation",
        store=True,
        compute_sudo=True,
    )
    all_computation_done_ok = fields.Boolean(
        string="All Computation Done",
        compute="_compute_num_computation",
        store=True,
        compute_sudo=True,
    )

    @api.depends(
        "detail_ids",
        "detail_ids.computation_id",
        "detail_ids.computation_id.state",
        "detail_ids.create_computation_ok",
    )
    def _compute_num_computation(self):
        Detail = self.env["batch_receivable_penalty_computation.detail"]
        for record in self:
            record.all_computation_done_ok = False
            criteria = [
                ("batch_id", "=", record.id),
                ("create_computation_ok", "=", True),
                ("computation_id", "!=", False),
            ]
            record.num_computation = Detail.search_count(criteria)
            criteria = [
                ("batch_id", "=", record.id),
                ("create_computation_ok", "=", True),
                ("computation_id", "!=", False),
                ("computation_id.state", "=", "done"),
            ]
            record.num_done_computation = Detail.search_count(criteria)
            if (
                record.num_computation != 0
                and record.num_computation == record.num_done_computation
            ):
                record.all_computation_done_ok = True

    @api.depends(
        "date",
        "type_id",
        "use_min_days_overdue",
        "min_days_overdue",
        "use_max_days_overdue",
        "max_days_overdue",
    )
    def _compute_allowed_base_move_line_ids(self):
        AML = self.env["account.move.line"]
        for record in self:
            result = []
            if record.date and record.type_id:
                ttype = record.type_id
                criteria = [
                    ("account_id.id", "in", ttype.account_ids.ids),
                    ("debit", ">", 0.0),
                    ("reconciled", "=", False),
                    ("move_id.state", "=", "posted"),
                    ("partner_id", "!=", False),
                    ("exclude_from_penalty", "=", False),
                ]
                result = AML.search(criteria).ids
            record.allowed_base_move_line_ids = result

    def action_compute_computation(self):
        for record in self.sudo():
            record._compute_computation()

    def _compute_computation(self):
        self.ensure_one()
        Detail = self.env["batch_receivable_penalty_computation.detail"]
        self.detail_ids.unlink()
        for line in self.allowed_base_move_line_ids:
            data = {
                "batch_id": self.id,
                "base_move_line_id": line.id,
            }
            Detail.create(data)

    @api.model
    def _get_policy_field(self):
        res = super(BatchPenaltyComputation, self)._get_policy_field()
        policy_field = [
            "confirm_ok",
            "approve_ok",
            "open_ok",
            "done_ok",
            "cancel_ok",
            "reject_ok",
            "terminate_ok",
            "restart_ok",
            "restart_approval_ok",
            "manual_number_ok",
        ]
        res += policy_field
        return res

    @ssi_decorator.post_open_action()
    def _10_create_penalty_computation(self):
        self.ensure_one()
        for detail in self.detail_ids.filtered(
            lambda r: r.create_computation_ok
            and not r.override_penalty_computation_creation
        ):
            detail._create_computation()

    @ssi_decorator.insert_on_form_view()
    def _insert_form_element(self, view_arch):
        if self._automatically_insert_view_element:
            view_arch = self._reconfigure_statusbar_visible(view_arch)
        return view_arch
