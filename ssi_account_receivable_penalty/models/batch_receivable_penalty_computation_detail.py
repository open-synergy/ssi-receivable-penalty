# Copyright 2022 OpenSynergy Indonesia
# Copyright 2022 PT. Simetri Sinergi Indonesia
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import api, fields, models


class BatchReceivablePenaltyComputation(models.Model):
    _name = "batch_receivable_penalty_computation.detail"
    _description = "Batch Receivable Penalty Computation - Detail"

    batch_id = fields.Many2one(
        string="# Batch",
        comodel_name="batch_receivable_penalty_computation",
        required=True,
        ondelete="cascade",
    )
    date = fields.Date(
        string="Date",
        related="batch_id.date",
        store=True,
    )
    company_currency_id = fields.Many2one(
        related="batch_id.company_currency_id",
        store=True,
    )
    base_move_line_id = fields.Many2one(
        string="Base Move Line",
        comodel_name="account.move.line",
        required=True,
    )
    base_move_id = fields.Many2one(
        string="Base Accounting Entry",
        comodel_name="account.move",
        related="base_move_line_id.move_id",
        store=True,
    )
    amount_total = fields.Monetary(
        string="Amount Total",
        related="base_move_line_id.debit",
        currency_field="company_currency_id",
        store=True,
    )
    days_overdue = fields.Integer(
        string="Days Overdue",
        compute="_compute_days_overdue",
        store=True,
        compute_sudo=True,
    )
    amount_residual = fields.Monetary(
        string="Amount Residual",
        compute="_compute_amount_residual",
        currency_field="company_currency_id",
        store=True,
        compute_sudo=True,
    )
    computation_id = fields.Many2one(
        string="# Penalty Computation",
        comodel_name="account.receivable_penalty_computation",
        readonly=True,
        ondelete="restrict",
    )
    create_computation_ok = fields.Boolean(
        string="Create Computation",
        compute="_compute_create_computation_ok",
        store=True,
        compute_sudo=True,
    )
    override_penalty_computation_creation = fields.Boolean(
        string="Overide Penalty Computation Creation",
        readonly=True,
    )
    state = fields.Selection(
        related="batch_id.state",
        store=False,
    )

    @api.depends(
        "base_move_line_id",
        "date",
    )
    def _compute_days_overdue(self):
        for record in self:
            result = 0
            if (
                record.base_move_line_id
                and record.date
                and record.base_move_line_id.date_maturity
            ):
                dt_date_due = record.base_move_line_id.date_maturity
                dt_date = record.date
                result = (dt_date - dt_date_due).days
            record.days_overdue = result

    @api.depends(
        "base_move_line_id",
        "date",
    )
    def _compute_amount_residual(self):
        for record in self:
            result = 0.0
            if record.base_move_line_id and record.date:
                base_ml = record.base_move_line_id
                lines = base_ml.matched_debit_ids.mapped(
                    "debit_move_id"
                ) + base_ml.matched_credit_ids.mapped("credit_move_id")
                line_ids = lines.ids
                criteria = [
                    ("id", "in", line_ids),
                    ("date", "<=", record.date),
                ]
                payment_lines = self.env["account.move.line"].search(criteria)
                for payment_line in payment_lines:
                    result += payment_line.credit + payment_line.debit
                result = base_ml.debit - result
            record.amount_residual = result

    @api.depends(
        "base_move_line_id",
        "days_overdue",
        "batch_id.use_min_days_overdue",
        "batch_id.min_days_overdue",
        "batch_id.use_max_days_overdue",
        "batch_id.max_days_overdue",
    )
    def _compute_create_computation_ok(self):
        for record in self:
            result = True
            if record.batch_id.use_min_days_overdue:
                if record.days_overdue < record.batch_id.min_days_overdue:
                    result = False
                    continue
            if record.batch_id.use_max_days_overdue:
                if record.days_overdue > record.batch_id.max_days_overdue:
                    result = False
                    continue
            record.create_computation_ok = result

    def action_override_penalty_computation_creation(self):
        for record in self.sudo():
            record._override_penalty_computation_creation()

    def action_disable_override_penalty_computation_creation(self):
        for record in self.sudo():
            record._disable_override_penalty_computation_creation()

    def action_remove_penalty_computation(self):
        for record in self.sudo():
            record._remove_penalty_computation()

    def _remove_penalty_computation(self):
        self.ensure_one()
        computation = self.computation_id

        if computation:
            self.write(
                {
                    "computation_id": False,
                }
            )
            computation.unlink()

    def _override_penalty_computation_creation(self):
        self.ensure_one()
        self.write(
            {
                "override_penalty_computation_creation": True,
            }
        )

    def _disable_override_penalty_computation_creation(self):
        self.ensure_one()
        self.write(
            {
                "override_penalty_computation_creation": False,
            }
        )

    def _create_computation(self):
        self.ensure_one()
        Computation = self.env["account.receivable_penalty_computation"]
        batch = self.batch_id
        data = {
            "date": batch.date,
            "base_move_line_id": self.base_move_line_id.id,
            "type_id": batch.type_id.id,
            "partner_id": self.base_move_line_id.partner_id.id,
            "base_amount": batch.type_id._evaluate_python(
                self.base_move_line_id, batch.type_id.base_amount_python
            ),
            "penalty_amount": batch.type_id._evaluate_python(
                self.base_move_line_id, batch.type_id.penalty_amount_python
            ),
            "batch_id": self.id,
        }
        computation = Computation.create(data)
        self.write(
            {
                "computation_id": computation.id,
            }
        )
