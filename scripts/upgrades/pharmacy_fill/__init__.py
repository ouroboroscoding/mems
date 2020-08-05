# Import version files
from . import copy_adhoc, copy_ds_ids, copy_fill_errors, copy_outbound, \
				copy_rx, copy_triggers, create_tables, rename_perms

modules = [
	create_tables, rename_perms, copy_ds_ids, copy_fill_errors, \
	copy_outbound, copy_adhoc, copy_rx, copy_triggers
]
