"""
Base interfaces for database operations following SOLID principles
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any


class DatabaseInterface(ABC):
    """
    Interface for database operations (Dependency Inversion Principle)
    """

    @abstractmethod
    def connect(self) -> None:
        """Establish database connection"""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Close database connection"""
        pass

    @abstractmethod
    def execute(self, query: str, params: tuple = ()) -> Any:
        """
        Execute a database query

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            Query result
        """
        pass

    @abstractmethod
    def commit(self) -> None:
        """Commit current transaction"""
        pass

    @abstractmethod
    def rollback(self) -> None:
        """Rollback current transaction"""
        pass


class RepositoryInterface(ABC):
    """
    Generic repository interface (Repository Pattern)
    """

    @abstractmethod
    def create(self, entity: Any) -> str:
        """Create a new entity"""
        pass

    @abstractmethod
    def get(self, entity_id: str) -> Optional[Any]:
        """Get entity by ID"""
        pass

    @abstractmethod
    def update(self, entity: Any) -> bool:
        """Update existing entity"""
        pass

    @abstractmethod
    def delete(self, entity_id: str) -> bool:
        """Delete entity by ID"""
        pass

    @abstractmethod
    def list_all(self) -> List[Any]:
        """List all entities"""
        pass
