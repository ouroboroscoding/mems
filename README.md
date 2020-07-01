# MeMS
Male Excel Micro Services

## VM
Although possible, it is highly recommended not to run MeMS directly in your local machine. View the [VM_README](VM_README.md) file to get step by step instructions for installing a VirtualBox VM to run MeMS in the same environment as production.

## Libraries

### RestOC
The services in MeMS use a custom framework designed around RESTful API micro services called RestOC. Documentation for it can be found at http://ouroboroscoding.com/rest-oc/

### FormatOC
RestOC itself uses another library called FormatOC which is used to load definition files that allow for easy validation and cleaning up of document or table structures. Documentation for it can be found at http://ouroboroscoding.com/format-oc/

## Communication
Communication between different services works using a standard format that must be maintained in order to avoid any confusion or issues with libraries/modules that interact with the services. Services using RestOC.Services handle this using the Effect class (RestOC.Services.Effect), however the format is straight forward and can be easily followed in other languages or without libraries.

### Format
The format is JSON using a simple object with three variables of which at least data or error must be included.

    {
        "data": [mixed],
        "error": {
            "code": [uint],
            "msg": [mixed],
        }
        "warning": [string]
    }

#### data
Data assumes a valid request with no issue and can be any data, including false, None/NULL, or []. Just because a request does not have data to return does not mean an error has occurred and data should reflect that based on the request. As an example, returning a customer's details

    {
        "data": {
            "firstName": "John",
            "lastName": "Smith",
            "address": {
                "street": "123 Main Street",
                "city": "Anytown",
                "state": "NC",
                "country": "US"
            }
        }
    }

#### error
Error should only be set if a valid error has occurred such as a client failing to pass necessary data, passing that data in an invalid format, or the server having some sort of communication failure with another service or third party. Errors must always consist of a valid error `code` using an unsigned integer. Error codes must not be duplicated and reserved codes can be found in the medefs repo in the errors.json file which is shared with mems at definitions/errors.json.
Codes are used to make programming simpler for clients connecting to the services. If additional info about the error is necessary it can be placed in the optional `msg` value. For example, 1001 is a common error code for a request not getting proper data, either missing or invalid. The `code` is the same regardless of which data is wrong, but the `msg` can specify a list of fields that are wrong and the specific issue with them, e.g.

    {
        "error": 1001,
        "msg": [["user.email", "invalid"], ["user.passwd", "missing]]
    }

#### warning
Warning can be used in the case of a request mostly working fine, but with some non-critical failure occurring. For example, if a client updates some piece of data that normally fires off a notification to someone else, the request might return true in data, and a warning message notifying the client. This can avoid repeated attempts at something that shouldn't be run again and again. e.g.

    {
        "data": true,
        "warning": "email notifcation failed to send, please notify customer directly"
    }

