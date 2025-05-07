# Copyright 2025 OpenSynergy Indonesia
# Copyright 2025 PT. Simetri Sinergi Indonesia
# License AGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


class SaleOrder(models.Model):
    _name = "sale.order"
    _inherit = [
        "sale.order",
    ]

    receivable_penalty_ok = fields.Boolean(
        string="Can View Receivable Penalty",
        compute="_compute_policy",
        compute_sudo=True,
        store=False,
    )

    receivable_penalty_ids = fields.Many2many(
        string="Related Receivable Penalties",
        comodel_name="account.receivable_penalty",
        compute="_compute_receivable_penalty_ids",
        store=False,
        compute_sudo=True,
    )
    receivable_penalty_count = fields.Integer(
        string="Receivable Penalty Count",
        compute="_compute_receivable_penalty_count",
        compute_sudo=True,
        store=True,
    )

    @api.depends(
        "invoice_ids",
        "receivable_penalty_ids",
    )
    def _compute_receivable_penalty_count(self):
        for record in self:
            result = len(record.receivable_penalty_ids)
            record.receivable_penalty_count = result

    def _compute_policy(self):
        _super = super(SaleOrder, self)
        _super._compute_policy()

    @api.model
    def _get_policy_field(self):
        res = super(SaleOrder, self)._get_policy_field()
        policy_field = [
            "receivable_penalty_ok",
        ]
        res += policy_field
        return res

    def _compute_receivable_penalty_ids(self):
        for record in self:
            result = []
            if record.invoice_ids:
                for invoice in record.invoice_ids:
                    if invoice.receivable_penalty_ids:
                        for penalty in invoice.receivable_penalty_ids:
                            result.append(penalty.id)
            record.receivable_penalty_ids = result

    def action_view_penalty(self):
        for record in self.sudo():
            result = record._view_penalty()
        return result

    def _view_penalty(self):
        waction = self.env.ref(
            "ssi_account_receivable_penalty.receivable_penalty_action"
        ).read()[0]
        waction.update(
            {
                "view_mode": "tree,form",
                "domain": [("id", "in", self.receivable_penalty_ids.ids)],
                "context": {},
            }
        )
        return waction
