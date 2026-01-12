from abc import ABC, abstractmethod
import logging

class BaseSearcher(ABC):
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
    @abstractmethod
    def search(self, query, start_date=None, max_results=10, stop_event=None):
        """
        Search for papers.
        Returns a list of paper metadata dictionaries.
        """
        pass
        
    @abstractmethod
    def download(self, paper_meta):
        """
        Downloads the paper.
        Returns absolute path to the file.
        """
        pass
