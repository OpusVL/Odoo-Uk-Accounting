from odoo import _


def reset_config_settings_sysparam(cr):
    """
    Called from migration scripts as it will be a fairly common block.
    If the key doesn't exist, will just UPDATE 0 and the key will
    get created as part of initial install which is intended
    """
    cr.execute("""
        UPDATE ir_config_parameter
        SET value='False'
        WHERE key='has_run_approval_set_config'
    """)


# A process that will be updated manually in case there
# are added or removed other fields. Actually are added all fields that are
# visible in gui on the respective models
def get_fields_to_be_tracked():
    return {
        'res.partner': [
            'company_type',
            'name',
            'state',
            'approval_user_id',
            'street',
            'street2',
            'city',
            'state_id',
            'zip',
            'country_id',
            'vat',
            'jac_vsr_number',
            'phone',
            'mobile',
            'email',
            'website',
            'category_id',
            'child_ids',
            'user_id',
            'property_payment_term_id',
            'property_product_pricelist',
            'property_supplier_payment_term_id',
            'property_account_position_id',
            'property_stock_customer',
            'property_stock_supplier',
            'ref',
            'industry_id',
            'bank_ids',
            'property_account_receivable_id',
            'property_account_payable_id',
            'comment',
            'purchase_warn',
            'payment_warn',
        ],
        'res.partner.bank': [
            'acc_number',
            'sort_code',
            'short_name',
            'sort_code',
            'short_name',
            'account_type',
            'acc_type',
            'bank_id',
            'acc_holder_name',
        ],
        'hr.employee.base': [
            'delegated_user_id',
            'job_title',
            'mobile_phone',
            'work_phone',
            'work_email',
            'work_location',
            'department_id',
            'job_id',
            'parent_id',
            'address_id',
            'coach_id',
            'resource_calendar_id',
            'tz',
        ],
        'hr.employee': [
            'name',
            'state',
            'user_id',
            'barcode',
            'address_home_id',
            'private_email',
            'bank_account_id',
            'country_id',
            'gender',
            'birthday',
            'marital',
            'children',
            'emergency_contact',
            'emergency_contact',
            'permit_no',
            'visa_no',
            'visa_expire',
            'visa_expire',
            'study_field',
            'study_school',
            'country_of_birth',
            'emergency_phone',
            'identification_id',
            'km_home_work',
            'passport_id',
            'pin',
            'place_of_birth',
            'spouse_complete_name',
            'spouse_birthdate',
            'phone',
            'mobile_phone',
            'job_id',
        ],
        'hr.job': [
            'state',
            'department_id',
            'description',
            'name',
            'job_role_ids',
        ],
    }


def get_fields_to_be_excluded():
    return {
        'account.move': [
            'posted_date',
        ],
    }


def get_create_write_unlink_access_groups():
    return {
        'hr.employee': 'approval_hierarchy.group_amend_system_users',
        'hr.job': 'approval_hierarchy.group_amend_system_users',
        'res.partner': 'approval_hierarchy.supplier_set_up_role',
        'account.move.out_invoice': 'approval_hierarchy.input_ar_invoice_role',
        'account.move.out_refund': 'approval_hierarchy.input_ar_invoice_role',
        'account.move.out_receipt': 'approval_hierarchy.input_ar_invoice_role',
        'account.move.in_invoice': 'approval_hierarchy.input_ap_invoice_role',
        'account.move.in_refund': 'approval_hierarchy.input_ap_invoice_role',
        'account.move.in_receipt': 'approval_hierarchy.input_ap_invoice_role',
        'account.move.entry': 'approval_hierarchy.input_account_move_role',
        'account.bank.statement':
            'approval_hierarchy.import_bank_statement_role',
    }


CUSTOM_ERROR_MESSAGES = {
    'create': _('You do not have the permission to create %s. '
                'Please contact the support team.'),
    'write': _('You do not have the permission to modify %s. '
               'Please contact the support team.'),
    'unlink': _('You do not have the permission to delete %s. '
                'Please contact the support team.'),
    'approve': _('You do not have the permission to approve %s. '
                 'Please contact the administration team.'),
    'reject': _('You do not have the permission to reject %s. '
                'Please contact the administration team.'),
    'request': _('You do not have the permission to request approval. '
                 'Please contact the administration team.'),
    'export': _('You do not have the permission to export %s. '
                'Please contact the administration team.'),
}

CONFIGURATION_ERROR_MESSAGE = _('Your user account is not configured properly. '
                                'Please contact the support team.')
