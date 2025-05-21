# Copyright 2022 OpenSynergy Indonesia
# Copyright 2022 PT. Simetri Sinergi Indonesia
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import date

from odoo import _, fields, models, tools
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
    date_cutoff_python = fields.Text(
        string="Date Cutoff Python",
        default="""# Available variables:
#  - env: Odoo Environment on which the action is triggered.
#  - document: Recordset of move lines.
#  - result: Return result.
result = 0""",
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
    default_tax_ids = fields.Many2many(
        string="Default Taxes",
        comodel_name="account.tax",
        relation="rel_receivable_penalty_type_2_tax",
        column1="type_id",
        column2="tax_id",
    )
    limit_max_penalty_ok = fields.Boolean(
        string="Limit Max Penalty Count",
        default=False,
    )
    max_penalty = fields.Integer(
        string="Max Penalty",
        required=True,
        default=0,
    )

    def onchange_max_penalty(self):
        if not self.limit_max_penalty_ok:
            self.max_penalty = 0

    def _get_policy_localdict(self, move_line):
        self.ensure_one()
        return {
            "env": self.env,
            "document": move_line,
            "time": tools.safe_eval.time,
            "datetime": tools.safe_eval.datetime,
            "dateutil": tools.safe_eval.dateutil,
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

    def _prepare_computation_data(self, move_line, penalty_date=False):
        self.ensure_one()
        if not penalty_date:
            penalty_date = date.today()

        return {
            "base_move_line_id": move_line.id,
            "partner_id": move_line.partner_id.id,
            "type_id": self.id,
            "date": penalty_date,
            "base_amount": 0.0,
            "penalty_amount": 0.0,
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
        for document in self:
            criteria = [
                ("account_id.reconcile", "!=", False),
                ("reconciled", "=", False),
                ("account_id", "in", document.account_ids.ids),
                ("debit", ">", 0),
                ("partner_id", "!=", False),
            ]
            move_line_ids = obj_account_move_line.search(criteria)
            if move_line_ids:
                for move_line in move_line_ids:
                    self.create_penalty_computation(move_line)

    def create_penalty_computation(self, move_line, penalty_date=False):
        self.ensure_one()
        PenaltyComputation = self.env["account.receivable_penalty_computation"]
        _check = self._evaluate_python(move_line, self.condition_python)
        _check_limit = self._check_max_limit(move_line)

        if _check and _check_limit:
            penalty = PenaltyComputation.create(
                self._prepare_computation_data(move_line, penalty_date)
            )
            penalty.onchange_base_amount()
            penalty.onchange_penalty_amount()

    def _check_max_limit(self, move_line):
        self.ensure_one()
        result = True
        if not self.limit_max_penalty_ok:
            return result

        PenaltyComputation = self.env["account.receivable_penalty_computation"]
        partner = move_line.partner_id.commercial_partner_id
        criteria = [
            ("partner_id.commercial_partner_id.id", "=", partner.id),
            ("type_id.id", "=", self.id),
            ("state", "in", ["confirm", "open", "done"]),
            ("base_move_line_id.id", "=", move_line.id),
        ]
        if PenaltyComputation.search_count(criteria) >= self.max_penalty:
            result = False

        return result
