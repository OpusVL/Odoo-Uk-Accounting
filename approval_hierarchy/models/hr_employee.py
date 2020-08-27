# -*- coding: utf-8 -*-

from odoo import fields, models, _
from odoo.exceptions import UserError


class HrEmployeePublic(models.Model):
    _inherit = "hr.employee.public"

    delegated_user_id = fields.Many2one(readonly=True)


class HrEmployeeBase(models.AbstractModel):
    _inherit = "hr.employee.base"

    delegated_user_id = fields.Many2one(
        'res.users',
        string='Delegated User',
        tracking=True,
    )
    job_title = fields.Char(
        "Job Title",
        tracking=True,
    )
    mobile_phone = fields.Char(
        'Work Mobile',
        tracking=True,
    )
    work_phone = fields.Char(
        'Work Phone',
        tracking=True,
    )
    work_email = fields.Char(
        'Work Email',
        tracking=True,
    )
    work_location = fields.Char(
        'Work Location',
        tracking=True,
    )
    department_id = fields.Many2one(
        'hr.department',
        'Department',
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        tracking=True,
    )
    job_id = fields.Many2one(
        'hr.job',
        'Job Position',
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        tracking=True,
    )
    parent_id = fields.Many2one(
        'hr.employee',
        'Manager',
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        tracking=True,
    )
    address_id = fields.Many2one(
        'res.partner',
        'Work Address',
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        tracking=True,
    )
    coach_id = fields.Many2one(
        'hr.employee',
        'Coach',
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        tracking=True,
    )
    resource_calendar_id = fields.Many2one(
        'resource.calendar',
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        tracking=True,
    )
    tz = fields.Selection(
        string='Timezone',
        related='resource_id.tz',
        readonly=False,
        help="This field is used in order to define in which timezone the resources will work.",
        tracking=True,
    )


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('waiting', 'Waiting'),
            ('rejected', 'Rejected'),
            ('approved', 'Approved')
        ],
        string='Status',
        readonly=True,
        copy=False,
        default='draft',
        tracking=True,
    )
    user_id = fields.Many2one(
        'res.users',
        'User',
        related='resource_id.user_id',
        store=True,
        readonly=False,
        tracking=True,
    )
    barcode = fields.Char(
        string="Badge ID",
        help="ID used for employee identification.",
        groups="hr.group_hr_user,approval_hierarchy.group_amend_system_users,approval_hierarchy.group_approve_system_users",
        copy=False,

    )
    has_delegated = fields.Boolean(compute='_check_has_delegated')
    address_home_id = fields.Many2one(
        'res.partner',
        'Address',
        help='Enter here the private address of the employee, not the one linked to your company.',
        groups="hr.group_hr_user,approval_hierarchy.group_amend_system_users,approval_hierarchy.group_approve_system_users",
        tracking=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]"
    )
    private_email = fields.Char(
        related='address_home_id.email',
        string="Private Email",
        groups="hr.group_hr_user,approval_hierarchy.group_amend_system_users,approval_hierarchy.group_approve_system_users",
    )
    bank_account_id = fields.Many2one(
        'res.partner.bank',
        'Bank Account Number',
        domain="[('partner_id', '=', address_home_id), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        groups="hr.group_hr_user,approval_hierarchy.group_amend_system_users,approval_hierarchy.group_approve_system_users",
        tracking=True,
        help='Employee bank salary account'
    )
    country_id = fields.Many2one(
        'res.country',
        'Nationality (Country)',
        groups="hr.group_hr_user,approval_hierarchy.group_amend_system_users,approval_hierarchy.group_approve_system_users",
        tracking=True,
    )
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other')],
        groups="hr.group_hr_user,approval_hierarchy.group_amend_system_users,approval_hierarchy.group_approve_system_users",
        default="male",
        tracking=True,
    )
    birthday = fields.Date(
        'Date of Birth',
        groups="hr.group_hr_user,approval_hierarchy.group_amend_system_users,approval_hierarchy.group_approve_system_users",
        tracking=True
    )
    marital = fields.Selection([
        ('single', 'Single'),
        ('married', 'Married'),
        ('cohabitant', 'Legal Cohabitant'),
        ('widower', 'Widower'),
        ('divorced', 'Divorced')],
        string='Marital Status',
        groups="hr.group_hr_user,approval_hierarchy.group_amend_system_users,approval_hierarchy.group_approve_system_users",
        default='single',
        tracking=True,
    )
    children = fields.Integer(
        string='Number of Children',
        groups="hr.group_hr_user,approval_hierarchy.group_amend_system_users,approval_hierarchy.group_approve_system_users",
        tracking=True,
    )
    emergency_contact = fields.Char(
        "Emergency Contact",
        groups="hr.group_hr_user,approval_hierarchy.group_amend_system_users,approval_hierarchy.group_approve_system_users",
        tracking=True,
    )
    emergency_phone = fields.Char(
        "Emergency Phone",
        groups="hr.group_hr_user,approval_hierarchy.group_amend_system_users,approval_hierarchy.group_approve_system_users",
        tracking=True
    )
    permit_no = fields.Char(
        'Work Permit No',
        groups="hr.group_hr_user,approval_hierarchy.group_amend_system_users,approval_hierarchy.group_approve_system_users",
        tracking=True,
    )
    visa_no = fields.Char(
        'Visa No',
        groups="hr.group_hr_user,approval_hierarchy.group_amend_system_users,approval_hierarchy.group_approve_system_users",
        tracking=True,
    )
    visa_expire = fields.Date(
        'Visa Expire Date',
        groups="hr.group_hr_user,approval_hierarchy.group_amend_system_users,approval_hierarchy.group_approve_system_users",
        tracking=True,
    )
    certificate = fields.Selection([
        ('bachelor', 'Bachelor'),
        ('master', 'Master'),
        ('other', 'Other')],
        'Certificate Level',
        default='other',
        groups="hr.group_hr_user,approval_hierarchy.group_amend_system_users,approval_hierarchy.group_approve_system_users",
        tracking=True,
    )
    study_field = fields.Char(
        "Field of Study",
        groups="hr.group_hr_user,approval_hierarchy.group_amend_system_users,approval_hierarchy.group_approve_system_users",
        tracking=True,
    )
    study_school = fields.Char(
        "School",
        groups="hr.group_hr_user,approval_hierarchy.group_amend_system_users,approval_hierarchy.group_approve_system_users",
        tracking=True,
    )
    country_of_birth = fields.Many2one(
        'res.country',
        string="Country of Birth",
        groups="hr.group_hr_user,approval_hierarchy.group_amend_system_users,approval_hierarchy.group_approve_system_users",
        tracking=True,
    )
    emergency_phone = fields.Char(
        "Emergency Phone",
        groups="hr.group_hr_user,approval_hierarchy.group_amend_system_users,approval_hierarchy.group_approve_system_users",
        tracking=True,
    )
    identification_id = fields.Char(
        string='Identification No',
        groups="hr.group_hr_user,approval_hierarchy.group_amend_system_users,approval_hierarchy.group_approve_system_users",
        tracking=True,
    )
    km_home_work = fields.Integer(
        string="Km Home-Work",
        groups="hr.group_hr_user,approval_hierarchy.group_amend_system_users,approval_hierarchy.group_approve_system_users",
        tracking=True,
    )
    passport_id = fields.Char(
        'Passport No',
        groups="hr.group_hr_user,approval_hierarchy.group_amend_system_users,approval_hierarchy.group_approve_system_users",
        tracking=True
    )
    pin = fields.Char(
        string="PIN",
        groups="hr.group_hr_user,approval_hierarchy.group_amend_system_users,approval_hierarchy.group_approve_system_users",
        copy=False,
        help="PIN used to Check In/Out in Kiosk Mode (if enabled in Configuration).",
        tracking=True,
    )
    place_of_birth = fields.Char(
        'Place of Birth',
        groups="hr.group_hr_user,approval_hierarchy.group_amend_system_users,approval_hierarchy.group_approve_system_users",
        tracking=True,
    )
    spouse_complete_name = fields.Char(
        string="Spouse Complete Name",
        groups="hr.group_hr_user,approval_hierarchy.group_amend_system_users,approval_hierarchy.group_approve_system_users",
        tracking=True,
    )
    spouse_birthdate = fields.Date(
        string="Spouse Birthdate",
        groups="hr.group_hr_user,approval_hierarchy.group_amend_system_users,approval_hierarchy.group_approve_system_users",
        tracking=True,
    )
    phone = fields.Char(
        related='address_home_id.phone',
        related_sudo=False,
        string="Private Phone",
        groups="hr.group_hr_user,approval_hierarchy.group_amend_system_users,approval_hierarchy.group_approve_system_users",
    )

    def _check_has_delegated(self):
        for rec in self:
            rec.has_delegated = rec.delegated_user_id and True or False

    def get_approved_user(self, action):
        approval_user_id = False
        found = False
        employee = self
        while not found and employee:
            # Checks if employee has approval rights
            has_approval_rights = employee.check_if_has_approval_rights(
                action)
            if has_approval_rights:
                found = True
                delegated_user = employee.user_id.delegated_user_id
                if delegated_user:
                    while delegated_user:
                        approval_user_id = delegated_user
                        delegated_user = delegated_user.delegated_user_id
                else:
                    approval_user_id = employee.user_id
            else:
                # Replace with employee manager and next loop it will
                # controll if his manager has approval rights
                employee = employee.parent_id
        return approval_user_id

    def check_if_has_approval_rights(self, action):
        if not self.user_id or not self.job_id or not \
                self.job_id.state == 'approved' or not self.state == 'approved':
            return False
        else:
            role_action = self.job_id.job_role_ids.filtered(
                lambda r: r.role_action_id == action and r.permission)
            if role_action:
                return True
            else:
                return False

    def get_approved_user_amount_interval(self, action,
                                          value, currency):
        approval_user_id = False
        found = False
        employee = self
        while not found and employee:
            # Checks if employee has approval rights
            has_approval_rights = employee.check_if_has_approval_rights_amount_interval(
                action, value, currency)
            if has_approval_rights:
                found = True
                delegated_user = employee.user_id.delegated_user_id
                if delegated_user:
                    while delegated_user:
                        approval_user_id = delegated_user
                        delegated_user = delegated_user.delegated_user_id
                else:
                    approval_user_id = employee.user_id
            else:
                # Replace with employee manager and next loop it will
                # controll if his manager has approval rights
                employee = employee.parent_id
        return approval_user_id

    def check_if_has_approval_rights_amount_interval(self, action,
                                                     value, currency):
        if not self.user_id or not self.job_id or not \
                self.job_id.state == 'approved' or not self.state == 'approved':
            return False
        else:
            role_action = self.job_id.job_role_ids.filtered(
                lambda r: r.role_action_id == action and r.permission and
                          r.currency_id == currency)
            if role_action:
                # As a result of constraint unique if
                # role_action the length will be 1
                if role_action[0].min_value <= value <= role_action[0].max_value:
                    return True
                else:
                    return False
            else:
                return False

    def request_approval(self):
        if not self.env.user.has_group(
                "approval_hierarchy.group_amend_system_users"):
            raise UserError(_('You do not have the permission to request '
                              'approval for this employee. '
                              'Please contact the support team.')
                            )
        return self.with_context(supplier_action=True).write(
            {'state': 'waiting'}
        )

    def action_approve(self):
        if not self.env.user.has_group(
                "approval_hierarchy.group_approve_system_users"):
            raise UserError(_('You do not have the permission to approve '
                              'this employee. '
                              'Please contact the support team.'
                              )
                            )
        return self.with_context(supplier_action=True).write(
            {'state': 'approved'}
        )

    def action_reject(self):
        if not self.env.user.has_group(
                "approval_hierarchy.group_approve_system_users"):
            raise UserError(_('You do not have the permission to reject '
                              'this employee. '
                              'Please contact the support team.')
                            )
        return self.with_context(supplier_action=True).write(
            {'state': 'rejected'}
        )

    def set_to_draft(self):
        if not self.env.user.has_group(
                "approval_hierarchy.group_amend_system_users"):
            raise UserError(_('You do not have the permission to make changes '
                              'to this employee. '
                              'Please contact the support team.')
                            )
        return self.with_context(supplier_action=True).write({'state': 'draft'})

    def write(self, vals):
        if self._context.get('supplier_action') :
            return super(HrEmployee, self).write(vals)
        elif self._context.get('from_my_profile'):
            if self.env.user == self.user_id:
                return super(HrEmployee, self).write(vals)
            else:
                raise UserError(
                    _('You do not have the permission to make changes '
                      'to this employee. '
                      'Please contact the support team.'))
        elif self.env.user.has_group(
                "approval_hierarchy.group_amend_system_users"):
            vals['state'] = 'draft'
            return super(HrEmployee, self.with_context(
                supplier_action=True)).write(vals)
        else:
            raise UserError(_('You do not have the permission to make changes '
                              'to this employee. '
                              'Please contact the support team.'))
