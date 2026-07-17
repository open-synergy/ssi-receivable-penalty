# Copyright 2026 OpenSynergy Indonesia
# Copyright 2026 PT. Simetri Sinergi Indonesia
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "Account Receivable Penalty + Operating Unit",
    "version": "14.0.1.0.0",
    "website": "https://simetri-sinergi.id",
    "author": "PT. Simetri Sinergi Indonesia, OpenSynergy Indonesia",
    "contributors": [
        "Andhitia Rama <andhitia.r@gmail.com>",
    ],
    "license": "AGPL-3",
    "installable": True,
    "depends": [
        "ssi_account_receivable_penalty",
        "ssi_operating_unit_mixin",
    ],
    "data": [
        "security/res_group/account_receivable_penalty.xml",
        "security/ir_rule/account_receivable_penalty.xml",
        "view/account_receivable_penalty.xml",
        "security/res_group/account_receivable_penalty_computation.xml",
        "security/ir_rule/account_receivable_penalty_computation.xml",
        "view/account_receivable_penalty_computation.xml",
        "security/res_group/batch_receivable_penalty_computation.xml",
        "security/ir_rule/batch_receivable_penalty_computation.xml",
        "view/batch_receivable_penalty_computation.xml",
    ],
}
