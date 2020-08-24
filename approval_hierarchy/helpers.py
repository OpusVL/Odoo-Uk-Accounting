
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
