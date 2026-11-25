"""don xin phep vang; quy trinh duyet khuon mat (nguoi duyet, SV xac nhan); bo ma QR;
chuan hoa schedules.room

Revision ID: e2a7c4b91f6d
Revises: d4f8a2c6e913
Create Date: 2026-11-10

- leave_requests: SV xin phep vang mot buoi (lich hoc + ngay); GV lop / Lanh dao Khoa duyet hoac
  tu choi kem ly do; SV xac nhan da nhan ket qua.
- face_embeddings: reviewed_by, reviewed_at (P.CTSV duyet), student_ack_at (SV xac nhan ket qua).
- attendance_sessions.require_qr: bo (bo han chuc nang ma QR khi SV tu diem danh).
- schedules.room: chi giu ten phong TU NHAP khi khong chon phong trong danh muc. Khi da co room_id,
  ma phong lay qua room_id (room_id -> ma phong la phu thuoc bac cau - vi pham 3NF). Chi xoa cac
  gia tri trung dung ma phong da chon (khong mat du lieu nguoi dung tu ghi khac ma phong).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'e2a7c4b91f6d'
down_revision: Union[str, Sequence[str], None] = 'd4f8a2c6e913'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'leave_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('schedule_id', sa.Integer(), nullable=False),
        sa.Column('absence_date', sa.Date(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=10), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('reviewed_by', sa.Integer(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('review_note', sa.String(length=500), nullable=False),
        sa.Column('student_ack_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['student_id'], ['students.id']),
        sa.ForeignKeyConstraint(['schedule_id'], ['schedules.id']),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('student_id', 'schedule_id', 'absence_date'),
    )
    op.create_index(op.f('ix_leave_requests_student_id'), 'leave_requests', ['student_id'])
    op.create_index(op.f('ix_leave_requests_schedule_id'), 'leave_requests', ['schedule_id'])

    op.add_column('face_embeddings', sa.Column(
        'reviewed_by', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True))
    op.add_column('face_embeddings', sa.Column('reviewed_at', sa.DateTime(), nullable=True))
    op.add_column('face_embeddings', sa.Column('student_ack_at', sa.DateTime(), nullable=True))

    op.drop_column('attendance_sessions', 'require_qr')

    op.alter_column('schedules', 'room', existing_type=sa.String(length=50), nullable=True)
    op.execute("""
        UPDATE schedules s SET room = NULL
        FROM rooms r
        WHERE s.room_id = r.id AND (s.room IS NULL OR btrim(s.room) = '' OR s.room = r.code)
    """)


def downgrade() -> None:
    op.execute("""
        UPDATE schedules s SET room = r.code
        FROM rooms r
        WHERE s.room_id = r.id AND (s.room IS NULL OR btrim(s.room) = '')
    """)
    op.execute("UPDATE schedules SET room = '' WHERE room IS NULL")
    op.alter_column('schedules', 'room', existing_type=sa.String(length=50), nullable=False)

    op.add_column('attendance_sessions', sa.Column(
        'require_qr', sa.Boolean(), nullable=False, server_default=sa.false()))

    op.drop_column('face_embeddings', 'student_ack_at')
    op.drop_column('face_embeddings', 'reviewed_at')
    op.drop_column('face_embeddings', 'reviewed_by')

    op.drop_index(op.f('ix_leave_requests_schedule_id'), table_name='leave_requests')
    op.drop_index(op.f('ix_leave_requests_student_id'), table_name='leave_requests')
    op.drop_table('leave_requests')
