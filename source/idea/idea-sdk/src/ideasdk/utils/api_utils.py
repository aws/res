import re

from ideadatamodel import (
    exceptions,
    errorcodes,
)

from ideadatamodel.constants import INVALID_RANGE_ERROR_MESSAGE

class ApiUtils:

    @staticmethod    
    def validate_input(input_string: str, validation_regex: str, error_message=""):
        if not re.match(validation_regex, input_string):
            raise exceptions.soca_exception(
                error_code=errorcodes.INVALID_PARAMS,
                message=error_message
            )
            
    @staticmethod
    def validate_input_range(value: int, range: tuple, error_message=INVALID_RANGE_ERROR_MESSAGE):
        if value < range[0] or value > range[1]:
            raise exceptions.soca_exception(
                error_code=errorcodes.INVALID_PARAMS,
                message=error_message
            )