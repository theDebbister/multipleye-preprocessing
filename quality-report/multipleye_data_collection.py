from data_collection import DataCollection


class MulipleyeDataCollection(DataCollection):

    def __init__(self, language: str, country: str, year: int, eye_tracker: str, lab_number: int, kwargs: dict = None):
        super().__init__(language, country, year, eye_tracker, kwargs)
        self.lab_number = lab_number
