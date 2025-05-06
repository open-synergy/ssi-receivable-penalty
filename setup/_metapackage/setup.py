import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo14-addons-open-synergy-ssi-receivable-penalty",
    description="Meta package for open-synergy-ssi-receivable-penalty Odoo addons",
    version=version,
    install_requires=[
        'odoo14-addon-ssi_account_receivable_penalty',
        'odoo14-addon-ssi_account_receivable_penalty_sale',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
        'Framework :: Odoo :: 14.0',
    ]
)
