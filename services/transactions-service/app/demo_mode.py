from fastapi import HTTPException


def is_demo_mode_enabled(value: bool) -> bool:
    return value is True


def require_demo_mode(value: bool) -> None:
    if not is_demo_mode_enabled(value):
        raise HTTPException(status_code=404, detail="Not Found")
