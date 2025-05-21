# Copyright 2022 OpenSynergy Indonesia
# Copyright 2022 PT. Simetri Sinergi Indonesia
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from datetime import date

from odoo import api, fields, models


class CreatePenaltyComputationFromMove(models.TransientModel):
    _name = "create_penalty_computation_from_move"
    _description = "Create Penalty Computation From Journal Entry"

    @api.model
    def _default_account_move_ids(self):
        return self.env.context.get("active_ids", False)

    @api.model
    def _default_date(self):
        return date.today()

    account_move_ids = fields.Many2many(
        string="Journal Entries",
        comodel_name="account.move",
        relation="rel_create_penalty_computation_from_move",
        column1="wizard_id",
        column2="move_id",
        required=False,
        default=lambda self: self._default_account_move_ids(),
    )
    type_id = fields.Many2one(
        string="Penalty Type",
        comodel_name="account.receivable_penalty_type",
        required=True,
    )
    date = fields.Date(
        string="Date",
        required=True,
    )

    def action_confirm(self):
        for record in self.sudo():
            record._confirm()

    def _confirm(self):
        self.ensure_one()
        for move in self.account_move_ids:
            for ml in move.line_ids.filtered(
                lambda r: r.account_id.user_type_id.type == "receivable"
                and r.debit > 0.0
            ):
                self.type_id.create_penalty_computation(ml, self.date)
