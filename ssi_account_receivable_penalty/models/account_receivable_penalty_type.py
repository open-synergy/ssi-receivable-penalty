# Copyright 2022 OpenSynergy Indonesia
# Copyright 2022 PT. Simetri Sinergi Indonesia
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import _, fields, models
from odoo.exceptions import Warning as UserError
from odoo.tools.safe_eval import safe_eval


class AccountReceivablePenaltyType(models.Model):
    _name = "account.receivable_penalty_type"
    _inherit = ["mixin.master_data"]
    _description = "Account Receivable Penalty Type"

    name = fields.Char(
        string="Penalty Type",
    )
    journal_id = fields.Many2one(
        string="Journal",
        comodel_name="account.journal",
        required=True,
        ondelete="restrict",
    )
    receivable_account_id = fields.Many2one(
        string="Receivable Account",
        comodel_name="account.account",
        required=True,
        ondelete="restrict",
    )
    income_account_id = fields.Many2one(
        string="Income Account",
        comodel_name="account.account",
        required=True,
        ondelete="restrict",
    )
    base_amount_python = fields.Text(
        string="Base Amount Python",
        default="""# Available variables:
#  - env: Odoo Environment on which the action is triggered.
#  - document: Recordset of move lines.
#  - result: Return result.
result = 0.0""",
        copy=True,
    )
    penalty_amount_python = fields.Text(
        string="Penalty Amount Python",
        default="""# Available variables:
#  - env: Odoo Environment on which the action is triggered.
#  - document: Recordset of move lines.
#  - result: Return result.
result = 0.0""",
        copy=True,
    )
    condition_python = fields.Text(
        string="Condition Python",
        default="""# Available variables:
#  - env: Odoo Environment on which the action is triggered.
#  - document: Recordset of move lines.
#  - result: Return result.
result = True""",
        copy=True,
    )
    cron_id = fields.Many2one(
        string="Cron",
        comodel_name="ir.cron",
        readonly=True,
        copy=False,
    )
    account_ids = fields.Many2many(
        string="Accounts",
        comodel_name="account.account",
        relation="rel_account_2_receivable_penalty_type",
        column1="type_id",
        column2="account_id",
    )

    def _get_policy_localdict(self, move_line):
        self.ensure_one()
        return {
            "env": self.env,
            "document": move_line,
        }

    def _evaluate_python(self, move_line, python_code):
        self.ensure_one()
        res = False
        localdict = self._get_policy_localdict(move_line)
        try:
            safe_eval(python_code, localdict, mode="exec", nocopy=True)
            res = localdict["result"]
        except Exception as error:
            raise UserError(_("Error evaluating conditions.\n %s") % error)
        return res

    def _prepare_cron_data(self):
        self.ensure_one()
        return {
            "name": self.name,
            "model_id": self.env.ref(
                "ssi_account_receivable_penalty.model_account_receivable_penalty_type"
            ).id,
            "interval_number": 1,
            "interval_type": "hours",
            "state": "code",
            "code": "model.browse(%s).cron_create_penalty_computation()" % self.id,
            "active": True,
        }

    def _prepare_computation_data(self, move_line):
        self.ensure_one()
        return {
            "base_move_line_id": move_line.id,
            "type_id": self.id,
            "date": fields.Date.context_today(self),
            "base_amount": self._evaluate_python(move_line, self.base_amount_python),
            "penalty_amount": self._evaluate_python(
                move_line, self.penalty_amount_python
            ),
            "state": "draft",
        }

    def action_create_cron(self):
        for document in self:
            obj_ir_cron = self.env["ir.cron"]
            cron_id = obj_ir_cron.create(document._prepare_cron_data())
            document.cron_id = cron_id

    def action_delete_cron(self):
        for document in self:
            document.cron_id.unlink()

    def cron_create_penalty_computation(self):
        obj_account_move_line = self.env["account.move.line"]
        obj_penalty_computation = self.env["account.receivable_penalty_computation"]
        for document in self:
            criteria = [
                ("account_id.reconcile", "!=", False),
                ("reconciled", "=", False),
                ("account_id", "in", document.account_ids.ids),
                ("debit", ">", 0),
            ]
            move_line_ids = obj_account_move_line.search(criteria)
            if move_line_ids:
                for move_line in move_line_ids:
                    _check = self._evaluate_python(move_line, self.condition_python)
                    if _check:
                        obj_penalty_computation.create(
                            self._prepare_computation_data(move_line)
                        )
