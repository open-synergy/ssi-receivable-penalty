# Copyright 2025 OpenSynergy Indonesia
# Copyright 2025 PT. Simetri Sinergi Indonesia
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "Account Receivable Penalty + Sale Order Integration",
    "version": "14.0.1.1.0",
    "website": "https://simetri-sinergi.id",
    "author": "PT. Simetri Sinergi Indonesia, OpenSynergy Indonesia",
    "license": "AGPL-3",
    "installable": True,
    "depends": [
        "ssi_account_receivable_penalty",
        "ssi_sale",
    ],
    "data": [
        "data/policy_template_data.xml",
        "views/sale_order_views.xml",
    ],
    "demo": [],
    "images": [],
}
