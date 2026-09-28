from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import Node
from schemas import NodeResponse
from typing import List

router = APIRouter(prefix="/api", tags=["nodes"])

@router.get("/nodes/status", response_model=List[NodeResponse])
def get_all_nodes(db: Session = Depends(get_db)):
    return db.query(Node).all()

@router.get("/nodes/{node_id}", response_model=NodeResponse)
def get_node_by_id(node_id: int, db: Session = Depends(get_db)):
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        return {"error": "Node not found"}
    return node
