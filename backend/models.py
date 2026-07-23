from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class Comment(BaseModel):
    id: str
    text: str
    created_at: str


class Node(BaseModel):
    id: str
    label: str
    parent_id: Optional[str] = None
    children: List[str] = Field(default_factory=list)
    notes: str = ""
    canvas_x: float = 0
    canvas_y: float = 0
    collapsed: bool = False

    node_type: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    complexity: Optional[str] = None
    risk_level: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    owner: Optional[str] = None
    comments: List[Comment] = Field(default_factory=list)
    shape: str = "rect"
    group_children: bool = False
    is_group: bool = False
    classification: Optional[str] = None
    custom_color: Optional[str] = None


class Reference(BaseModel):
    id: str
    from_: str = Field(alias="from")
    to: str
    label: Optional[str] = None

    model_config = {"populate_by_name": True}


class ReferenceCreate(BaseModel):
    from_: str = Field(alias="from")
    to: str
    label: Optional[str] = None

    model_config = {"populate_by_name": True}


class ReferenceUpdate(BaseModel):
    from_: Optional[str] = Field(default=None, alias="from")
    to: Optional[str] = None
    label: Optional[str] = None

    model_config = {"populate_by_name": True}


class ActivityEntry(BaseModel):
    id: str
    timestamp: str
    message: str


class Project(BaseModel):
    id: str
    name: str
    created_at: str
    updated_at: str
    nodes: Dict[str, Node] = Field(default_factory=dict)
    references: List[Reference] = Field(default_factory=list)
    activity_log: List[ActivityEntry] = Field(default_factory=list)


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
    is_group: bool = False


class NodeUpdate(BaseModel):
    label: Optional[str] = None
    notes: Optional[str] = None
    collapsed: Optional[bool] = None
    node_type: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    complexity: Optional[str] = None
    risk_level: Optional[str] = None
    tags: Optional[List[str]] = None
    owner: Optional[str] = None
    shape: Optional[str] = None
    group_children: Optional[bool] = None
    is_group: Optional[bool] = None
    classification: Optional[str] = None
    custom_color: Optional[str] = None


class MoveSiblingRequest(BaseModel):
    direction: str  # "up" or "down"


class ReparentRequest(BaseModel):
    new_parent_id: str


class NodePosition(BaseModel):
    canvas_x: float
    canvas_y: float


class NodeWithLevel(Node):
    level: int


class CommentCreate(BaseModel):
    text: str


class TemplateNode(BaseModel):
    label: str
    notes: str = ""
    children: List["TemplateNode"] = Field(default_factory=list)


TemplateNode.model_rebuild()


class Template(BaseModel):
    id: str
    name: str
    created_at: str
    root: TemplateNode


class TemplateSummary(BaseModel):
    id: str
    name: str
    created_at: str
    node_count: int


class TemplateCreate(BaseModel):
    name: str


class OutlineImport(BaseModel):
    text: str


class AddParentRequest(BaseModel):
    label: str = "New parent"


class PasteSubtreeRequest(BaseModel):
    root: TemplateNode


class ValidationReport(BaseModel):
    score: int
    rating: str
    duplicate_labels: List[str]
    circular_references: List[List[str]]
    large_modules: List[str]
    single_child_nodes: List[str]
    missing_notes_count: int
