from abc import ABC, abstractmethod
from typing import Dict, Type

class IService(ABC):
    """
    后台服务接口 (例如：Web服务器, 调度器, 机器人)。
    Interface for background services (e.g., WebServer, Scheduler, TelegramBot).
    """
    
    @abstractmethod
    def start(self):
        """
        启动服务 (首选非阻塞方式，或者定义线程策略)。
        Start the service (non-blocking preferred, or define threading strategy)
        """
        pass

    @abstractmethod
    def stop(self):
        """
        停止服务并清理资源。
        Stop the service and cleanup
        """
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass

class ServiceManager:
    _services: Dict[str, IService] = {}

    @classmethod
    def register(cls, service: IService):
        cls._services[service.name] = service
        print(f"[System] Registered service: {service.name}")

    @classmethod
    def start_all(cls):
        for name, service in cls._services.items():
            print(f"[System] Starting service: {name}...")
            service.start()

    @classmethod
    def stop_all(cls):
        for name, service in cls._services.items():
            print(f"[System] Stopping service: {name}...")
            service.stop()
