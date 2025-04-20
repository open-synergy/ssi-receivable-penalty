# Copyright 2022 OpenSynergy Indonesia
# Copyright 2022 PT. Simetri Sinergi Indonesia
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import date

from odoo import api, fields, models, tools


class CreatePenaltyFromComputation(models.TransientModel):
    _name = "create_penalty_from_computation"
    _description = "Create Penalty From Computation"

    @api.model
    def _default_computation_ids(self):
        return self.env.context.get("active_ids", False)

    computation_ids = fields.Many2many(
        string="Penalty Computations",
        comodel_name="account.receivable_penalty_computation",
        relation="rel_create_penalty_from_computation",
        column1="wizard_id",
        column2="computation_id",
        required=False,
        default=lambda self: self._default_computation_ids(),
    )
    detail_ids = fields.One2many(
        string="Details",
        comodel_name="create_penalty_from_computation.detail",
        inverse_name="wizard_id",
    )

    def action_confirm(self):
        for record in self.sudo():
            record._confirm()

    def _confirm(self):
        self.ensure_one()
        for detail in self.detail_ids:
            detail.create_penalty()


class CreatePenaltyFromComputationSummary(models.Model):
    _name = "create_penalty_from_computation.detail"
    _auto = False
    _description = "Create Penalty From Computation - Detail"

    wizard_id = fields.Many2one(
        string="# Contract",
        comodel_name="create_penalty_from_computation",
    )
    base_move_line_id = fields.Many2one(
        string="Base Move Line",
        comodel_name="account.move.line",
    )
    type_id = fields.Many2one(
        string="Penalty Type",
        comodel_name="account.receivable_penalty_type",
    )
    partner_id = fields.Many2one(
        string="Partner",
        comodel_name="res.partner",
    )

    def _select(self):
        select_str = """
        SELECT
            ROW_NUMBER() OVER() AS id,
            a.wizard_id AS wizard_id,
            b.base_move_line_id AS base_move_line_id,
            b.type_id as type_id,
            b.partner_id AS partner_id
        """
        return select_str

    def _from(self):
        from_str = """
        rel_create_penalty_from_computation AS a
        """
        return from_str

    def _where(self):
        where_str = """
        WHERE b.penalty_id IS NULL
        """
        return where_str

    def _join(self):
        join_str = """
        JOIN account_receivable_penalty_computation AS b
            ON a.computation_id = b.id
        """
        return join_str

    def _group_by(self):
        group_str = """
        GROUP BY    a.wizard_id,
                    b.base_move_line_id,
                    b.type_id,
                    b.partner_id
        """
        return group_str

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        # pylint: disable=locally-disabled, sql-injection
        self._cr.execute(
            """CREATE or REPLACE VIEW %s as (
            %s
            FROM %s
            %s
            %s
            %s
        )"""
            % (
                self._table,
                self._select(),
                self._from(),
                self._join(),
                self._where(),
                self._group_by(),
            )
        )

    def create_penalty(self):
        self.ensure_one()
        Penalty = self.env["account.receivable_penalty"]
        Computation = self.env["account.receivable_penalty_computation"]
        data = self._prepare_penalty_data()
        penalty = Penalty.create(data)

        criteria = [
            ("base_move_line_id", "=", self.base_move_line_id.id),
            ("type_id", "=", self.type_id.id),
            ("id", "in", self.wizard_id.computation_ids.ids),
        ]
        for computation in Computation.search(criteria):
            computation.write(
                {
                    "penalty_id": penalty.id,
                }
            )

        penalty.action_compute_tax()

    def _prepare_penalty_data(self):
        tax_ids = self.type_id.default_tax_ids.ids or False
        result = {
            "partner_id": self.partner_id.id,
            "type_id": self.type_id.id,
            "base_move_line_id": self.base_move_line_id.id,
            "date": date.today(),
            "date_due": date.today(),
            "journal_id": self.type_id.journal_id.id,
            "receivable_account_id": self.type_id.receivable_account_id.id,
            "income_account_id": self.type_id.income_account_id.id,
        }
        if tax_ids:
            result.update({"tax_ids": [(6, 0, tax_ids)]})
        return result
