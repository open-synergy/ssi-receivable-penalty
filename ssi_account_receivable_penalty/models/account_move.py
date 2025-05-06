# Copyright 2025 OpenSynergy Indonesia
# Copyright 2025 PT. Simetri Sinergi Indonesia
# License AGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = [
        "account.move",
    ]

    receivable_penalty_ids = fields.One2many(
        string="Related Receivable Penalties",
        comodel_name="account.receivable_penalty",
        inverse_name="base_move_id",
    )
