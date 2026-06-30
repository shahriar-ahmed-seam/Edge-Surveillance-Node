"""Fleet status endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import Node
from ..db.session import get_session
from .auth import require_role
from .schemas import NodeOut

router = APIRouter(prefix="/api/nodes", tags=["nodes"])


@router.get("", response_model=list[NodeOut])
def list_nodes(db: Session = Depends(get_session), _user=Depends(require_role("viewer"))):
    nodes = db.execute(select(Node).order_by(Node.node_id)).scalars().all()
    return nodes


@router.get("/{node_id}", response_model=NodeOut)
def get_node(node_id: str, db: Session = Depends(get_session),
             _user=Depends(require_role("viewer"))):
    node = db.get(Node, node_id)
    if node is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Node not found")
    return node
