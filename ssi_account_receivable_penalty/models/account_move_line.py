# Copyright 2025 OpenSynergy Indonesia
# Copyright 2025 PT. Simetri Sinergi Indonesia
# License AGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class AccountMoveLine(models.Model):
    _name = "account.move.line"
    _inherit = [
        "account.move.line",
    ]

    receivable_penalty_ids = fields.One2many(
        string="Related Receivable Penalties",
        comodel_name="account.receivable_penalty",
        inverse_name="base_move_line_id",
    )
    exclude_from_penalty = fields.Boolean(
        string="Exclude From Penalty Computation",
    )
