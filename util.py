from datetime import datetime


def oc_vencida(start: str, end: str, limit: int = 8) -> dict[str, float | bool]:
    d_start = datetime.fromisoformat(start)
    d_end = datetime.fromisoformat(end)
    duration = d_end - d_start
    total_hour = duration.total_seconds() / 3600
    expired = total_hour > limit
    return {"duration": round(total_hour, 2), "expired": expired}


if __name__ == "__main__":
    print(oc_vencida("2026-08-05T06:07:43", "2026-08-06T00:07:16"))
