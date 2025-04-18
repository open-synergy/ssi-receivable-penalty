# Copyright 2022 OpenSynergy Indonesia
# Copyright 2022 PT. Simetri Sinergi Indonesia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models


class AccountReceivablePenaltyTax(models.Model):
    _name = "account.receivable_penalty_tax"
    _description = "Account Receivable Penalty Tax"

    # FIELD
    penalty_id = fields.Many2one(
        string="Penalty",
        comodel_name="account.receivable_penalty",
        required=True,
        ondelete="cascade",
    )
    tax_id = fields.Many2one(
        string="Tax",
        comodel_name="account.tax",
        required=False,
        ondelete="restrict",
    )
    account_id = fields.Many2one(
        string="Account",
        comodel_name="account.account",
        required=False,
        ondelete="restrict",
    )
    base_amount = fields.Float(
        string="Base Amount",
        required=True,
    )
    tax_amount = fields.Float(
        string="Tax Amount",
        required=True,
    )
    account_move_line_id = fields.Many2one(
        string="Journal Item",
        comodel_name="account.move.line",
        readonly=True,
        copy=False,
    )

    def get_grouping_key(self, value):
        return str(value["tax_id"]) + "-" + str(value["account_id"])

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
            "name": self.tax_id.name,
            "partner_id": penalty.base_move_line_id.partner_id.id,
            "account_id": self.account_id.id,
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

        amount_currency = self.tax_amount
        amount = currency.with_context(date=move_date).compute(
            amount_currency,
            penalty.company_currency_id,
        )

        if amount < 0.0:
            debit = abs(amount)
        else:
            credit = abs(amount)

        return debit, credit, amount_currency
