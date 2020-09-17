
# Record imports
from records.patient import Activity

def run():
	Activity.tableCreate();
	return True
