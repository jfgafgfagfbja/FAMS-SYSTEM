"""Truy cap bang face_embeddings (vector khuon mat 512 chieu, pgvector)."""
from sqlalchemy.orm import Session

from app.db import models


def get(db: Session, embedding_id: int) -> models.FaceEmbedding | None:
    return db.get(models.FaceEmbedding, embedding_id)


def of_student(db: Session, student_id: int) -> list[models.FaceEmbedding]:
    return (db.query(models.FaceEmbedding).filter_by(student_id=student_id)
            .order_by(models.FaceEmbedding.created_at.desc()).all())


def pending(db: Session) -> list[models.FaceEmbedding]:
    return (db.query(models.FaceEmbedding)
            .filter(models.FaceEmbedding.status == "pending")
            .order_by(models.FaceEmbedding.created_at).all())


def nearest_approved_of_other_student(db: Session,
                                      emb: models.FaceEmbedding) -> tuple[int, float] | None:
    """(student_id, khoang cach cosine) cua vector DA DUYET gan nhat thuoc SV khac."""
    distance = models.FaceEmbedding.embedding.cosine_distance(list(emb.embedding))
    return (
        db.query(models.FaceEmbedding.student_id, distance.label("distance"))
        .filter(models.FaceEmbedding.student_id != emb.student_id,
                models.FaceEmbedding.status == "approved")
        .order_by(distance)
        .first()
    )
