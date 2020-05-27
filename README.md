# MeMS
Male Excel Micro Services

## VM
Although possible, it is highly recommended not to run MeMS directly in your
local machine. View the [VM_README](VM_README.md) file to get step by step
instructions for installing a VirtualBox VM to run MeMS in the same environment
as production.

## RestOC
The services in MeMS use a custom framework designed around RESTful API micro
services called RestOC. Documentation for it can be found at http://ouroboroscoding.com/rest-oc/

## FormatOC
RestOC itself uses another library called FormatOC which is used to load
definition files that allow for easy validation and cleaning up of document or
table structures. Documentation for it can be found at http://ouroboroscoding.com/format-oc/
