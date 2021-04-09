{
    "name": "UK Accounting Localization",
    "summary": "UK Accounting: Localization",
    "category": "Accounting",
    "description": """
        UK Accounting: Localization
    """,
    "author": "Opus Vision Limited",
    "website": "https://opusvl.com",
    "version": "13.0.1.0.2",
    # any module necessary for this one to work correctly
    "depends": [
        "account",
        "base_iban",
        "base_vat",
        "l10n_uk",
    ],
    # always loaded
    "data": [
        # Security
        "security/uk_accounting_security.xml",

        # Data
        "data/account_type_data.xml",
        "data/l10n_uk_chart_data.xml",
        "data/account.account.template.csv",
        "data/account.chart.template.csv",
        "data/account_payment_method.xml",
        "data/account_tax_data.xml",
        "data/account_chart_template_data.xml",

        # Views
        "views/account_account_view.xml",
        "views/account_move_view.xml",
        "views/res_partner_bank_view.xml",
        "views/res_config_settings_views.xml",
        "views/account_journal_view.xml",
        "views/account_payment_view.xml",
    ],
}
