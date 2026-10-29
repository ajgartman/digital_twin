# Custom exceptions. Fascinating!

class MeasurementNotFoundError(Exception):
    """Raised when a measurement is not found in the database. Custom error message."""
    pass

class InvalidRunIdError(Exception):
    """Raised when measurement input is incorrect - missing "_" etc...Custom error message"""
