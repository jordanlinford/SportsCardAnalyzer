from typing import Dict, Any
from modules.services.firebase import FirebaseService
from modules.services.storage import StorageService
from modules.core.card_value_analyzer import CardValueAnalyzer

class ServiceContainer:
    _instance = None
    _services: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ServiceContainer, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._services:
            self._initialize_services()

    def _initialize_services(self):
        """Initialize all services"""
        self._services['firebase'] = FirebaseService()
        self._services['storage'] = StorageService()
        self._services['value_analyzer'] = CardValueAnalyzer()

    def get_service(self, service_name: str) -> Any:
        """Get a service by name"""
        if service_name not in self._services:
            raise ValueError(f"Service {service_name} not found")
        return self._services[service_name]

    @property
    def firebase(self) -> FirebaseService:
        return self.get_service('firebase')

    @property
    def storage(self) -> StorageService:
        return self.get_service('storage')

    @property
    def value_analyzer(self) -> CardValueAnalyzer:
        return self.get_service('value_analyzer') 