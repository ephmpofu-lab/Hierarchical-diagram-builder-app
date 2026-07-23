from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class Node(BaseModel):
    id: str
    label: str
    parent_id: Optional[str] = None
    children: List[str] = Field(default_factory=list)
    notes: str = ""
    canvas_x: float = 0
    canvas_y: float = 0
    collapsed: bool = False


class Reference(BaseModel):
    from_: str = Field(alias="from")
    to: str
    label: Optional[str] = None

    model_config = {"populate_by_name": True}


class Project(BaseModel):
    id: str
    name: str
    created_at: str
    updated_at: str
    nodes: Dict[str, Node] = Field(default_factory=dict)
    references: List[Reference] = Field(default_factory=list)


class ProjectSummary(BaseModel):
    id: str
    name: str
    updated_at: str
    node_count: int


class ProjectCreate(BaseModel):
    name: str


class ProjectRename(BaseModel):
    name: str


class NodeCreate(BaseModel):
    parent_id: str
    label: str = "New node"
    insert_after: Optional[str] = None


class NodeUpdate(BaseModel):
    label: Optional[str] = None
    notes: Optional[str] = None
    collapsed: Optional[bool] = None


class NodePosition(BaseModel):
    canvas_x: float
    canvas_y: float


class NodeWithLevel(Node):
    level: int
