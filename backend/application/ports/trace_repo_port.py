import abc
from backend.domain.models.trace import WorkflowTrace

class ITraceRepository(abc.ABC):
    @abc.abstractmethod
    async def save(self, trace: WorkflowTrace) -> None:
        pass
        
    @abc.abstractmethod
    async def get_all(self) -> list[WorkflowTrace]:
        pass
