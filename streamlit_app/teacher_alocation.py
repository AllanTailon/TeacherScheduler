"""Compatibility shim — use teacher_allocation.TeacherScheduler."""

from teacher_allocation import ScheduleResult, TeacherScheduler, STATUS_NAME

__all__ = ["ScheduleResult", "TeacherScheduler", "STATUS_NAME"]
