from abc import ABC, abstractmethod

class IConnector(ABC):
    @abstractmethod
    def connect(self, config):
        """
        Establishes a connection to the data source based on the provided config.
        :param config: Configuration needed to establish the connection (API keys, endpoints, etc.)
        """
        pass

    @abstractmethod
    def fetch_data(self):
        """
        Fetches data from the connected source and passes it to the next component.
        This could be raw file data, emails, documents, or API responses.
        :return: A dictionary with file data or API response
        """
        pass

    @abstractmethod
    def validate_config(self, config):
        """
        Validates if the configuration provided is valid for the connector.
        :param config: The configuration settings to be validated
        """
        pass
